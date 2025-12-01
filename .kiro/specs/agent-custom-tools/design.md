# Design Document

## Overview

This document describes the design for a modular custom tools framework that allows users to add tools to chat agents with persistent per-chat storage. The system will support both custom backend tools (like a calculator) and built-in OpenAI tools (like web_search), with a frontend interface for managing which tools each agent can access.

The initial implementation includes a Calculator Tool that safely evaluates mathematical expressions using Python's `ast` module, and extends the existing agent preset system to include tool configuration.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Agent Preset UI  │  │  Tool Configuration UI           │ │
│  │  - Tool Toggle   │  │  - Built-in Tools (web_search)   │ │
│  │  - Tool List     │  │  - Custom Tools (calculator)     │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend Layer                           │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Agent Preset     │  │  Tool Registry                   │ │
│  │ Manager          │  │  - Tool Registration             │ │
│  │  - Tool Config   │  │  - Tool Discovery                │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Tool Executor    │  │  Tool Storage Manager            │ │
│  │  - Route Calls   │  │  - Per-Chat Storage              │ │
│  │  - Error Handle  │  │  - JSON Persistence              │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Custom Tools                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │ Calculator   │  │ Future Tool  │  │ Future Tool  │  │ │
│  │  │ Tool         │  │              │  │              │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Agent Presets    │  │  Tool Data                       │ │
│  │ static/agents/   │  │  static/chats/{user}/{chat}/     │ │
│  │ {user}.json      │  │  {tool_name}.json                │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Tool Configuration**: User configures tools for an agent preset via UI
2. **Tool Storage**: Configuration saved to agent preset JSON
3. **Chat Request**: User sends message with active agent preset
4. **Tool Resolution**: System determines which tools are available based on preset
5. **API Call**: OpenAI API called with appropriate tools array
6. **Tool Execution**: If AI requests tool use, backend executes and returns result
7. **Data Persistence**: Tool stores data in per-chat storage if needed

## Components and Interfaces

### 1. Tool Registry

**Purpose**: Central registry for all available tools (both custom and built-in)

**Interface**:
```python
class ToolRegistry:
    """Registry for managing available tools."""
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a custom tool."""
        
    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name."""
        
    def list_tools(self) -> list[ToolInfo]:
        """List all available tools with metadata."""
        
    def is_builtin_tool(self, tool_name: str) -> bool:
        """Check if a tool is a built-in OpenAI tool."""
```

**Tool Metadata**:
```python
@dataclass
class ToolInfo:
    """Metadata about a tool."""
    name: str
    display_name: str
    description: str
    is_builtin: bool  # True for OpenAI tools, False for custom
    category: str  # e.g., "computation", "search", "data"
```

### 2. Base Tool Interface

**Purpose**: Define contract that all custom tools must implement

**Interface**:
```python
class BaseTool(ABC):
    """Base class for all custom tools.
    
    When implementing a tool, follow OpenAI best practices:
    - Write clear, detailed function names and descriptions
    - Explicitly describe parameter formats with examples
    - Document when to use (and when NOT to use) the tool
    - Include edge cases in descriptions
    - Use strict schema validation
    - Make invalid states unrepresentable through schema design
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., 'calculator')."""
        
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Calculator')."""
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for users."""
        
    @abstractmethod
    def get_openai_tool_definition(self) -> dict[str, Any]:
        """Get OpenAI function tool definition.
        
        Must follow OpenAI function calling best practices:
        - Set "strict": true for schema validation
        - Set "additionalProperties": false to prevent extra params
        - Include detailed descriptions with examples
        - Document edge cases and error conditions
        - Use enums where appropriate to constrain values
        """
        
    @abstractmethod
    def execute(
        self, 
        parameters: dict[str, Any],
        storage: ToolStorage
    ) -> dict[str, Any]:
        """Execute the tool with given parameters."""
        
    def validate_parameters(self, parameters: dict[str, Any]) -> list[str]:
        """Validate parameters and return list of errors."""
        return []
```

