"""Test that reasoning configuration is properly set in API calls."""

import pytest
from unittest.mock import Mock, patch
from app import ResponsesAPIClient


class TestReasoningAPIConfiguration:
    """Test reasoning configuration in API calls."""

    def test_reasoning_config_in_api_call(self, mock_openai_client):
        """Test that detailed reasoning is configured in API calls."""
        client = ResponsesAPIClient(mock_openai_client)
        
        # Mock the responses.create method
        mock_response = Mock()
        mock_openai_client.responses.create.return_value = mock_response
        
        # Call create_response
        result = client.create_response("test input")
        
        # Verify that responses.create was called with correct reasoning config
        mock_openai_client.responses.create.assert_called_once()
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        
        # Check that reasoning is configured correctly
        assert "reasoning" in call_kwargs
        reasoning_config = call_kwargs["reasoning"]
        assert reasoning_config["effort"] == "high"
        assert reasoning_config["summary"] == "detailed"
        
        # Verify other expected parameters
        assert call_kwargs["model"] == "gpt-5"
        assert call_kwargs["input"] == "test input"
        assert call_kwargs["stream"] is True
        assert call_kwargs["store"] is True

    def test_reasoning_config_with_all_parameters(self, mock_openai_client):
        """Test reasoning config with all optional parameters."""
        client = ResponsesAPIClient(mock_openai_client)
        
        mock_response = Mock()
        mock_openai_client.responses.create.return_value = mock_response
        
        # Call with all parameters
        result = client.create_response(
            input_text="test input",
            previous_response_id="prev_123",
            stream=False,
            username="testuser"
        )
        
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        
        # Verify reasoning config is still present
        assert call_kwargs["reasoning"]["effort"] == "high"
        assert call_kwargs["reasoning"]["summary"] == "detailed"
        
        # Verify other parameters
        assert call_kwargs["previous_response_id"] == "prev_123"
        assert call_kwargs["stream"] is False
        assert call_kwargs["user"] == "testuser"

    def test_reasoning_config_preserved_on_error_handling(self, mock_openai_client):
        """Test that reasoning config is preserved even when errors occur."""
        client = ResponsesAPIClient(mock_openai_client)
        
        # Mock a generic error
        mock_openai_client.responses.create.side_effect = Exception("Test error")
        
        # Call create_response (should handle error gracefully)
        result = client.create_response("test input")
        
        # Verify the call was made with correct reasoning config before error
        mock_openai_client.responses.create.assert_called_once()
        call_kwargs = mock_openai_client.responses.create.call_args[1]
        
        assert call_kwargs["reasoning"]["effort"] == "high"
        assert call_kwargs["reasoning"]["summary"] == "detailed"
        
        # Verify error was handled
        assert isinstance(result, dict)
        assert "error" in result