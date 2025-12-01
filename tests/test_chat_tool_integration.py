"""Integration tests for chat endpoint tool integration."""

import json
from unittest.mock import Mock, patch

import pytest

from tool_framework import ToolExecutor, ToolRegistry
from tools.calculator_tool import CalculatorTool


class TestChatToolIntegration:
    """Test tool integration in the chat endpoint."""

    @pytest.fixture
    def tool_registry(self):
        """Create a tool registry with calculator tool."""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        return registry

    @pytest.fixture
    def tool_executor(self, tool_registry):
        """Create a tool executor."""
        return ToolExecutor(tool_registry)

    def test_tool_registry_initialization(self, tool_registry):
        """Test that tool registry is properly initialized."""
        # Verify calculator tool is registered
        calculator = tool_registry.get_tool("calculator")
        assert calculator is not None
        assert calculator.name == "calculator"
        assert calculator.display_name == "Calculator"

    def test_tool_executor_initialization(self, tool_executor):
        """Test that tool executor is properly initialized."""
        assert tool_executor is not None
        assert tool_executor.registry is not None

    def test_tool_execution_via_executor(self, tool_executor):
        """Test executing a tool via the executor."""
        result = tool_executor.execute_tool_call(
            tool_name="calculator",
            parameters={"expression": "2 + 2"},
            username="testuser",
            conversation_id="test_conv_123",
        )

        assert result["success"] is True
        assert result["result"] == 4
        assert result["expression"] == "2 + 2"

    def test_tool_execution_not_found(self, tool_executor):
        """Test executing a non-existent tool."""
        result = tool_executor.execute_tool_call(
            tool_name="nonexistent_tool",
            parameters={},
            username="testuser",
            conversation_id="test_conv_123",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["error_code"] == "tool_not_found"

    def test_tool_execution_with_storage(self, tool_executor, tmp_path):
        """Test that tool execution uses per-conversation storage."""
        # Execute multiple calculations
        result1 = tool_executor.execute_tool_call(
            tool_name="calculator",
            parameters={"expression": "10 + 5"},
            username="testuser",
            conversation_id="conv_1",
        )

        result2 = tool_executor.execute_tool_call(
            tool_name="calculator",
            parameters={"expression": "20 * 2"},
            username="testuser",
            conversation_id="conv_1",
        )

        # Both should succeed
        assert result1["success"] is True
        assert result1["result"] == 15

        assert result2["success"] is True
        assert result2["result"] == 40

    def test_stream_event_processor_with_tool_executor(self):
        """Test that StreamEventProcessor can be initialized with tool executor."""
        from queue import Queue

        from app import StreamEventProcessor

        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        executor = ToolExecutor(registry)

        event_queue = Queue()
        processor = StreamEventProcessor(
            event_queue=event_queue,
            tool_executor=executor,
            username="testuser",
            conversation_id="test_conv",
        )

        # Verify processor has tool executor
        assert processor.tool_executor is not None
        assert processor.username == "testuser"
        assert processor.conversation_id == "test_conv"
        assert processor.tool_calls == {}

    def test_agent_preset_enabled_tools_default(self):
        """Test that agent presets have default enabled tools."""
        from app import AgentPreset

        preset = AgentPreset(
            id="test_preset",
            name="Test Preset",
            instructions="Test instructions",
            created_at=1234567890,
            updated_at=1234567890,
        )

        # Should have default tools
        assert "web_search" in preset.enabled_tools
        assert "calculator" in preset.enabled_tools

    def test_agent_preset_custom_enabled_tools(self):
        """Test that agent presets can have custom enabled tools."""
        from app import AgentPreset

        preset = AgentPreset(
            id="test_preset",
            name="Test Preset",
            instructions="Test instructions",
            created_at=1234567890,
            updated_at=1234567890,
            enabled_tools=["web_search"],  # Only web search
        )

        # Should have only web_search
        assert preset.enabled_tools == ["web_search"]

    def test_agent_preset_validates_enabled_tools(self):
        """Test that agent presets validate enabled tools."""
        from app import AgentPreset
        from pydantic import ValidationError

        # Empty tools list should fail
        with pytest.raises(ValidationError) as exc_info:
            AgentPreset(
                id="test_preset",
                name="Test Preset",
                instructions="Test instructions",
                created_at=1234567890,
                updated_at=1234567890,
                enabled_tools=[],  # Empty list
            )

        assert "at least one tool must be enabled" in str(exc_info.value).lower()

    def test_agent_preset_validates_duplicate_tools(self):
        """Test that agent presets reject duplicate tool names."""
        from app import AgentPreset
        from pydantic import ValidationError

        # Duplicate tools should fail
        with pytest.raises(ValidationError) as exc_info:
            AgentPreset(
                id="test_preset",
                name="Test Preset",
                instructions="Test instructions",
                created_at=1234567890,
                updated_at=1234567890,
                enabled_tools=["web_search", "calculator", "web_search"],  # Duplicate
            )

        assert "duplicate" in str(exc_info.value).lower()

    def test_responses_client_receives_enabled_tools(self):
        """Test that ResponsesAPIClient receives enabled_tools parameter."""
        from unittest.mock import MagicMock

        from app import ResponsesAPIClient

        mock_client = MagicMock()
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        responses_client = ResponsesAPIClient(mock_client, tool_registry=registry)

        # Mock the responses.create method
        mock_client.responses.create.return_value = {"id": "test_response"}

        # Call create_response with enabled_tools
        responses_client.create_response(
            input_text="Calculate 2 + 2",
            stream=False,
            enabled_tools=["web_search", "calculator"],
        )

        # Verify that responses.create was called
        assert mock_client.responses.create.called

        # Get the call arguments
        call_args = mock_client.responses.create.call_args
        params = call_args[1] if call_args[1] else call_args[0][0]

        # Verify tools array was built
        assert "tools" in params
        tools = params["tools"]

        # Should have both web_search and calculator
        assert len(tools) == 2

        # Check for web_search
        web_search_tool = next((t for t in tools if t.get("type") == "web_search"), None)
        assert web_search_tool is not None

        # Check for calculator
        calculator_tool = next(
            (t for t in tools if t.get("type") == "function"), None
        )
        assert calculator_tool is not None
        assert calculator_tool["function"]["name"] == "calculator"
