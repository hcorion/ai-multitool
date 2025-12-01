"""Unit tests for Calculator tool.

Tests cover:
- Valid expressions: basic arithmetic, functions, parentheses
- Invalid expressions: malicious code, undefined functions, syntax errors
- Edge cases: division by zero, very large numbers, empty expressions
- Storage operations: history tracking, history limit
- Error handling: proper error messages for all failure modes
"""

import ast
import os
import tempfile
import shutil
from unittest.mock import Mock

import pytest

from tools.calculator_tool import CalculatorTool
from tool_framework import ToolStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def calculator():
    """Create a CalculatorTool instance."""
    return CalculatorTool()


@pytest.fixture
def storage(temp_storage_dir):
    """Create a ToolStorage instance for testing."""
    return ToolStorage(
        username='testuser',
        conversation_id='test_conv',
        tool_name='calculator',
        static_folder=temp_storage_dir
    )


class TestCalculatorToolBasics:
    """Test basic Calculator tool properties and metadata."""
    
    def test_tool_name(self, calculator):
        """Test tool name property."""
        assert calculator.name == 'calculator'
    
    def test_display_name(self, calculator):
        """Test display name property."""
        assert calculator.display_name == 'Calculator'
    
    def test_description(self, calculator):
        """Test description property."""
        assert 'mathematical expressions' in calculator.description.lower()
    
    def test_openai_tool_definition(self, calculator):
        """Test OpenAI tool definition structure."""
        definition = calculator.get_openai_tool_definition()
        
        assert definition['type'] == 'function'
        assert 'function' in definition
        
        func = definition['function']
        assert func['name'] == 'calculator'
        assert func['strict'] is True
        assert 'description' in func
        assert 'parameters' in func
        
        params = func['parameters']
        assert params['type'] == 'object'
        assert 'expression' in params['properties']
        assert 'expression' in params['required']
        assert params['additionalProperties'] is False


class TestValidExpressions:
    """Test valid mathematical expressions."""
    
    def test_basic_addition(self, calculator, storage):
        """Test simple addition."""
        result = calculator.execute({'expression': '2 + 2'}, storage)
        assert result['success'] is True
        assert result['result'] == 4
        assert result['expression'] == '2 + 2'
    
    def test_basic_subtraction(self, calculator, storage):
        """Test simple subtraction."""
        result = calculator.execute({'expression': '10 - 3'}, storage)
        assert result['success'] is True
        assert result['result'] == 7
    
    def test_basic_multiplication(self, calculator, storage):
        """Test simple multiplication."""
        result = calculator.execute({'expression': '6 * 7'}, storage)
        assert result['success'] is True
        assert result['result'] == 42
    
    def test_basic_division(self, calculator, storage):
        """Test simple division."""
        result = calculator.execute({'expression': '15 / 3'}, storage)
        assert result['success'] is True
        assert result['result'] == 5.0
    
    def test_exponentiation(self, calculator, storage):
        """Test exponentiation operator."""
        result = calculator.execute({'expression': '2 ** 8'}, storage)
        assert result['success'] is True
        assert result['result'] == 256
    
    def test_modulo(self, calculator, storage):
        """Test modulo operator."""
        result = calculator.execute({'expression': '17 % 5'}, storage)
        assert result['success'] is True
        assert result['result'] == 2
    
    def test_parentheses(self, calculator, storage):
        """Test expressions with parentheses."""
        result = calculator.execute({'expression': '(5 + 3) * 2'}, storage)
        assert result['success'] is True
        assert result['result'] == 16
    
    def test_nested_parentheses(self, calculator, storage):
        """Test nested parentheses."""
        result = calculator.execute({'expression': '((2 + 3) * (4 + 5))'}, storage)
        assert result['success'] is True
        assert result['result'] == 45
    
    def test_complex_expression(self, calculator, storage):
        """Test complex expression with multiple operations."""
        result = calculator.execute({'expression': '2 + 3 * 4 - 5 / 2'}, storage)
        assert result['success'] is True
        assert result['result'] == 11.5
    
    def test_negative_numbers(self, calculator, storage):
        """Test expressions with negative numbers."""
        result = calculator.execute({'expression': '-5 + 10'}, storage)
        assert result['success'] is True
        assert result['result'] == 5
    
    def test_unary_plus(self, calculator, storage):
        """Test unary plus operator."""
        result = calculator.execute({'expression': '+5 + 3'}, storage)
        assert result['success'] is True
        assert result['result'] == 8
    
    def test_float_arithmetic(self, calculator, storage):
        """Test floating point arithmetic."""
        result = calculator.execute({'expression': '3.14 + 2.86'}, storage)
        assert result['success'] is True
        assert abs(result['result'] - 6.0) < 0.001


