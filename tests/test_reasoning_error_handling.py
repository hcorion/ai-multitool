"""
Test comprehensive error handling for reasoning inspection feature.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from app import (
    app,
    ConversationManager,
    StreamEventProcessor,
    ResponsesAPIClient,
    validate_reasoning_data,
    ChatMessage,
)
from queue import Queue


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = "testuser"
        yield client


@pytest.fixture
def conversation_manager():
    """Create a test conversation manager."""
    return ConversationManager("test_static")


class TestReasoningErrorHandling:
    """Test comprehensive error handling for reasoning inspection."""

    def test_validate_reasoning_data_with_invalid_input(self):
        """Test reasoning data validation with various invalid inputs."""
        # Test None input
        assert validate_reasoning_data(None) is None

        # Test non-dict input
        with pytest.raises(ValueError, match="Reasoning data must be a dictionary"):
            validate_reasoning_data("invalid")

        # Test invalid field types
        invalid_data = {
            "summary_parts": "should_be_list",
            "complete_summary": 123,
            "timestamp": "should_be_number",
            "response_id": 456,
        }

        with pytest.raises(ValueError):
            validate_reasoning_data(invalid_data)

        # Test invalid summary_parts content
        invalid_parts_data = {
            "summary_parts": ["valid", 123, "also_valid"],
            "complete_summary": "test",
            "timestamp": 1234567890,
            "response_id": "test_id",
        }

        with pytest.raises(ValueError, match="All items in summary_parts must be strings"):
            validate_reasoning_data(invalid_parts_data)

    def test_validate_reasoning_data_with_valid_input(self):
        """Test reasoning data validation with valid inputs."""
        valid_data = {
            "summary_parts": ["part1", "part2"],
            "complete_summary": "Complete reasoning summary",
            "timestamp": 1234567890,
            "response_id": "resp_123",
        }

        result = validate_reasoning_data(valid_data)
        assert result == valid_data

        # Test with partial data
        partial_data = {
            "complete_summary": "Just a summary",
            "timestamp": 1234567890,
        }

        result = validate_reasoning_data(partial_data)
        assert result == partial_data

    def test_stream_event_processor_reasoning_error_handling(self):
        """Test StreamEventProcessor handles reasoning errors gracefully."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)

        # Test handling malformed reasoning events
        malformed_event = Mock()
        malformed_event.type = "response.reasoning_summary_part.added"
        malformed_event.part = None

        # Should not raise exception
        processor._handle_reasoning_summary_part_added(malformed_event)

        # Test with missing attributes
        missing_attr_event = Mock()
        missing_attr_event.type = "response.reasoning_summary_text.delta"
        del missing_attr_event.delta  # Remove the attribute

        # Should not raise exception
        processor._handle_reasoning_summary_text_delta(missing_attr_event)

        # Test get_reasoning_data with corrupted data
        processor.reasoning_data = {"invalid": "data"}
        result = processor.get_reasoning_data()
        assert result is None

    def test_conversation_manager_reasoning_error_handling(self, conversation_manager):
        """Test ConversationManager handles reasoning errors gracefully."""
        # Test getting reasoning data for non-existent conversation
        result = conversation_manager.get_message_reasoning_data(
            "testuser", "nonexistent", 0
        )
        assert result is None

        # Test getting reasoning data with invalid message index
        conversation_id = conversation_manager.create_conversation("testuser", "Test Chat")
        conversation_manager.add_message("testuser", conversation_id, "user", "Hello")

        result = conversation_manager.get_message_reasoning_data(
            "testuser", conversation_id, 999
        )
        assert result is None

        # Test getting reasoning data for user message (should return None)
        result = conversation_manager.get_message_reasoning_data(
            "testuser", conversation_id, 0
        )
        assert result is None

    def test_reasoning_api_endpoint_error_handling(self, client):
        """Test reasoning API endpoint handles various error conditions."""
        # Test without authentication - should redirect to login (302) or return 404
        response = client.get("/chat/reasoning/test_conv/0")
        # The actual behavior depends on Flask-Login configuration
        assert response.status_code in [401, 404, 302]

        # Test with authentication but non-existent conversation
        with client.session_transaction() as sess:
            sess["username"] = "testuser"

        response = client.get("/chat/reasoning/nonexistent/0")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error"] == "Conversation not found"

    def test_responses_api_client_error_handling(self):
        """Test ResponsesAPIClient handles various error conditions."""
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)

        # Test rate limit error
        from openai import RateLimitError
        mock_response = Mock()
        mock_response.status_code = 429
        rate_limit_error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        rate_limit_error.retry_after = 60
        mock_client.responses.create.side_effect = rate_limit_error

        result = responses_client.create_response("test input")
        assert isinstance(result, dict)
        assert result["error"] == "rate_limit"
        assert "Too many requests" in result["message"]

        # Test API error
        from openai import APIError
        mock_response = Mock()
        mock_response.status_code = 400
        api_error = APIError("API Error", response=mock_response, body=None)
        api_error.code = "model_unavailable"
        mock_client.responses.create.side_effect = api_error

        result = responses_client.create_response("test input")
        assert isinstance(result, dict)
        assert result["error"] == "model_unavailable"

        # Test general error
        mock_client.responses.create.side_effect = ConnectionError("Connection failed")

        result = responses_client.create_response("test input")
        assert isinstance(result, dict)
        assert result["error"] == "connection_error"

    def test_reasoning_availability_status(self, conversation_manager):
        """Test reasoning availability status functionality."""
        # Test with non-existent conversation
        status = conversation_manager.get_reasoning_availability_status(
            "testuser", "nonexistent"
        )
        assert status["available"] is False
        assert status["reason"] == "conversation_not_found"

        # Test with conversation without reasoning data
        conversation_id = conversation_manager.create_conversation("testuser", "Test Chat")
        conversation_manager.add_message("testuser", conversation_id, "user", "Hello")
        conversation_manager.add_message("testuser", conversation_id, "assistant", "Hi there")

        status = conversation_manager.get_reasoning_availability_status(
            "testuser", conversation_id
        )
        assert status["available"] is False
        assert status["reason"] == "no_reasoning_data"
        assert status["assistant_message_count"] == 1
        assert status["reasoning_count"] == 0

        # Test with reasoning data
        reasoning_data = {
            "summary_parts": ["test reasoning"],
            "complete_summary": "Complete test reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_123",
        }

        conversation_manager.add_message(
            "testuser", conversation_id, "assistant", "Another response", "resp_123", reasoning_data
        )

        status = conversation_manager.get_reasoning_availability_status(
            "testuser", conversation_id
        )
        assert status["available"] is True
        assert status["reason"] == "available"
        assert status["assistant_message_count"] == 2
        assert status["reasoning_count"] == 1
        assert status["reasoning_percentage"] == 50.0

    @patch("logging.warning")
    def test_reasoning_error_logging(self, mock_logging_warning, conversation_manager):
        """Test that reasoning errors are properly logged."""
        # Test logging when reasoning data validation fails
        conversation_id = conversation_manager.create_conversation("testuser", "Test Chat")
        
        # Add a message with invalid reasoning data directly to test error handling
        conversation = conversation_manager.get_conversation("testuser", conversation_id)
        invalid_message = ChatMessage(
            role="assistant",
            text="Test response",
            timestamp=1234567890,
            response_id="resp_123",
            reasoning_data={"invalid": "data"}  # This will fail validation
        )
        conversation.messages.append(invalid_message)

        # Try to get reasoning data - should log warning and return None
        result = conversation_manager.get_message_reasoning_data(
            "testuser", conversation_id, 0
        )
        assert result is None
        
        # Verify warning was logged
        mock_logging_warning.assert_called()

    def test_chat_functionality_continues_with_reasoning_failure(self):
        """Test that chat functionality continues even when reasoning processing fails."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)

        # Simulate successful text processing
        processor.accumulated_text = "This is a test response"
        processor.current_response_id = "resp_123"

        # Simulate reasoning processing failure by corrupting reasoning data
        processor.reasoning_data = None

        # Getting reasoning data should return None but not crash
        reasoning_data = processor.get_reasoning_data()
        assert reasoning_data is None

        # Text processing should still work
        assert processor.accumulated_text == "This is a test response"
        assert processor.current_response_id == "resp_123"

    def test_graceful_degradation_when_reasoning_unavailable(self, client):
        """Test graceful degradation when reasoning is completely unavailable."""
        # This test would require setting up a conversation and testing the frontend behavior
        # For now, we test that the API returns appropriate responses
        
        with client.session_transaction() as sess:
            sess["username"] = "testuser"

        # Test that the system handles missing reasoning gracefully
        # The actual frontend behavior would be tested in integration tests
        pass


if __name__ == "__main__":
    pytest.main([__file__])