### 3. Tool Storage Manager

**Purpose**: Manage per-chat persistent storage for tools

**Interface**:
```python
class ToolStorage:
    """Per-chat storage for tool data."""
    
    def __init__(
        self, 
        username: str, 
        conversation_id: str, 
        tool_name: str
    ):
        """Initialize storage for a specific tool in a conversation."""
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from storage."""
        
    def set(self, key: str, value: Any) -> None:
        """Set a value in storage."""
        
    def delete(self, key: str) -> None:
        """Delete a value from storage."""
        
    def get_all(self) -> dict[str, Any]:
        """Get all stored data."""
        
    def clear(self) -> None:
        """Clear all stored data."""
```

**Storage Implementation**:
- File path: `static/chats/{username}/{conversation_id}/{tool_name}.json`
- Format: JSON
- Atomic writes using existing `save_json_file_atomic` utility
- Thread-safe using locks from `UserFileManager` pattern

### 4. Calculator Tool

**Purpose**: Safe mathematical expression evaluator

**Implementation**:
```python
class CalculatorTool(BaseTool):
    """Safe calculator using Python AST."""
    
    name = "calculator"
    display_name = "Calculator"
    description = "Evaluate mathematical expressions safely"
    
    # Allowed AST node types for safe evaluation
    ALLOWED_NODES = {
        ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.USub, ast.UAdd, ast.Call, ast.Name
    }
    
    # Allowed functions
    ALLOWED_FUNCTIONS = {
        'abs', 'min', 'max', 'round', 'sum', 'pow'
    }
    
    def execute(self, parameters: dict[str, Any], storage: ToolStorage) -> dict[str, Any]:
        """Execute calculation and store in history."""
        expression = parameters.get('expression', '')
        
        try:
            # Parse and validate AST
            tree = ast.parse(expression, mode='eval')
            self._validate_ast(tree)
            
            # Evaluate safely
            result = eval(compile(tree, '<string>', 'eval'), 
                         {"__builtins__": {}}, 
                         self._get_safe_functions())
            
            # Store in history
            history = storage.get('history', [])
            history.append({
                'expression': expression,
                'result': result,
                'timestamp': int(time.time())
            })
            storage.set('history', history[-100:])  # Keep last 100
            
            return {
                'success': True,
                'result': result,
                'expression': expression
            }
            
        except (SyntaxError, ValueError) as e:
            return {
                'success': False,
                'error': f'Invalid expression: {str(e)}'
            }
```

**OpenAI Tool Definition**:

Following OpenAI best practices for function definitions:
- Clear, detailed descriptions
- Explicit parameter formats with examples
- Edge cases documented
- Strict schema validation
- Invalid states made unrepresentable

```python
{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluates mathematical expressions and returns the numeric result. Use this when the user asks for calculations, math operations, or numeric computations. Supports basic arithmetic operators (+, -, *, /, **, %) and mathematical functions (abs, min, max, round, sum, pow). Returns an error for invalid expressions or unsafe operations.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A valid mathematical expression to evaluate. Examples: '2 + 2' (addition), 'pow(2, 8)' (exponentiation), 'abs(-5)' (absolute value), 'max(10, 20, 30)' (maximum), '(5 + 3) * 2' (with parentheses). Do not include variable assignments or code statements - only mathematical expressions."
                }
            },
            "required": ["expression"],
            "additionalProperties": false
        },
        "strict": true
    }
}
```

### 5. Agent Preset Extension

**Purpose**: Extend agent presets to include tool configuration

**Updated AgentPreset Model**:
```python
class AgentPreset(BaseModel):
    """Agent preset with tool configuration."""
    id: str
    name: str
    instructions: str
    model: str
    default_reasoning_level: str
    created_at: int
    updated_at: int
    enabled_tools: list[str] = Field(
        default_factory=lambda: ["web_search", "calculator"],
        description="List of enabled tool names"
    )
```

