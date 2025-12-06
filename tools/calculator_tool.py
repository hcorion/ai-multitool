import ast
import math
import time
from typing import Any

from tool_framework import BaseTool, ToolStorage


class CalculatorTool(BaseTool):
    """Safe calculator using Python AST for expression evaluation.

    This tool evaluates mathematical expressions safely by:
    - Using Python's AST module to parse and validate expressions
    - Restricting allowed operations to safe mathematical operations
    - Preventing code execution, imports, and attribute access
    - Limiting allowed functions to a safe whitelist
    - Storing calculation history per conversation

    Supported operations:
    - Arithmetic: +, -, *, /, **, % (add, subtract, multiply, divide, power, modulo)
    - Functions: abs, min, max, round, sum, pow
    - Parentheses for grouping

    Security features:
    - No access to __builtins__ or system functions
    - No import statements allowed
    - No attribute access allowed
    - No variable assignments allowed
    - Expression length limited to 1000 characters
    - Only safe AST node types allowed

    Example expressions:
    - "2 + 2" -> 4
    - "pow(2, 8)" -> 256
    - "abs(-5)" -> 5
    - "max(10, 20, 30)" -> 30
    - "(5 + 3) * 2" -> 16
    - "round(3.14159, 2)" -> 3.14
    """

    # Maximum expression length to prevent abuse
    MAX_EXPRESSION_LENGTH = 1000

    # Allowed AST node types for safe evaluation
    ALLOWED_NODES = {
        ast.Expression,  # Top-level expression wrapper
        ast.Constant,  # Literal values (numbers)
        ast.BinOp,  # Binary operations (a + b)
        ast.UnaryOp,  # Unary operations (-a, +a)
        ast.Call,  # Function calls
        ast.Name,  # Variable/function names
        ast.Load,  # Load context for names (used when reading variables/functions)
        ast.List,  # List literals [1, 2, 3]
        ast.Tuple,  # Tuple literals (1, 2, 3)
        # Binary operators
        ast.Add,  # +
        ast.Sub,  # -
        ast.Mult,  # *
        ast.Div,  # /
        ast.Pow,  # **
        ast.Mod,  # %
        # Unary operators
        ast.USub,  # Unary minus (-)
        ast.UAdd,  # Unary plus (+)
    }

    # Allowed function names
    ALLOWED_FUNCTIONS = {
        "abs",  # Absolute value
        "min",  # Minimum value
        "max",  # Maximum value
        "round",  # Round to n decimal places
        "sum",  # Sum of iterable
        "pow",  # Power function
    }

    @property
    def name(self) -> str:
        """Tool identifier."""
        return "calculator"

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return "Calculator"

    @property
    def description(self) -> str:
        """Tool description for users."""
        return "Evaluate mathematical expressions safely"

    def get_openai_tool_definition(self) -> dict[str, Any]:
        """Get OpenAI function tool definition.

        Returns OpenAI function definition following best practices:
        - Strict schema validation enabled
        - Detailed descriptions with examples
        - Edge cases documented
        - Additional properties disabled
        
        Note: Uses flat structure for Responses API (not nested under 'function' key)
        """
        return {
            "type": "function",
            "name": "calculator",
            "description": (
                "Evaluates mathematical expressions and returns the numeric result. "
                "Use this when the user asks for calculations, math operations, or numeric computations. "
                "Supports basic arithmetic operators (+, -, *, /, **, %) and mathematical functions "
                "(abs, min, max, round, sum, pow). "
                "Returns an error for invalid expressions or unsafe operations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A valid mathematical expression to evaluate. "
                            "Examples: '2 + 2' (addition), 'pow(2, 8)' (exponentiation), "
                            "'abs(-5)' (absolute value), 'max(10, 20, 30)' (maximum), "
                            "'(5 + 3) * 2' (with parentheses). "
                            "Do not include variable assignments or code statements - "
                            "only mathematical expressions."
                        ),
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def validate_parameters(self, parameters: dict[str, Any]) -> list[str]:
        """Validate parameters beyond schema validation.

        Args:
            parameters: Dictionary of parameters to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if "expression" in parameters:
            expr = parameters["expression"]

            # Check expression length
            if len(expr) > self.MAX_EXPRESSION_LENGTH:
                errors.append(
                    f"Expression too long (max {self.MAX_EXPRESSION_LENGTH} characters)"
                )

            # Check for empty expression
            if not expr or not expr.strip():
                errors.append("Expression cannot be empty")

        return errors

    def execute(
        self, parameters: dict[str, Any], storage: ToolStorage
    ) -> dict[str, Any]:
        """Execute calculation and store in history.

        Args:
            parameters: Dictionary containing 'expression' key
            storage: ToolStorage instance for persisting calculation history

        Returns:
            Dictionary with success status, result, and expression.
            On error, includes error message instead of result.

        Example success response:
            {
                'success': True,
                'result': 4,
                'expression': '2 + 2'
            }

        Example error response:
            {
                'success': False,
                'error': 'Invalid expression: division by zero',
                'expression': '1 / 0'
            }
        """
        expression = parameters.get("expression", "")

        # Validate parameters
        validation_errors = self.validate_parameters(parameters)
        if validation_errors:
            return {
                "success": False,
                "error": "; ".join(validation_errors),
                "expression": expression,
            }

        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode="eval")

            # Validate AST for safety
            self._validate_ast(tree)

            # Evaluate expression safely
            result = eval(
                compile(tree, "<string>", "eval"),
                {"__builtins__": {}},  # No access to builtins
                self._get_safe_functions(),  # Only allowed functions
            )

            # Convert non-finite floats to strings for valid JSON
            result = self._sanitize_result(result)

            # Store in history
            self._store_calculation(storage, expression, result)

            return {"success": True, "result": result, "expression": expression}

        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Invalid expression syntax: {str(e)}",
                "expression": expression,
            }
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid expression: {str(e)}",
                "expression": expression,
            }
        except ZeroDivisionError:
            return {
                "success": False,
                "error": "Division by zero",
                "expression": expression,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Calculation error: {str(e)}",
                "expression": expression,
            }

    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate that AST only contains safe node types.

        Args:
            tree: AST tree to validate

        Raises:
            ValueError: If tree contains unsafe node types or operations
        """
        for node in ast.walk(tree):
            # Check if node type is allowed
            if type(node) not in self.ALLOWED_NODES:
                raise ValueError(
                    f"Unsafe operation: {type(node).__name__} is not allowed"
                )

            # If it's a function call, validate function name
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in self.ALLOWED_FUNCTIONS:
                        raise ValueError(
                            f"Function {func_name} is not allowed. "
                            f"Allowed functions: {', '.join(sorted(self.ALLOWED_FUNCTIONS))}"
                        )
                else:
                    raise ValueError("Only simple function calls are allowed")

    def _get_safe_functions(self) -> dict[str, Any]:
        """Get dictionary of safe functions for evaluation.

        Returns:
            Dictionary mapping function names to their implementations
        """
        return {
            "abs": abs,
            "min": min,
            "max": max,
            "round": round,
            "sum": sum,
            "pow": pow,
        }

    def _sanitize_result(self, result: Any) -> Any:
        """Sanitize result for valid JSON serialization.

        Converts non-finite floats (Infinity, -Infinity, NaN) to strings
        since JSON doesn't support these values.

        Args:
            result: The calculation result

        Returns:
            The result, with non-finite floats converted to strings
        """
        if isinstance(result, float) and not math.isfinite(result):
            if math.isnan(result):
                return "NaN"
            elif result > 0:
                return "Infinity"
            else:
                return "-Infinity"
        return result

    def _store_calculation(
        self, storage: ToolStorage, expression: str, result: Any
    ) -> None:
        """Store calculation in history.

        Maintains a history of the last 100 calculations.

        Args:
            storage: ToolStorage instance
            expression: The expression that was evaluated
            result: The result of the evaluation
        """
        # Get existing history
        history = storage.get("history", [])

        # Add new calculation
        history.append(
            {"expression": expression, "result": result, "timestamp": int(time.time())}
        )

        # Keep only last 100 entries
        if len(history) > 100:
            history = history[-100:]

        # Save updated history
        storage.set("history", history)

    def format_input_for_display(self, parameters: dict[str, Any]) -> str:
        """Format calculator input for display.

        Shows just the expression without JSON wrapper.

        Args:
            parameters: Dictionary containing 'expression' key

        Returns:
            The expression string
        """
        return parameters.get("expression", "")

    def format_output_for_display(self, result: dict[str, Any]) -> str:
        """Format calculator output for display.

        Shows just the result or error message.

        Args:
            result: Dictionary containing execution result

        Returns:
            The result value or error message
        """
        if result.get("success"):
            return str(result.get("result", ""))
        return f"Error: {result.get('error', 'Unknown error')}"
