"""Tool framework for custom agent tools.

This module provides the infrastructure for creating and managing custom tools
that can be used by chat agents. It includes:
- BaseTool: Abstract base class for all custom tools
- ToolRegistry: Central registry for managing available tools
- ToolInfo: Metadata about tools
- ToolStorage: Per-chat persistent storage for tool data
- ToolExecutor: Execute tool calls with error handling and logging
"""

from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from file_manager_utils import load_json_file_with_backup, save_json_file_atomic

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Metadata about a tool.
    
    Attributes:
        name: Tool identifier (e.g., 'calculator')
        display_name: Human-readable name (e.g., 'Calculator')
        description: Tool description for users
        is_builtin: True for OpenAI tools, False for custom tools
        category: Tool category (e.g., 'computation', 'search', 'data')
    """
    name: str
    display_name: str
    description: str
    is_builtin: bool
    category: str


class BaseTool(ABC):
    """Base class for all custom tools.
    
    When implementing a tool, follow OpenAI best practices:
    - Write clear, detailed function names and descriptions
    - Explicitly describe parameter formats with examples
    - Document when to use (and when NOT to use) the tool
    - Include edge cases in descriptions
    - Use strict schema validation
    - Make invalid states unrepresentable through schema design
    
    Example:
        class CalculatorTool(BaseTool):
            @property
            def name(self) -> str:
                return "calculator"
            
            @property
            def display_name(self) -> str:
                return "Calculator"
            
            @property
            def description(self) -> str:
                return "Evaluate mathematical expressions safely"
            
            def get_openai_tool_definition(self) -> dict[str, Any]:
                return {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": "Evaluates mathematical expressions...",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "expression": {
                                    "type": "string",
                                    "description": "A valid mathematical expression..."
                                }
                            },
                            "required": ["expression"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(
                self, 
                parameters: dict[str, Any],
                storage: 'ToolStorage'
            ) -> dict[str, Any]:
                # Implementation here
                pass
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., 'calculator').
        
        This should be a lowercase, underscore-separated identifier that
        uniquely identifies the tool.
        """
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Calculator').
        
        This is shown to users in the UI.
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for users.
        
        This should clearly explain what the tool does and when to use it.
        """
        pass
    
    @abstractmethod
    def get_openai_tool_definition(self) -> dict[str, Any]:
        """Get OpenAI function tool definition.
        
        Must follow OpenAI function calling best practices:
        - Set "strict": true for schema validation
        - Set "additionalProperties": false to prevent extra params
        - Include detailed descriptions with examples
        - Document edge cases and error conditions
        - Use enums where appropriate to constrain values
        
        Returns:
            Dictionary containing the OpenAI function definition with:
            - type: "function"
            - function: Object with name, description, parameters, and strict=true
        
        Example:
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Evaluates mathematical expressions...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "A valid mathematical expression..."
                            }
                        },
                        "required": ["expression"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        """
        pass
    
    @abstractmethod
    def execute(
        self, 
        parameters: dict[str, Any],
        storage: ToolStorage
    ) -> dict[str, Any]:
        """Execute the tool with given parameters.
        
        Args:
            parameters: Dictionary of parameters from the AI's tool call
            storage: ToolStorage instance for persisting data
        
        Returns:
            Dictionary containing the execution result. Should include:
            - success: Boolean indicating if execution succeeded
            - result: The actual result (if successful)
            - error: Error message (if failed)
        
        Example:
            {
                'success': True,
                'result': 42,
                'expression': '2 + 2'
            }
            
            or
            
            {
                'success': False,
                'error': 'Invalid expression: division by zero'
            }
        """
        pass
    
    def validate_parameters(self, parameters: dict[str, Any]) -> list[str]:
        """Validate parameters and return list of errors.
        
        Override this method to add custom parameter validation beyond
        what OpenAI's schema validation provides.
        
        Args:
            parameters: Dictionary of parameters to validate
        
        Returns:
            List of error messages. Empty list if validation passes.
        
        Example:
            def validate_parameters(self, parameters: dict[str, Any]) -> list[str]:
                errors = []
                if 'expression' in parameters:
                    expr = parameters['expression']
                    if len(expr) > 1000:
                        errors.append('Expression too long (max 1000 characters)')
                return errors
        """
        return []