**Default Tools**:
- New presets: `["web_search", "calculator"]`
- Existing presets: Migrated to include defaults

### 6. Tool Executor

**Purpose**: Execute tool calls from OpenAI API

**Interface**:
```python
class ToolExecutor:
    """Execute tool calls from OpenAI responses."""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
        
    def execute_tool_call(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        username: str,
        conversation_id: str
    ) -> dict[str, Any]:
        """Execute a tool call and return result."""
        
        # Get tool from registry
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {'error': f'Tool {tool_name} not found'}
            
        # Create storage for this tool
        storage = ToolStorage(username, conversation_id, tool_name)
        
        # Execute with error handling
        try:
            return tool.execute(parameters, storage)
        except Exception as e:
            logging.error(f"Tool execution error: {e}")
            return {'error': f'Tool execution failed: {str(e)}'}
```

### 7. ResponsesAPIClient Extension

**Purpose**: Build tools array based on agent preset configuration

**Updated Method**:
```python
def create_response(
    self,
    input_text: str,
    previous_response_id: str | None = None,
    stream: bool = True,
    username: str | None = None,
    model: str | None = None,
    reasoning_level: str | None = None,
    instructions: str | None = None,
    enabled_tools: list[str] | None = None,  # NEW
) -> Any:
    """Create response with configured tools."""
    
    # Build tools array from enabled_tools
    tools = self._build_tools_array(enabled_tools or ["web_search"])
    
    params = {
        "model": validated_model,
        "input": input_text,
        "stream": stream,
        "store": True,
        "tools": tools,  # Dynamic based on preset
        "instructions": enhanced_instructions,
    }
    
    # ... rest of implementation

def _build_tools_array(self, enabled_tools: list[str]) -> list[dict[str, Any]]:
    """Build OpenAI tools array from enabled tool names."""
    tools = []
    
    for tool_name in enabled_tools:
        if tool_name == "web_search":
            # Built-in OpenAI tool
            tools.append({
                "type": "web_search",
                "user_location": {
                    "type": "approximate",
                    "country": "CA",
                    "city": "Vancouver",
                    "region": "Vancouver",
                    "timezone": "America/Vancouver",
                }
            })
        else:
            # Custom tool - get definition from registry
            tool = tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool.get_openai_tool_definition())
    
    return tools
```

### 8. Frontend Tool Configuration UI

**Purpose**: Allow users to enable/disable tools for agent presets

**UI Components**:

1. **Tool Configuration Section** (in agent preset modal):
```html
<div class="tool-configuration">
    <h4>Available Tools</h4>
    
    <div class="tool-category">
        <h5>Built-in Tools</h5>
        <label>
            <input type="checkbox" name="tool" value="web_search" checked>
            Web Search - Search the internet for current information
        </label>
    </div>
    
    <div class="tool-category">
        <h5>Custom Tools</h5>
        <label>
            <input type="checkbox" name="tool" value="calculator" checked>
            Calculator - Evaluate mathematical expressions
        </label>
    </div>
</div>
```

2. **TypeScript Interface Updates**:
```typescript
export interface AgentPreset {
    id: string;
    name: string;
    instructions: string;
    model: 'gpt-5.1' | 'gpt-5' | 'gpt-5-mini' | 'gpt-5-pro';
    default_reasoning_level: 'high' | 'medium' | 'low' | 'none';
    created_at: number;
    updated_at: number;
    enabled_tools: string[];  // NEW
}
```

## Data Models

### Tool Storage Data Structure

**File**: `static/chats/{username}/{conversation_id}/{tool_name}.json`

**Calculator Tool Storage Example**:
```json
{
    "history": [
        {
            "expression": "2 + 2",
            "result": 4,
            "timestamp": 1701234567
        },
        {
            "expression": "pow(2, 8)",
            "result": 256,
            "timestamp": 1701234580
        }
    ]
}
```

### Agent Preset Data Structure

**File**: `static/agents/{username}.json`