class TestMathematicalFunctions:
    """Test mathematical functions."""
    
    def test_abs_function(self, calculator, storage):
        """Test absolute value function."""
        result = calculator.execute({'expression': 'abs(-5)'}, storage)
        assert result['success'] is True
        assert result['result'] == 5
    
    def test_min_function(self, calculator, storage):
        """Test minimum function."""
        result = calculator.execute({'expression': 'min(10, 20, 5, 30)'}, storage)
        assert result['success'] is True
        assert result['result'] == 5
    
    def test_max_function(self, calculator, storage):
        """Test maximum function."""
        result = calculator.execute({'expression': 'max(10, 20, 5, 30)'}, storage)
        assert result['success'] is True
        assert result['result'] == 30
    
    def test_round_function(self, calculator, storage):
        """Test round function."""
        result = calculator.execute({'expression': 'round(3.14159, 2)'}, storage)
        assert result['success'] is True
        assert result['result'] == 3.14
    
    def test_round_no_decimals(self, calculator, storage):
        """Test round function without decimal places."""
        result = calculator.execute({'expression': 'round(3.7)'}, storage)
        assert result['success'] is True
        assert result['result'] == 4
    
    def test_sum_function(self, calculator, storage):
        """Test sum function with list."""
        result = calculator.execute({'expression': 'sum([1, 2, 3, 4, 5])'}, storage)
        assert result['success'] is True
        assert result['result'] == 15
    
    def test_pow_function(self, calculator, storage):
        """Test power function."""
        result = calculator.execute({'expression': 'pow(2, 10)'}, storage)
        assert result['success'] is True
        assert result['result'] == 1024
    
    def test_nested_functions(self, calculator, storage):
        """Test nested function calls."""
        result = calculator.execute({'expression': 'abs(min(-5, -10, -3))'}, storage)
        assert result['success'] is True
        assert result['result'] == 10
    
    def test_function_with_arithmetic(self, calculator, storage):
        """Test functions combined with arithmetic."""
        result = calculator.execute({'expression': 'max(5, 10) + min(2, 3)'}, storage)
        assert result['success'] is True
        assert result['result'] == 12