class ToolRegistry:
    """Registry for managing available tools.
    
    This class maintains a central registry of all available tools,
    both custom backend tools and built-in OpenAI tools.
    
    Example:
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        
        tool = registry.get_tool('calculator')
        if tool:
            result = tool.execute({'expression': '2 + 2'}, storage)
    """
    
    # Built-in OpenAI tools that don't need custom implementation
    BUILTIN_TOOLS = {'web_search'}
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: dict[str, BaseTool] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a custom tool.
        
        Args:
            tool: BaseTool instance to register
        
        Raises:
            ValueError: If tool name conflicts with a built-in tool
            TypeError: If tool doesn't implement BaseTool interface
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must be an instance of BaseTool, got {type(tool)}")
        
        if tool.name in self.BUILTIN_TOOLS:
            raise ValueError(
                f"Cannot register tool '{tool.name}': "
                f"name conflicts with built-in OpenAI tool"
            )
        
        self._tools[tool.name] = tool
    
    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Get a tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
        
        Returns:
            BaseTool instance if found, None otherwise
        
        Note:
            This only returns custom tools. Built-in OpenAI tools
            (like web_search) are not returned.
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> list[ToolInfo]:
        """List all available tools with metadata.
        
        Returns:
            List of ToolInfo objects for all available tools,
            including both custom and built-in tools.
        """
        tools = []
        
        # Add built-in tools
        for builtin_name in self.BUILTIN_TOOLS:
            tools.append(ToolInfo(
                name=builtin_name,
                display_name=builtin_name.replace('_', ' ').title(),
                description=self._get_builtin_description(builtin_name),
                is_builtin=True,
                category='search' if builtin_name == 'web_search' else 'other'
            ))
        
        # Add custom tools
        for tool in self._tools.values():
            tools.append(ToolInfo(
                name=tool.name,
                display_name=tool.display_name,
                description=tool.description,
                is_builtin=False,
                category=self._infer_category(tool)
            ))
        
        return tools
    
    def is_builtin_tool(self, tool_name: str) -> bool:
        """Check if a tool is a built-in OpenAI tool.
        
        Args:
            tool_name: Name of the tool to check
        
        Returns:
            True if the tool is a built-in OpenAI tool, False otherwise
        """
        return tool_name in self.BUILTIN_TOOLS
    
    def _get_builtin_description(self, tool_name: str) -> str:
        """Get description for a built-in tool.
        
        Args:
            tool_name: Name of the built-in tool
        
        Returns:
            Description string for the tool
        """
        descriptions = {
            'web_search': 'Search the internet for current information'
        }
        return descriptions.get(tool_name, 'Built-in OpenAI tool')
    
    def _infer_category(self, tool: BaseTool) -> str:
        """Infer category for a custom tool based on its name.
        
        Args:
            tool: BaseTool instance
        
        Returns:
            Category string (e.g., 'computation', 'data', 'other')
        """
        name_lower = tool.name.lower()
        
        if any(word in name_lower for word in ['calc', 'math', 'compute']):
            return 'computation'
        elif any(word in name_lower for word in ['data', 'store', 'save']):
            return 'data'
        elif any(word in name_lower for word in ['search', 'find', 'query']):
            return 'search'
        else:
            return 'other'