**Updated Structure**:
```json
{
    "presets": [
        {
            "id": "default",
            "name": "Default Assistant",
            "instructions": "You are a helpful assistant...",
            "model": "gpt-5.1",
            "default_reasoning_level": "medium",
            "created_at": 1701234567,
            "updated_at": 1701234567,
            "enabled_tools": ["web_search", "calculator"]
        }
    ]
}
```

## Data Flow

### Tool Execution Flow

1. **User sends message** with active agent preset
2. **Backend retrieves preset** and gets `enabled_tools` list
3. **Tools array built** from enabled_tools configuration
4. **OpenAI API called** with tools array
5. **AI decides to use tool** (e.g., calculator)
6. **Tool call received** in stream event
7. **Backend executes tool**:
   - Get tool from registry
   - Create ToolStorage instance
   - Execute tool with parameters
   - Tool reads/writes to storage
8. **Result returned** to OpenAI API
9. **AI incorporates result** in response
10. **Response streamed** to frontend

### Tool Configuration Flow

1. **User opens agent preset modal**
2. **Tool list rendered** with checkboxes
3. **User toggles tools** on/off
4. **User saves preset**
5. **Frontend sends** enabled_tools array
6. **Backend validates** tool names
7. **Preset saved** with tool configuration
8. **Future chats** use updated tool configuration

## Error Handling

### Tool Execution Errors

**Error Types**:
1. **Tool Not Found**: Tool name not in registry
2. **Invalid Parameters**: Parameters don't match tool schema
3. **Execution Error**: Tool raises exception during execution
4. **Storage Error**: Failed to read/write tool data
5. **Timeout**: Tool execution exceeds time limit

**Error Response Format**:
```python
{
    'success': False,
    'error': 'Error message',
    'error_code': 'tool_not_found',  # machine-readable
    'user_action': 'Try again or contact support'
}
```

**Error Handling Strategy**:
- All tool execution wrapped in try/except
- Errors logged with full context
- User-friendly error messages returned
- Chat continues even if tool fails
- Storage errors don't crash tool execution

### Tool Configuration Errors

**Validation**:
- Tool names validated against registry
- At least one tool must be enabled
- Unknown tool names rejected
- Built-in tools validated separately

**Error Messages**:
- "Unknown tool: {tool_name}"
- "At least one tool must be enabled"
- "Tool {tool_name} is not available"

## Testing Strategy

### Unit Tests

**Tool Registry Tests**:
- Test tool registration
- Test tool retrieval
- Test tool listing
- Test built-in tool detection

**Calculator Tool Tests**:
- Test valid expressions (2+2, pow(2,8), abs(-5))
- Test invalid expressions (malicious code, undefined functions)
- Test storage operations (history tracking)
- Test error handling (syntax errors, division by zero)

**Tool Storage Tests**:
- Test get/set/delete operations
- Test atomic writes
- Test thread safety
- Test file creation/cleanup

**Agent Preset Tests**:
- Test preset creation with tools
- Test preset update with tools
- Test tool configuration validation
- Test migration of existing presets

### Integration Tests

**End-to-End Tool Execution**:
- Create agent preset with calculator
- Send message requiring calculation
- Verify tool called correctly
- Verify result incorporated in response
- Verify storage persisted

**Frontend Integration**:
- Test tool checkbox rendering
- Test tool toggle functionality
- Test preset save with tools
- Test tool configuration persistence

### Property-Based Tests

Not applicable for this feature - the tool system is primarily about integration and configuration rather than algorithmic correctness that would benefit from property-based testing.

## OpenAI Function Calling Best Practices

### Function Definition Guidelines

When implementing custom tools, follow OpenAI's recommended best practices:

**1. Clear and Detailed Descriptions**
- Write explicit function names that describe the purpose
- Provide detailed parameter descriptions with format specifications
- Include examples in descriptions (e.g., "City and country e.g. Bogotá, Colombia")
- Document what the output represents

