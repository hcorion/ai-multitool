"""Tests for reasoning data capture and stream processing functionality."""

import json
import pytest
from queue import Queue
from unittest.mock import Mock, MagicMock
from app import StreamEventProcessor, validate_reasoning_data, ResponsesAPIClient


class TestReasoningDataValidation:
    """Test reasoning data validation functionality."""

    def test_validate_reasoning_data_valid(self):
        """Test validation with valid reasoning data."""
        valid_data = {
            "summary_parts": ["Part 1", "Part 2"],
            "complete_summary": "Complete reasoning summary",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        
        result = validate_reasoning_data(valid_data)
        assert result == valid_data

    def test_validate_reasoning_data_none(self):
        """Test validation with None input."""
        result = validate_reasoning_data(None)
        assert result is None

    def test_validate_reasoning_data_invalid_type(self):
        """Test validation with invalid data type."""
        with pytest.raises(ValueError, match="Reasoning data must be a dictionary"):
            validate_reasoning_data("invalid")

    def test_validate_reasoning_data_invalid_field_type(self):
        """Test validation with invalid field types."""
        invalid_data = {
            "summary_parts": "should be list",
            "complete_summary": "Valid summary",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        
        with pytest.raises(ValueError, match="Reasoning data field 'summary_parts' must be of type"):
            validate_reasoning_data(invalid_data)

    def test_validate_reasoning_data_invalid_summary_parts(self):
        """Test validation with invalid summary_parts content."""
        invalid_data = {
            "summary_parts": ["Valid part", 123],  # 123 is not a string
            "complete_summary": "Valid summary",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        
        with pytest.raises(ValueError, match="All items in summary_parts must be strings"):
            validate_reasoning_data(invalid_data)


class TestStreamEventProcessor:
    """Test StreamEventProcessor reasoning functionality."""

    def test_initialization(self):
        """Test StreamEventProcessor initialization with reasoning data."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        assert processor.reasoning_data == {
            "summary_parts": [],
            "complete_summary": "",
            "timestamp": 0,
            "response_id": "",
        }

    def test_handle_response_created_resets_reasoning(self):
        """Test that response.created event resets reasoning data."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        # Set some initial reasoning data
        processor.reasoning_data["summary_parts"] = ["old part"]
        processor.reasoning_data["complete_summary"] = "old summary"
        
        # Create mock event
        mock_event = Mock()
        mock_event.response = Mock()
        mock_event.response.id = "resp_123"
        
        # Handle response created
        processor._handle_response_created(mock_event)
        
        # Check that reasoning data was reset
        assert processor.reasoning_data == {
            "summary_parts": [],
            "complete_summary": "",
            "timestamp": 0,
            "response_id": "",
        }
        assert processor.current_response_id == "resp_123"

    def test_handle_reasoning_summary_part_added(self):
        """Test handling of reasoning summary part added events."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        # Create mock event with part text
        mock_event = Mock()
        mock_event.part = Mock()
        mock_event.part.text = "Reasoning part 1"
        
        processor._handle_reasoning_summary_part_added(mock_event)
        
        assert processor.reasoning_data["summary_parts"] == ["Reasoning part 1"]

    def test_handle_reasoning_summary_text_delta(self):
        """Test handling of reasoning summary text delta events."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        # Create mock event with delta text
        mock_event = Mock()
        mock_event.delta = Mock()
        mock_event.delta.text = "Delta text"
        
        processor._handle_reasoning_summary_text_delta(mock_event)
        
        assert processor.reasoning_data["complete_summary"] == "Delta text"
        
        # Test accumulation
        processor._handle_reasoning_summary_text_delta(mock_event)
        assert processor.reasoning_data["complete_summary"] == "Delta textDelta text"

    def test_handle_reasoning_summary_text_done(self):
        """Test handling of reasoning summary text done events."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        processor.current_response_id = "resp_123"
        
        # Create mock event with final text
        mock_event = Mock()
        mock_event.text = "Final reasoning summary"
        
        processor._handle_reasoning_summary_text_done(mock_event)
        
        assert processor.reasoning_data["complete_summary"] == "Final reasoning summary"
        assert processor.reasoning_data["response_id"] == "resp_123"
        assert processor.reasoning_data["timestamp"] > 0

    def test_get_reasoning_data_with_content(self):
        """Test getting reasoning data when content exists."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        processor.current_response_id = "resp_123"
        
        # Set up reasoning data
        processor.reasoning_data["summary_parts"] = ["Part 1", "Part 2"]
        processor.reasoning_data["complete_summary"] = "Complete summary"
        processor.reasoning_data["timestamp"] = 1234567890
        processor.reasoning_data["response_id"] = "resp_123"
        
        result = processor.get_reasoning_data()
        
        assert result is not None
        assert result["summary_parts"] == ["Part 1", "Part 2"]
        assert result["complete_summary"] == "Complete summary"
        assert result["response_id"] == "resp_123"

    def test_get_reasoning_data_empty(self):
        """Test getting reasoning data when no content exists."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        result = processor.get_reasoning_data()
        assert result is None

    def test_reasoning_event_handling_in_stream(self):
        """Test that reasoning events are properly handled in stream processing."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        # Create mock reasoning events
        reasoning_part_event = Mock()
        reasoning_part_event.type = "response.reasoning_summary_part.added"
        reasoning_part_event.part = "Reasoning step 1"
        
        reasoning_delta_event = Mock()
        reasoning_delta_event.type = "response.reasoning_summary_text.delta"
        reasoning_delta_event.delta = "Delta reasoning"
        
        reasoning_done_event = Mock()
        reasoning_done_event.type = "response.reasoning_summary_text.done"
        reasoning_done_event.text = "Final reasoning that is longer than delta"
        
        # Process events
        processor._handle_stream_event(reasoning_part_event)
        processor._handle_stream_event(reasoning_delta_event)
        processor._handle_stream_event(reasoning_done_event)
        
        # Check that reasoning data was captured
        assert processor.reasoning_data["summary_parts"] == ["Reasoning step 1"]
        # The final text should override the delta since it's longer
        assert processor.reasoning_data["complete_summary"] == "Final reasoning that is longer than delta"

    def test_error_handling_in_reasoning_methods(self):
        """Test error handling in reasoning event processing methods."""
        queue = Queue()
        processor = StreamEventProcessor(queue)
        
        # Create mock event that will cause an error
        mock_event = Mock()
        mock_event.part = None  # This should be handled gracefully
        mock_event.delta = None
        mock_event.text = None
        
        # These should not raise exceptions, just log warnings
        processor._handle_reasoning_summary_part_added(mock_event)
        processor._handle_reasoning_summary_text_delta(mock_event)
        processor._handle_reasoning_summary_text_done(mock_event)
        
        # Reasoning data should remain in initial state (None values should be filtered out)
        assert processor.reasoning_data["summary_parts"] == []
        assert processor.reasoning_data["complete_summary"] == ""


class TestResponsesAPIClientReasoning:
    """Test ResponsesAPIClient reasoning configuration."""

    def test_create_response_includes_detailed_reasoning(self, mock_openai_client):
        """Test that create_response includes detailed reasoning configuration."""
        client = ResponsesAPIClient(mock_openai_client)
        
        # Mock the responses.create method
        mock_response = Mock()
        mock_openai_client.responses.create.return_value = mock_response
        
        # Call create_response
        result = client.create_response("test input", stream=True)
        
        # Verify that responses.create was called with detailed reasoning
        mock_openai_client.responses.create.assert_called_once()
        call_args = mock_openai_client.responses.create.call_args[1]
        
        assert "reasoning" in call_args
        assert call_args["reasoning"]["effort"] == "high"
        assert call_args["reasoning"]["summary"] == "detailed"
        assert result == mock_response

    def test_create_response_with_previous_response_id(self, mock_openai_client):
        """Test create_response with previous response ID and reasoning."""
        client = ResponsesAPIClient(mock_openai_client)
        
        mock_response = Mock()
        mock_openai_client.responses.create.return_value = mock_response
        
        result = client.create_response(
            "test input", 
            previous_response_id="prev_123",
            username="testuser"
        )
        
        call_args = mock_openai_client.responses.create.call_args[1]
        
        assert call_args["previous_response_id"] == "prev_123"
        assert call_args["user"] == "testuser"
        assert call_args["reasoning"]["summary"] == "detailed"