class ToolStorage:
    """Per-chat storage for tool data.
    
    Provides persistent storage for tools that is isolated per chat conversation.
    Each tool gets its own JSON file within the conversation directory.
    
    Storage path structure: static/chats/{username}/{conversation_id}/{tool_name}.json
    
    Features:
    - Thread-safe concurrent access using per-conversation locks
    - Atomic file writes to prevent corruption
    - Automatic directory creation
    - Comprehensive error handling
    
    Example:
        storage = ToolStorage('john', 'conv_123', 'calculator')
        storage.set('history', [{'expr': '2+2', 'result': 4}])
        history = storage.get('history', [])
        storage.delete('history')
        storage.clear()
    """
    
    # Class-level lock management for thread safety
    _conversation_locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()
    
    def __init__(
        self, 
        username: str, 
        conversation_id: str, 
        tool_name: str,
        static_folder: str = 'static'
    ):
        """Initialize storage for a specific tool in a conversation.
        
        Args:
            username: Username who owns the conversation
            conversation_id: Unique identifier for the conversation
            tool_name: Name of the tool using this storage
            static_folder: Base static folder path (default: 'static')
        """
        self.username = username
        self.conversation_id = conversation_id
        self.tool_name = tool_name
        self.static_folder = static_folder
        
        # Build storage path: static/chats/{username}/{conversation_id}/{tool_name}.json
        self.conversation_dir = os.path.join(
            static_folder, 
            'chats', 
            username, 
            conversation_id
        )
        self.storage_file = os.path.join(self.conversation_dir, f'{tool_name}.json')
        
        # Ensure directory exists
        os.makedirs(self.conversation_dir, exist_ok=True)
        
        # Get lock for this conversation
        self._lock = self._get_conversation_lock(username, conversation_id)
    
    @classmethod
    def _get_conversation_lock(cls, username: str, conversation_id: str) -> threading.Lock:
        """Get or create a thread lock for safe concurrent access to conversation data.
        
        Args:
            username: Username who owns the conversation
            conversation_id: Unique identifier for the conversation
        
        Returns:
            Threading lock for the specified conversation
        """
        lock_key = f"{username}:{conversation_id}"
        
        with cls._locks_lock:
            if lock_key not in cls._conversation_locks:
                cls._conversation_locks[lock_key] = threading.Lock()
            return cls._conversation_locks[lock_key]
    
    def _load_data(self) -> dict[str, Any]:
        """Load all data from storage file.
        
        Returns:
            Dictionary containing all stored data, or empty dict if file doesn't exist
        """
        return load_json_file_with_backup(
            self.storage_file,
            f"tool storage ({self.tool_name})",
            self.username,
            {}
        )
    
    def _save_data(self, data: dict[str, Any]) -> None:
        """Save all data to storage file atomically.
        
        Args:
            data: Dictionary containing all data to save
        
        Raises:
            IOError: If file write operation fails
            ValueError: If JSON encoding fails
        """
        save_json_file_atomic(
            self.storage_file,
            data,
            f"tool storage ({self.tool_name})",
            self.username
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from storage.
        
        Args:
            key: Key to retrieve
            default: Default value to return if key doesn't exist
        
        Returns:
            Value associated with key, or default if key not found
        
        Example:
            history = storage.get('history', [])
            count = storage.get('count', 0)
        """
        with self._lock:
            data = self._load_data()
            return data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in storage.
        
        Args:
            key: Key to set
            value: Value to store (must be JSON-serializable)
        
        Raises:
            IOError: If file write operation fails
            ValueError: If value is not JSON-serializable
        
        Example:
            storage.set('history', [{'expr': '2+2', 'result': 4}])
            storage.set('count', 42)
        """
        with self._lock:
            data = self._load_data()
            data[key] = value
            self._save_data(data)
    
    def delete(self, key: str) -> None:
        """Delete a value from storage.
        
        Args:
            key: Key to delete
        
        Note:
            Does nothing if key doesn't exist (no error raised)
        
        Example:
            storage.delete('history')
        """
        with self._lock:
            data = self._load_data()
            if key in data:
                del data[key]
                self._save_data(data)
    
    def get_all(self) -> dict[str, Any]:
        """Get all stored data.
        
        Returns:
            Dictionary containing all stored key-value pairs
        
        Example:
            all_data = storage.get_all()
            print(all_data)  # {'history': [...], 'count': 42}
        """
        with self._lock:
            return self._load_data()
    
    def clear(self) -> None:
        """Clear all stored data.
        
        Removes all key-value pairs from storage.
        
        Example:
            storage.clear()
        """
        with self._lock:
            self._save_data({})



class ToolExecutor:
    """Execute tool calls from OpenAI responses.
    
    This class handles routing tool calls to the appropriate tool implementation,
    managing per-chat storage, and providing comprehensive error handling.
    
    Features:
    - Routes tool calls to registered tools
    - Creates per-chat storage for each tool
    - Comprehensive error handling with structured responses
    - Logging of all tool execution events
    - Graceful degradation on errors
    
    Example:
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        
        executor = ToolExecutor(registry)
        result = executor.execute_tool_call(
            tool_name='calculator',
            parameters={'expression': '2 + 2'},
            username='john',
            conversation_id='conv_123'
        )
        
        if result['success']:
            print(f"Result: {result['result']}")
        else:
            print(f"Error: {result['error']}")
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """Initialize the tool executor.
        
        Args:
            tool_registry: ToolRegistry instance containing registered tools
        """
        self.registry = tool_registry
        logger.info("ToolExecutor initialized")
    
    def execute_tool_call(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        username: str,
        conversation_id: str
    ) -> dict[str, Any]:
        """Execute a tool call and return result.
        
        This method handles the complete tool execution flow:
        1. Validates tool exists in registry
        2. Creates per-chat storage for the tool
        3. Executes the tool with error handling
        4. Logs execution events
        5. Returns structured result
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Dictionary of parameters for the tool
            username: Username who owns the conversation
            conversation_id: Unique identifier for the conversation
        
        Returns:
            Dictionary containing execution result with the following structure:
            
            Success case:
            {
                'success': True,
                'result': <tool-specific result>,
                ... (other tool-specific fields)
            }
            
            Error cases:
            {
                'success': False,
                'error': 'Error message',
                'error_code': 'tool_not_found' | 'execution_error' | 'storage_error',
                'tool_name': <tool name>
            }
        
        Example:
            result = executor.execute_tool_call(
                tool_name='calculator',
                parameters={'expression': '2 + 2'},
                username='john',
                conversation_id='conv_123'
            )
        """
        logger.info(
            f"Executing tool call: tool={tool_name}, user={username}, "
            f"conversation={conversation_id}, params={parameters}"
        )
        
        try:
            # Get tool from registry
            tool = self.registry.get_tool(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found in registry"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': 'tool_not_found',
                    'tool_name': tool_name
                }
            
            # Create storage for this tool in this conversation
            try:
                storage = ToolStorage(username, conversation_id, tool_name)
            except Exception as e:
                error_msg = f"Failed to create storage for tool '{tool_name}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': 'storage_error',
                    'tool_name': tool_name
                }
            
            # Execute tool with error handling
            try:
                result = tool.execute(parameters, storage)
                
                # Log execution result
                if result.get('success'):
                    logger.info(
                        f"Tool execution succeeded: tool={tool_name}, "
                        f"user={username}, conversation={conversation_id}"
                    )
                else:
                    logger.warning(
                        f"Tool execution returned error: tool={tool_name}, "
                        f"error={result.get('error')}"
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(
                    f"Exception during tool execution: tool={tool_name}, "
                    f"user={username}, conversation={conversation_id}",
                    exc_info=True
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': 'execution_error',
                    'tool_name': tool_name
                }
        
        except Exception as e:
            # Catch-all for any unexpected errors
            error_msg = f"Unexpected error during tool execution: {str(e)}"
            logger.error(
                f"Unexpected exception in execute_tool_call: tool={tool_name}",
                exc_info=True
            )
            return {
                'success': False,
                'error': error_msg,
                'error_code': 'execution_error',
                'tool_name': tool_name
            }