**2. System Prompt Integration**
- Use agent instructions to describe when (and when NOT) to use each function
- Provide explicit guidance on tool selection
- Include examples and edge cases to prevent recurring failures
- Note: For reasoning models, excessive examples may hurt performance

**3. Schema Design Principles**
- Use `"strict": true` for schema validation
- Set `"additionalProperties": false` to prevent unexpected parameters
- Leverage JSON Schema features: enums, nested objects, type constraints
- Make invalid states unrepresentable (e.g., avoid `toggle_light(on: bool, off: bool)`)
- Use enums to constrain values to valid options

**4. Software Engineering Best Practices**
- Apply the "principle of least surprise" - make functions obvious and intuitive
- Pass the "intern test" - can someone use the function with only the provided information?
- Don't make the model fill arguments you already know (offload to code)
- Combine functions that are always called in sequence
- Keep the number of functions small (aim for fewer than 20)

**5. Example: Well-Designed Function**
```python
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Units the temperature will be returned in."
                }
            },
            "required": ["location", "units"],
            "additionalProperties": false
        },
        "strict": true
    }
}
```

### Implementation Requirements

All custom tools MUST:
- Include `"strict": true` in function definition
- Include `"additionalProperties": false` in parameters schema
- Provide detailed descriptions with examples
- Document edge cases and error conditions
- Use enums for constrained value sets
- Follow the "principle of least surprise"

## Security Considerations

### Calculator Tool Security

**AST Validation**:
- Only allow safe AST node types
- Reject any code execution attempts
- No access to `__builtins__`
- No import statements
- No attribute access

**Function Whitelist**:
- Only allow specific safe functions
- No access to file system
- No network access
- No system calls

**Resource Limits**:
- Expression length limit (1000 chars)
- Execution timeout (1 second)
- Result size limit
- History size limit (100 entries)

### Tool Storage Security

**Access Control**:
- Tools can only access their own storage
- Storage isolated by username and conversation
- No cross-conversation data access
- No cross-user data access

**Input Validation**:
- Validate all tool parameters
- Sanitize file paths
- Prevent directory traversal
- Validate JSON structure

## Performance Considerations

### Tool Registry

- Registry initialized once at startup
- Tools cached in memory
- No database queries for tool lookup
- O(1) tool retrieval by name

### Tool Storage

- Lazy loading (only load when tool used)
- File-based storage (no database overhead)
- Atomic writes prevent corruption
- Thread-safe with locks

### Tool Execution

- Timeout prevents hanging
- Async execution doesn't block chat
- Error handling prevents cascading failures
- Storage operations batched when possible

## Migration Strategy

### Existing Agent Presets

**Migration Steps**:
1. Add `enabled_tools` field to AgentPreset model with default
2. Existing presets automatically get default tools on load
3. No data migration required (Pydantic handles defaults)
4. Users can customize tools after migration

**Backward Compatibility**:
- Old presets without `enabled_tools` work with defaults
- Frontend handles missing field gracefully
- API accepts presets with or without tools field

### Deployment

**Phase 1**: Backend infrastructure
- Deploy tool registry
- Deploy calculator tool
- Deploy tool storage
- Update ResponsesAPIClient

**Phase 2**: Agent preset integration
- Update AgentPreset model
- Update preset API endpoints
- Migrate existing presets

**Phase 3**: Frontend
- Add tool configuration UI
- Update preset forms
- Test end-to-end

## Future Extensions

### Additional Tools

**Potential Tools**:
- **Code Executor**: Safe Python/JavaScript execution
- **File Manager**: Read/write user files
- **Database Query**: Query user data
- **API Caller**: Call external APIs
- **Image Analyzer**: Analyze uploaded images

### Tool Marketplace

- User-contributed tools
- Tool discovery and installation
- Tool versioning
- Tool permissions system

### Advanced Features

- Tool chaining (one tool calls another)
- Conditional tool execution
- Tool usage analytics
- Tool rate limiting per user
- Tool cost tracking
