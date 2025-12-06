"""Tests for ResponsesAPIClient tool integration."""

import pytest
from unittest.mock import Mock
from app import ResponsesAPIClient
from tool_framework import ToolRegistry, BaseTool


class MockCalculatorTool(BaseTool):
    """Mock calculator tool for testing."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def display_name(self) -> str:
        return "Calculator"
    
    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions"
    
    def get_openai_tool_definition(self) -> dict:
        return {
            "type": "function",
            "name": "calculator",
            "description": "Evaluates mathematical expressions",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A valid mathematical expression"
                    }
                },
                "required": ["expression"],
                "additionalProperties": False
            },
            "strict": True
        }
    
    def execute(self, parameters: dict, storage) -> dict:
        return {"success": True, "result": 42}


class TestResponsesAPIClientToolIntegration:
    """Test ResponsesAPIClient tool integration."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        return Mock()
    
    @pytest.fixture
    def tool_registry(self):
        """Create a tool registry with calculator tool."""
        registry = ToolRegistry()
        registry.register_tool(MockCalculatorTool())
        return registry
    
    def test_build_tools_array_web_search_only(self, mock_openai_client):
        """Test building tools array with only web_search."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=None)
        
        tools = client._build_tools_array(["web_search"])
        
        assert len(tools) == 1
        assert tools[0]["type"] == "web_search"
        assert "user_location" in tools[0]
        assert tools[0]["user_location"]["country"] == "CA"
    
    def test_build_tools_array_calculator_only(self, mock_openai_client, tool_registry):
        """Test building tools array with only calculator."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=tool_registry)
        
        tools = client._build_tools_array(["calculator"])
        
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["name"] == "calculator"
        assert tools[0]["strict"] is True
    
    def test_build_tools_array_both_tools(self, mock_openai_client, tool_registry):
        """Test building tools array with both web_search and calculator."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=tool_registry)
        
        tools = client._build_tools_array(["web_search", "calculator"])
        
        assert len(tools) == 2
        
        # Check web_search
        web_search = next((t for t in tools if t.get("type") == "web_search"), None)
        assert web_search is not None
        assert "user_location" in web_search
        
        # Check calculator
        calculator = next((t for t in tools if t.get("type") == "function"), None)
        assert calculator is not None
        assert calculator["name"] == "calculator"
    
    def test_build_tools_array_empty_list(self, mock_openai_client, tool_registry):
        """Test building tools array with empty list."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=tool_registry)
        
        tools = client._build_tools_array([])
        
        assert len(tools) == 0
    
    def test_build_tools_array_unknown_tool(self, mock_openai_client, tool_registry):
        """Test building tools array with unknown tool (should skip)."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=tool_registry)
        
        tools = client._build_tools_array(["web_search", "unknown_tool"])
        
        # Should only have web_search, unknown_tool should be skipped
        assert len(tools) == 1
        assert tools[0]["type"] == "web_search"
    
    def test_build_tools_array_no_registry(self, mock_openai_client):
        """Test building tools array without tool registry."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=None)
        
        tools = client._build_tools_array(["web_search", "calculator"])
        
        # Should only have web_search, calculator should be skipped
        assert len(tools) == 1
        assert tools[0]["type"] == "web_search"
    
    def test_create_response_with_enabled_tools(self, mock_openai_client, tool_registry):
        """Test create_response passes enabled_tools to _build_tools_array."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=tool_registry)
        
        # Mock the responses.create method
        mock_openai_client.responses.create.return_value = Mock()
        
        # Call create_response with enabled_tools
        client.create_response(
            input_text="Test message",
            enabled_tools=["web_search", "calculator"]
        )
        
        # Verify responses.create was called
        assert mock_openai_client.responses.create.called
        
        # Get the call arguments
        call_args = mock_openai_client.responses.create.call_args
        params = call_args[1] if call_args[1] else call_args[0][0]
        
        # Verify tools array was built correctly
        tools = params["tools"]
        assert len(tools) == 2
        
        # Check web_search
        web_search = next((t for t in tools if t.get("type") == "web_search"), None)
        assert web_search is not None
        
        # Check calculator
        calculator = next((t for t in tools if t.get("type") == "function"), None)
        assert calculator is not None
        assert calculator["name"] == "calculator"
    
    def test_create_response_default_tools(self, mock_openai_client):
        """Test create_response uses default tools when enabled_tools is None."""
        client = ResponsesAPIClient(mock_openai_client, tool_registry=None)
        
        # Mock the responses.create method
        mock_openai_client.responses.create.return_value = Mock()
        
        # Call create_response without enabled_tools
        client.create_response(input_text="Test message")
        
        # Verify responses.create was called
        assert mock_openai_client.responses.create.called
        
        # Get the call arguments
        call_args = mock_openai_client.responses.create.call_args
        params = call_args[1] if call_args[1] else call_args[0][0]
        
        # Verify default tools (web_search) was used
        tools = params["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "web_search"
