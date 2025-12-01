"""Tests for the tool framework infrastructure."""

import pytest
from tool_framework import BaseTool, ToolRegistry, ToolInfo


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def display_name(self) -> str:
        return "Mock Tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    def get_openai_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "mock_tool",
                "description": "A mock tool for testing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_param": {
                            "type": "string",
                            "description": "A test parameter"
                        }
                    },
                    "required": ["test_param"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    
    def execute(self, parameters: dict, storage) -> dict:
        return {
            "success": True,
            "result": f"Executed with {parameters.get('test_param')}"
        }


class TestToolInfo:
    """Tests for ToolInfo dataclass."""
    
    def test_tool_info_creation(self):
        """Test creating a ToolInfo instance."""
        info = ToolInfo(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool",
            is_builtin=False,
            category="computation"
        )
        
        assert info.name == "test_tool"
        assert info.display_name == "Test Tool"
        assert info.description == "A test tool"
        assert info.is_builtin is False
        assert info.category == "computation"


class TestBaseTool:
    """Tests for BaseTool abstract base class."""
    
    def test_cannot_instantiate_base_tool(self):
        """Test that BaseTool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore
    
    def test_mock_tool_implements_interface(self):
        """Test that MockTool properly implements BaseTool interface."""
        tool = MockTool()
        
        assert tool.name == "mock_tool"
        assert tool.display_name == "Mock Tool"
        assert tool.description == "A mock tool for testing"
        
        definition = tool.get_openai_tool_definition()
        assert definition["type"] == "function"
        assert definition["function"]["name"] == "mock_tool"
        assert definition["function"]["strict"] is True
        
        result = tool.execute({"test_param": "value"}, None)
        assert result["success"] is True
        assert "value" in result["result"]
    
    def test_validate_parameters_default(self):
        """Test default validate_parameters returns empty list."""
        tool = MockTool()
        errors = tool.validate_parameters({"test_param": "value"})
        assert errors == []


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test creating a new registry."""
        registry = ToolRegistry()
        assert registry is not None
    
    def test_register_tool(self):
        """Test registering a custom tool."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register_tool(tool)
        
        retrieved = registry.get_tool("mock_tool")
        assert retrieved is not None
        assert retrieved.name == "mock_tool"
    
    def test_register_invalid_tool(self):
        """Test registering an invalid tool raises TypeError."""
        registry = ToolRegistry()
        
        with pytest.raises(TypeError, match="must be an instance of BaseTool"):
            registry.register_tool("not a tool")  # type: ignore
    
    def test_register_builtin_name_conflict(self):
        """Test registering a tool with built-in name raises ValueError."""
        registry = ToolRegistry()
        
        class WebSearchTool(BaseTool):
            @property
            def name(self) -> str:
                return "web_search"
            
            @property
            def display_name(self) -> str:
                return "Web Search"
            
            @property
            def description(self) -> str:
                return "Search the web"
            
            def get_openai_tool_definition(self) -> dict:
                return {}
            
            def execute(self, parameters: dict, storage) -> dict:
                return {}
        
        tool = WebSearchTool()
        with pytest.raises(ValueError, match="conflicts with built-in OpenAI tool"):
            registry.register_tool(tool)
    
    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist returns None."""
        registry = ToolRegistry()
        
        tool = registry.get_tool("nonexistent")
        assert tool is None
    
    def test_is_builtin_tool(self):
        """Test checking if a tool is built-in."""
        registry = ToolRegistry()
        
        assert registry.is_builtin_tool("web_search") is True
        assert registry.is_builtin_tool("calculator") is False
        assert registry.is_builtin_tool("nonexistent") is False
    
    def test_list_tools_empty(self):
        """Test listing tools when only built-ins exist."""
        registry = ToolRegistry()
        
        tools = registry.list_tools()
        
        # Should have at least web_search
        assert len(tools) >= 1
        
        web_search = next((t for t in tools if t.name == "web_search"), None)
        assert web_search is not None
        assert web_search.is_builtin is True
        assert web_search.category == "search"
    
    def test_list_tools_with_custom(self):
        """Test listing tools includes custom tools."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register_tool(tool)
        
        tools = registry.list_tools()
        
        # Should have web_search + mock_tool
        assert len(tools) >= 2
        
        mock_tool_info = next((t for t in tools if t.name == "mock_tool"), None)
        assert mock_tool_info is not None
        assert mock_tool_info.display_name == "Mock Tool"
        assert mock_tool_info.is_builtin is False
    
    def test_category_inference_computation(self):
        """Test category inference for computation tools."""
        registry = ToolRegistry()
        
        class CalcTool(BaseTool):
            @property
            def name(self) -> str:
                return "calculator"
            
            @property
            def display_name(self) -> str:
                return "Calculator"
            
            @property
            def description(self) -> str:
                return "Calculate things"
            
            def get_openai_tool_definition(self) -> dict:
                return {}
            
            def execute(self, parameters: dict, storage) -> dict:
                return {}
        
        tool = CalcTool()
        registry.register_tool(tool)
        
        tools = registry.list_tools()
        calc_info = next((t for t in tools if t.name == "calculator"), None)
        assert calc_info is not None
        assert calc_info.category == "computation"



class TestToolStorage:
    """Tests for ToolStorage class."""
    
    def test_storage_initialization(self, tmp_path):
        """Test creating a ToolStorage instance."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        assert storage.username == "testuser"
        assert storage.conversation_id == "conv_123"
        assert storage.tool_name == "calculator"
        
        # Check that directory was created
        expected_dir = tmp_path / "chats" / "testuser" / "conv_123"
        assert expected_dir.exists()
    
    def test_set_and_get(self, tmp_path):
        """Test setting and getting values."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Set a value
        storage.set("count", 42)
        
        # Get the value
        value = storage.get("count")
        assert value == 42
    
    def test_get_with_default(self, tmp_path):
        """Test getting a non-existent key returns default."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Get non-existent key with default
        value = storage.get("nonexistent", "default_value")
        assert value == "default_value"
        
        # Get non-existent key without default
        value = storage.get("nonexistent")
        assert value is None
    
    def test_set_complex_data(self, tmp_path):
        """Test storing complex data structures."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Store a list of dictionaries
        history = [
            {"expression": "2+2", "result": 4},
            {"expression": "10*5", "result": 50}
        ]
        storage.set("history", history)
        
        # Retrieve and verify
        retrieved = storage.get("history")
        assert retrieved == history
        assert len(retrieved) == 2
        assert retrieved[0]["result"] == 4
    
    def test_delete(self, tmp_path):
        """Test deleting a key."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Set a value
        storage.set("temp", "value")
        assert storage.get("temp") == "value"
        
        # Delete it
        storage.delete("temp")
        assert storage.get("temp") is None
    
    def test_delete_nonexistent(self, tmp_path):
        """Test deleting a non-existent key doesn't raise error."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Should not raise an error
        storage.delete("nonexistent")
    
    def test_get_all(self, tmp_path):
        """Test getting all stored data."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Set multiple values
        storage.set("key1", "value1")
        storage.set("key2", 42)
        storage.set("key3", [1, 2, 3])
        
        # Get all data
        all_data = storage.get_all()
        assert len(all_data) == 3
        assert all_data["key1"] == "value1"
        assert all_data["key2"] == 42
        assert all_data["key3"] == [1, 2, 3]
    
    def test_clear(self, tmp_path):
        """Test clearing all stored data."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Set multiple values
        storage.set("key1", "value1")
        storage.set("key2", 42)
        
        # Clear all data
        storage.clear()
        
        # Verify all data is gone
        all_data = storage.get_all()
        assert len(all_data) == 0
        assert storage.get("key1") is None
        assert storage.get("key2") is None
    
    def test_persistence_across_instances(self, tmp_path):
        """Test that data persists across ToolStorage instances."""
        from tool_framework import ToolStorage
        
        # Create first instance and store data
        storage1 = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        storage1.set("persistent", "data")
        
        # Create second instance with same parameters
        storage2 = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        # Data should be accessible from second instance
        value = storage2.get("persistent")
        assert value == "data"
    
    def test_isolation_between_tools(self, tmp_path):
        """Test that different tools have isolated storage."""
        from tool_framework import ToolStorage
        
        # Create storage for calculator tool
        calc_storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        calc_storage.set("data", "calculator_data")
        
        # Create storage for different tool in same conversation
        other_storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="other_tool",
            static_folder=str(tmp_path)
        )
        other_storage.set("data", "other_data")
        
        # Verify isolation
        assert calc_storage.get("data") == "calculator_data"
        assert other_storage.get("data") == "other_data"
    
    def test_isolation_between_conversations(self, tmp_path):
        """Test that different conversations have isolated storage."""
        from tool_framework import ToolStorage
        
        # Create storage for first conversation
        storage1 = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        storage1.set("data", "conv1_data")
        
        # Create storage for second conversation
        storage2 = ToolStorage(
            username="testuser",
            conversation_id="conv_456",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        storage2.set("data", "conv2_data")
        
        # Verify isolation
        assert storage1.get("data") == "conv1_data"
        assert storage2.get("data") == "conv2_data"
    
    def test_isolation_between_users(self, tmp_path):
        """Test that different users have isolated storage."""
        from tool_framework import ToolStorage
        
        # Create storage for first user
        storage1 = ToolStorage(
            username="user1",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        storage1.set("data", "user1_data")
        
        # Create storage for second user
        storage2 = ToolStorage(
            username="user2",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        storage2.set("data", "user2_data")
        
        # Verify isolation
        assert storage1.get("data") == "user1_data"
        assert storage2.get("data") == "user2_data"
    
    def test_thread_safety(self, tmp_path):
        """Test that storage operations are thread-safe.
        
        This test verifies that concurrent set operations don't corrupt the file.
        Each thread writes to a different key to avoid read-modify-write races.
        """
        import threading
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        results = []
        
        def write_data(thread_id):
            # Each thread writes to its own key
            for i in range(50):
                storage.set(f"thread_{thread_id}_item_{i}", f"value_{i}")
            results.append(thread_id)
        
        # Run multiple threads
        threads = [threading.Thread(target=write_data, args=(i,)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Verify all threads completed
        assert len(results) == 5
        
        # Verify all data was written correctly
        all_data = storage.get_all()
        for thread_id in range(5):
            for i in range(50):
                key = f"thread_{thread_id}_item_{i}"
                assert key in all_data
                assert all_data[key] == f"value_{i}"
    
    def test_storage_file_path_structure(self, tmp_path):
        """Test that storage file is created in correct location."""
        from tool_framework import ToolStorage
        
        storage = ToolStorage(
            username="testuser",
            conversation_id="conv_123",
            tool_name="calculator",
            static_folder=str(tmp_path)
        )
        
        storage.set("test", "value")
        
        # Check file exists at expected path
        expected_file = tmp_path / "chats" / "testuser" / "conv_123" / "calculator.json"
        assert expected_file.exists()
        
        # Verify file contains correct data
        import json
        with open(expected_file, 'r') as f:
            data = json.load(f)
        assert data["test"] == "value"



class TestToolExecutor:
    """Tests for ToolExecutor class."""
    
    def test_executor_initialization(self):
        """Test creating a ToolExecutor instance."""
        from tool_framework import ToolExecutor, ToolRegistry
        
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        
        assert executor is not None
        assert executor.registry is registry
    
    def test_execute_tool_call_success(self, tmp_path):
        """Test successful tool execution."""
        from tool_framework import ToolExecutor, ToolRegistry
        
        # Set up registry with mock tool
        registry = ToolRegistry()
        tool = MockTool()
        registry.register_tool(tool)
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute tool call
        result = executor.execute_tool_call(
            tool_name="mock_tool",
            parameters={"test_param": "test_value"},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify success
        assert result["success"] is True
        assert "test_value" in result["result"]
    
    def test_execute_tool_not_found(self, tmp_path):
        """Test executing a non-existent tool."""
        from tool_framework import ToolExecutor, ToolRegistry
        
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        
        # Execute non-existent tool
        result = executor.execute_tool_call(
            tool_name="nonexistent_tool",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify error response
        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["error_code"] == "tool_not_found"
        assert result["tool_name"] == "nonexistent_tool"
    
    def test_execute_tool_with_storage(self, tmp_path):
        """Test that tool receives proper storage instance."""
        from tool_framework import ToolExecutor, ToolRegistry, BaseTool, ToolStorage
        
        # Create a tool that uses storage
        class StorageTool(BaseTool):
            @property
            def name(self) -> str:
                return "storage_tool"
            
            @property
            def display_name(self) -> str:
                return "Storage Tool"
            
            @property
            def description(self) -> str:
                return "A tool that uses storage"
            
            def get_openai_tool_definition(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "storage_tool",
                        "description": "Test storage",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(self, parameters: dict, storage: ToolStorage) -> dict:
                # Store and retrieve data
                storage.set("test_key", "test_value")
                value = storage.get("test_key")
                return {
                    "success": True,
                    "stored_value": value
                }
        
        # Set up registry
        registry = ToolRegistry()
        tool = StorageTool()
        registry.register_tool(tool)
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute tool call
        result = executor.execute_tool_call(
            tool_name="storage_tool",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify storage was used
        assert result["success"] is True
        assert result["stored_value"] == "test_value"
    
    def test_execute_tool_exception_handling(self, tmp_path):
        """Test that tool execution exceptions are caught and handled."""
        from tool_framework import ToolExecutor, ToolRegistry, BaseTool
        
        # Create a tool that raises an exception
        class FailingTool(BaseTool):
            @property
            def name(self) -> str:
                return "failing_tool"
            
            @property
            def display_name(self) -> str:
                return "Failing Tool"
            
            @property
            def description(self) -> str:
                return "A tool that fails"
            
            def get_openai_tool_definition(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "failing_tool",
                        "description": "Test failure",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(self, parameters: dict, storage) -> dict:
                raise RuntimeError("Tool execution failed")
        
        # Set up registry
        registry = ToolRegistry()
        tool = FailingTool()
        registry.register_tool(tool)
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute tool call
        result = executor.execute_tool_call(
            tool_name="failing_tool",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify error is caught and returned
        assert result["success"] is False
        assert "Tool execution failed" in result["error"]
        assert result["error_code"] == "execution_error"
        assert result["tool_name"] == "failing_tool"
    
    def test_execute_tool_with_invalid_parameters(self, tmp_path):
        """Test tool execution with invalid parameters."""
        from tool_framework import ToolExecutor, ToolRegistry, BaseTool
        
        # Create a tool that validates parameters
        class ValidatingTool(BaseTool):
            @property
            def name(self) -> str:
                return "validating_tool"
            
            @property
            def display_name(self) -> str:
                return "Validating Tool"
            
            @property
            def description(self) -> str:
                return "A tool that validates parameters"
            
            def get_openai_tool_definition(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "validating_tool",
                        "description": "Test validation",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "value": {
                                    "type": "number",
                                    "description": "A number"
                                }
                            },
                            "required": ["value"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(self, parameters: dict, storage) -> dict:
                value = parameters.get("value")
                if value < 0:
                    return {
                        "success": False,
                        "error": "Value must be non-negative"
                    }
                return {
                    "success": True,
                    "result": value * 2
                }
        
        # Set up registry
        registry = ToolRegistry()
        tool = ValidatingTool()
        registry.register_tool(tool)
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute with invalid parameter
        result = executor.execute_tool_call(
            tool_name="validating_tool",
            parameters={"value": -5},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify tool returned error
        assert result["success"] is False
        assert "non-negative" in result["error"]
    
    def test_execute_multiple_tools_isolated_storage(self, tmp_path):
        """Test that multiple tools have isolated storage."""
        from tool_framework import ToolExecutor, ToolRegistry, BaseTool, ToolStorage
        
        # Create two tools that use storage
        class Tool1(BaseTool):
            @property
            def name(self) -> str:
                return "tool1"
            
            @property
            def display_name(self) -> str:
                return "Tool 1"
            
            @property
            def description(self) -> str:
                return "First tool"
            
            def get_openai_tool_definition(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "tool1",
                        "description": "Test tool 1",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(self, parameters: dict, storage: ToolStorage) -> dict:
                storage.set("data", "tool1_data")
                return {"success": True, "data": storage.get("data")}
        
        class Tool2(BaseTool):
            @property
            def name(self) -> str:
                return "tool2"
            
            @property
            def display_name(self) -> str:
                return "Tool 2"
            
            @property
            def description(self) -> str:
                return "Second tool"
            
            def get_openai_tool_definition(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": "tool2",
                        "description": "Test tool 2",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            
            def execute(self, parameters: dict, storage: ToolStorage) -> dict:
                storage.set("data", "tool2_data")
                return {"success": True, "data": storage.get("data")}
        
        # Set up registry
        registry = ToolRegistry()
        registry.register_tool(Tool1())
        registry.register_tool(Tool2())
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute both tools
        result1 = executor.execute_tool_call(
            tool_name="tool1",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        result2 = executor.execute_tool_call(
            tool_name="tool2",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify storage is isolated
        assert result1["success"] is True
        assert result1["data"] == "tool1_data"
        
        assert result2["success"] is True
        assert result2["data"] == "tool2_data"
    
    def test_execute_tool_logging(self, tmp_path, caplog):
        """Test that tool execution is logged."""
        import logging
        from tool_framework import ToolExecutor, ToolRegistry
        
        # Set up logging
        caplog.set_level(logging.INFO)
        
        # Set up registry with mock tool
        registry = ToolRegistry()
        tool = MockTool()
        registry.register_tool(tool)
        
        # Create executor
        executor = ToolExecutor(registry)
        
        # Execute tool call
        executor.execute_tool_call(
            tool_name="mock_tool",
            parameters={"test_param": "test_value"},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify logging occurred
        assert any("Executing tool call" in record.message for record in caplog.records)
        assert any("Tool execution succeeded" in record.message for record in caplog.records)
    
    def test_execute_tool_error_logging(self, tmp_path, caplog):
        """Test that tool execution errors are logged."""
        import logging
        from tool_framework import ToolExecutor, ToolRegistry
        
        # Set up logging
        caplog.set_level(logging.ERROR)
        
        # Set up registry
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        
        # Execute non-existent tool
        executor.execute_tool_call(
            tool_name="nonexistent_tool",
            parameters={},
            username="testuser",
            conversation_id="conv_123"
        )
        
        # Verify error logging occurred
        assert any("not found" in record.message.lower() for record in caplog.records)