class TestInvalidExpressions:
    """Test invalid and malicious expressions."""
    
    def test_undefined_function(self, calculator, storage):
        """Test expression with undefined function."""
        result = calculator.execute({'expression': 'eval("2 + 2")'}, storage)
        assert result['success'] is False
        assert 'not allowed' in result['error'].lower()
    
    def test_import_statement(self, calculator, storage):
        """Test expression with import statement."""
        result = calculator.execute({'expression': 'import os'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_attribute_access(self, calculator, storage):
        """Test expression with attribute access."""
        result = calculator.execute({'expression': '__import__("os").system("ls")'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_variable_assignment(self, calculator, storage):
        """Test expression with variable assignment."""
        result = calculator.execute({'expression': 'x = 5'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_malicious_code_exec(self, calculator, storage):
        """Test expression attempting code execution."""
        result = calculator.execute({'expression': 'exec("print(1)")'}, storage)
        assert result['success'] is False
        assert 'not allowed' in result['error'].lower()
    
    def test_malicious_code_compile(self, calculator, storage):
        """Test expression attempting compilation."""
        result = calculator.execute({'expression': 'compile("1+1", "", "eval")'}, storage)
        assert result['success'] is False
        assert 'not allowed' in result['error'].lower()
    
    def test_open_file(self, calculator, storage):
        """Test expression attempting file access."""
        result = calculator.execute({'expression': 'open("/etc/passwd")'}, storage)
        assert result['success'] is False
        assert 'not allowed' in result['error'].lower()
    
    def test_lambda_function(self, calculator, storage):
        """Test expression with lambda function."""
        result = calculator.execute({'expression': '(lambda x: x + 1)(5)'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_list_comprehension(self, calculator, storage):
        """Test expression with list comprehension."""
        result = calculator.execute({'expression': '[x for x in range(10)]'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_syntax_error(self, calculator, storage):
        """Test expression with syntax error."""
        result = calculator.execute({'expression': '2 +'}, storage)
        assert result['success'] is False
        assert 'syntax' in result['error'].lower()
    
    def test_unmatched_parentheses(self, calculator, storage):
        """Test expression with unmatched parentheses."""
        result = calculator.execute({'expression': '(2 + 3'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_invalid_operator(self, calculator, storage):
        """Test expression with invalid operator."""
        result = calculator.execute({'expression': '2 @ 3'}, storage)
        assert result['success'] is False
        assert 'error' in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_division_by_zero(self, calculator, storage):
        """Test division by zero."""
        result = calculator.execute({'expression': '1 / 0'}, storage)
        assert result['success'] is False
        assert 'division by zero' in result['error'].lower()
    
    def test_modulo_by_zero(self, calculator, storage):
        """Test modulo by zero."""
        result = calculator.execute({'expression': '5 % 0'}, storage)
        assert result['success'] is False
        assert 'error' in result
    
    def test_empty_expression(self, calculator, storage):
        """Test empty expression."""
        result = calculator.execute({'expression': ''}, storage)
        assert result['success'] is False
        assert 'empty' in result['error'].lower()
    
    def test_whitespace_only_expression(self, calculator, storage):
        """Test expression with only whitespace."""
        result = calculator.execute({'expression': '   '}, storage)
        assert result['success'] is False
        assert 'empty' in result['error'].lower()
    
    def test_very_large_number(self, calculator, storage):
        """Test calculation with very large numbers."""
        result = calculator.execute({'expression': '10 ** 100'}, storage)
        assert result['success'] is True
        assert result['result'] == 10 ** 100
    
    def test_very_small_number(self, calculator, storage):
        """Test calculation with very small numbers."""
        result = calculator.execute({'expression': '1 / (10 ** 100)'}, storage)
        assert result['success'] is True
        assert result['result'] > 0
        assert result['result'] < 1e-99
    
    def test_expression_too_long(self, calculator, storage):
        """Test expression exceeding maximum length."""
        long_expr = '1 + ' * 1000 + '1'
        result = calculator.execute({'expression': long_expr}, storage)
        assert result['success'] is False
        assert 'too long' in result['error'].lower()
    
    def test_zero_operations(self, calculator, storage):
        """Test operations with zero."""
        result = calculator.execute({'expression': '0 * 999999'}, storage)
        assert result['success'] is True
        assert result['result'] == 0
    
    def test_negative_exponent(self, calculator, storage):
        """Test negative exponent."""
        result = calculator.execute({'expression': '2 ** -3'}, storage)
        assert result['success'] is True
        assert abs(result['result'] - 0.125) < 0.001
    
    def test_empty_list_sum(self, calculator, storage):
        """Test sum of empty list."""
        result = calculator.execute({'expression': 'sum([])'}, storage)
        assert result['success'] is True
        assert result['result'] == 0
    
    def test_single_number(self, calculator, storage):
        """Test expression with just a number."""
        result = calculator.execute({'expression': '42'}, storage)
        assert result['success'] is True
        assert result['result'] == 42


class TestStorageOperations:
    """Test storage operations and history tracking."""
    
    def test_history_stored(self, calculator, storage):
        """Test that calculation is stored in history."""
        calculator.execute({'expression': '2 + 2'}, storage)
        
        history = storage.get('history', [])
        assert len(history) == 1
        assert history[0]['expression'] == '2 + 2'
        assert history[0]['result'] == 4
        assert 'timestamp' in history[0]
    
    def test_multiple_calculations_stored(self, calculator, storage):
        """Test that multiple calculations are stored."""
        calculator.execute({'expression': '2 + 2'}, storage)
        calculator.execute({'expression': '3 * 3'}, storage)
        calculator.execute({'expression': '10 - 5'}, storage)
        
        history = storage.get('history', [])
        assert len(history) == 3
        assert history[0]['result'] == 4
        assert history[1]['result'] == 9
        assert history[2]['result'] == 5
    
    def test_history_limit(self, calculator, storage):
        """Test that history is limited to 100 entries."""
        # Add 150 calculations
        for i in range(150):
            calculator.execute({'expression': f'{i} + 1'}, storage)
        
        history = storage.get('history', [])
        assert len(history) == 100
        
        # Verify oldest entries were removed (first 50)
        # Most recent should be 149 + 1 = 150
        assert history[-1]['result'] == 150
        # Oldest should be 50 + 1 = 51
        assert history[0]['result'] == 51
    
    def test_failed_calculation_not_stored(self, calculator, storage):
        """Test that failed calculations are not stored in history."""
        calculator.execute({'expression': '1 / 0'}, storage)
        
        history = storage.get('history', [])
        assert len(history) == 0
    
    def test_storage_persistence(self, calculator, temp_storage_dir):
        """Test that storage persists across ToolStorage instances."""
        # Create first storage instance and add calculation
        storage1 = ToolStorage(
            username='testuser',
            conversation_id='test_conv',
            tool_name='calculator',
            static_folder=temp_storage_dir
        )
        calculator.execute({'expression': '5 + 5'}, storage1)
        
        # Create second storage instance and verify data persists
        storage2 = ToolStorage(
            username='testuser',
            conversation_id='test_conv',
            tool_name='calculator',
            static_folder=temp_storage_dir
        )
        history = storage2.get('history', [])
        assert len(history) == 1
        assert history[0]['result'] == 10
    
    def test_storage_isolation_by_conversation(self, calculator, temp_storage_dir):
        """Test that storage is isolated per conversation."""
        storage1 = ToolStorage(
            username='testuser',
            conversation_id='conv1',
            tool_name='calculator',
            static_folder=temp_storage_dir
        )
        storage2 = ToolStorage(
            username='testuser',
            conversation_id='conv2',
            tool_name='calculator',
            static_folder=temp_storage_dir
        )
        
        calculator.execute({'expression': '1 + 1'}, storage1)
        calculator.execute({'expression': '2 + 2'}, storage2)
        
        history1 = storage1.get('history', [])
        history2 = storage2.get('history', [])
        
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]['result'] == 2
        assert history2[0]['result'] == 4


class TestParameterValidation:
    """Test parameter validation."""
    
    def test_validate_parameters_empty_expression(self, calculator):
        """Test validation of empty expression."""
        errors = calculator.validate_parameters({'expression': ''})
        assert len(errors) > 0
        assert any('empty' in err.lower() for err in errors)
    
    def test_validate_parameters_whitespace_expression(self, calculator):
        """Test validation of whitespace-only expression."""
        errors = calculator.validate_parameters({'expression': '   '})
        assert len(errors) > 0
        assert any('empty' in err.lower() for err in errors)
    
    def test_validate_parameters_too_long(self, calculator):
        """Test validation of expression exceeding max length."""
        long_expr = 'x' * 1001
        errors = calculator.validate_parameters({'expression': long_expr})
        assert len(errors) > 0
        assert any('too long' in err.lower() for err in errors)
    
    def test_validate_parameters_valid_expression(self, calculator):
        """Test validation of valid expression."""
        errors = calculator.validate_parameters({'expression': '2 + 2'})
        assert len(errors) == 0
    
    def test_validate_parameters_missing_expression(self, calculator):
        """Test validation when expression parameter is missing."""
        errors = calculator.validate_parameters({})
        assert len(errors) == 0  # Missing parameter is handled by schema validation


class TestErrorMessages:
    """Test that error messages are descriptive and helpful."""
    
    def test_syntax_error_message(self, calculator, storage):
        """Test syntax error message is descriptive."""
        result = calculator.execute({'expression': '2 +'}, storage)
        assert result['success'] is False
        assert 'syntax' in result['error'].lower()
        assert result['expression'] == '2 +'
    
    def test_undefined_function_message(self, calculator, storage):
        """Test undefined function error message."""
        result = calculator.execute({'expression': 'undefined_func(5)'}, storage)
        assert result['success'] is False
        assert 'not allowed' in result['error'].lower()
        assert 'undefined_func' in result['error']
    
    def test_division_by_zero_message(self, calculator, storage):
        """Test division by zero error message."""
        result = calculator.execute({'expression': '10 / 0'}, storage)
        assert result['success'] is False
        assert 'division by zero' in result['error'].lower()
    
    def test_empty_expression_message(self, calculator, storage):
        """Test empty expression error message."""
        result = calculator.execute({'expression': ''}, storage)
        assert result['success'] is False
        assert 'empty' in result['error'].lower()
    
    def test_error_includes_expression(self, calculator, storage):
        """Test that error responses include the original expression."""
        result = calculator.execute({'expression': 'bad expression'}, storage)
        assert result['success'] is False
        assert result['expression'] == 'bad expression'
