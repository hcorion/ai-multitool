"""Core reasoning functionality tests - consolidated from multiple test files."""

import json
import pytest
import tempfile
import time
from queue import Queue
from unittest.mock import Mock, patch, MagicMock
from app import (
    app,
    ConversationManager,
    StreamEventProcessor,
    ResponsesAPIClient,
    validate_reasoning_data,
    ChatMessage,
    Conversation,
    ConversationData,
)


class TestReasoningDataValidation:
    """Test reasoning data validation functionality."""

    def test_validate_reasoning_data_valid(self):
        """Test validation with valid reasoning data."""
        valid_data = {
            "summary_parts": ["Part 1", "Part 2"],
            "complete_summary": "Complete reasoning summary",
            "timestamp": 1234567890,
            "response_id": "resp_123",
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

    def test_validate_reasoning_data_invalid_field_types(self):
        """Test validation with invalid field types."""
        invalid_data = {
            "summary_parts": "should_be_list",
            "complete_summary": 123,
            "timestamp": "should_be_number",
            "response_id": 456,
        }

        with pytest.raises(ValueError):
            validate_reasoning_data(invalid_data)

    def test_validate_reasoning_data_invalid_summary_parts_content(self):
        """Test validation with invalid summary_parts content."""
        invalid_parts_data = {
            "summary_parts": ["valid", 123, "also_valid"],
            "complete_summary": "test",
            "timestamp": 1234567890,
            "response_id": "test_id",
        }

        with pytest.raises(
            ValueError, match="All items in summary_parts must be strings"
        ):
            validate_reasoning_data(invalid_parts_data)


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
            username="testuser",
        )

        call_kwargs = mock_openai_client.responses.create.call_args[1]

        # Verify reasoning config is still present
        assert call_kwargs["reasoning"]["effort"] == "high"
        assert call_kwargs["reasoning"]["summary"] == "detailed"

        # Verify other parameters
        assert call_kwargs["previous_response_id"] == "prev_123"
        assert call_kwargs["stream"] is False
        assert call_kwargs["user"] == "testuser"

    def test_error_handling_preserves_reasoning_config(self, mock_openai_client):
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


class TestConversationManagerReasoning:
    """Test ConversationManager reasoning data functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def conversation_manager(self, temp_dir):
        """Create a ConversationManager instance for testing."""
        return ConversationManager(temp_dir)

    def test_get_message_reasoning_data_valid(self, conversation_manager):
        """Test retrieving valid reasoning data by message index."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add a user message (no reasoning data)
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )

        # Add an assistant message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1: Analyze request", "Step 2: Generate response"],
            "complete_summary": "User is greeting. I should respond politely.",
            "timestamp": 1234567890,
            "response_id": "resp_123",
        }

        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Hello! How can I help?",
            "resp_123",
            reasoning_data,
        )

        # Test retrieving reasoning data
        retrieved_data = conversation_manager.get_message_reasoning_data(
            username,
            conversation_id,
            1,  # Assistant message index
        )

        assert retrieved_data is not None
        assert retrieved_data["summary_parts"] == [
            "Step 1: Analyze request",
            "Step 2: Generate response",
        ]
        assert (
            retrieved_data["complete_summary"]
            == "User is greeting. I should respond politely."
        )
        assert retrieved_data["response_id"] == "resp_123"

    def test_get_message_reasoning_data_no_data(self, conversation_manager):
        """Test retrieving reasoning data when none exists."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add a message without reasoning data
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )

        # Test retrieving reasoning data (should return None)
        retrieved_data = conversation_manager.get_message_reasoning_data(
            username, conversation_id, 0
        )

        assert retrieved_data is None

    def test_get_message_reasoning_data_invalid_cases(self, conversation_manager):
        """Test retrieving reasoning data with invalid inputs."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add one message
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )

        # Test with invalid indices
        assert (
            conversation_manager.get_message_reasoning_data(
                username, conversation_id, -1
            )
            is None
        )
        assert (
            conversation_manager.get_message_reasoning_data(
                username, conversation_id, 1
            )
            is None
        )
        assert (
            conversation_manager.get_message_reasoning_data(
                username, conversation_id, 999
            )
            is None
        )

        # Test with invalid conversation
        assert (
            conversation_manager.get_message_reasoning_data(username, "fake-id", 0)
            is None
        )

    def test_has_reasoning_data(self, conversation_manager):
        """Test checking if a message has reasoning data."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add message without reasoning data
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )

        # Add message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1"],
            "complete_summary": "Summary",
            "timestamp": 1234567890,
            "response_id": "resp_123",
        }
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Response",
            "resp_123",
            reasoning_data,
        )

        # Test has_reasoning_data
        assert (
            conversation_manager.has_reasoning_data(username, conversation_id, 0)
            is False
        )
        assert (
            conversation_manager.has_reasoning_data(username, conversation_id, 1)
            is True
        )
        assert (
            conversation_manager.has_reasoning_data(username, conversation_id, 999)
            is False
        )

    def test_reasoning_data_persistence(self, temp_dir):
        """Test that reasoning data persists across ConversationManager instances."""
        username = "testuser"

        # Create first manager instance and add data
        manager1 = ConversationManager(temp_dir)
        conversation_id = manager1.create_conversation(username, "Test Chat")

        reasoning_data = {
            "summary_parts": ["Persistent step"],
            "complete_summary": "This should persist",
            "timestamp": 1234567890,
            "response_id": "resp_persist",
        }

        manager1.add_message(
            username,
            conversation_id,
            "assistant",
            "Persistent message",
            "resp_persist",
            reasoning_data,
        )

        # Create second manager instance and retrieve data
        manager2 = ConversationManager(temp_dir)
        retrieved_data = manager2.get_message_reasoning_data(
            username, conversation_id, 0
        )

        assert retrieved_data is not None
        assert retrieved_data["complete_summary"] == "This should persist"
        assert retrieved_data["response_id"] == "resp_persist"


class TestReasoningAPIEndpoint:
    """Test the /chat/reasoning/<conversation_id>/<message_index> endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def setup_conversation_with_reasoning(self, temp_dir):
        """Set up a conversation with reasoning data for testing."""
        # Create conversation manager
        conversation_manager = ConversationManager(temp_dir)

        # Replace the global conversation_manager for testing
        import app

        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager

        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add user message
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello, how are you?", None, None
        )

        # Add assistant message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1: Analyze greeting", "Step 2: Respond politely"],
            "complete_summary": "User is greeting me. I should respond politely and ask how I can help.",
            "timestamp": 1234567890,
            "response_id": "resp_123",
        }
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Hello! I'm doing well, thank you. How can I help you today?",
            "resp_123",
            reasoning_data,
        )

        # Add another assistant message without reasoning data
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Of course! I'd be happy to help you with Python.",
            "resp_124",
            None,
        )

        yield {
            "username": username,
            "conversation_id": conversation_id,
            "conversation_manager": conversation_manager,
        }

        # Restore original manager
        app.conversation_manager = original_manager

    def test_get_reasoning_data_success(
        self, client, setup_conversation_with_reasoning
    ):
        """Test successful retrieval of reasoning data."""
        data = setup_conversation_with_reasoning

        # Login as the test user
        with client.session_transaction() as sess:
            sess["username"] = data["username"]

        # Request reasoning data for assistant message with reasoning (index 1)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")

        assert response.status_code == 200

        response_data = json.loads(response.data)
        assert response_data["success"] is True
        assert response_data["conversation_id"] == data["conversation_id"]
        assert response_data["message_index"] == 1
        assert response_data["message_role"] == "assistant"
        assert response_data["response_id"] == "resp_123"

        reasoning = response_data["reasoning"]
        assert reasoning["summary_parts"] == [
            "Step 1: Analyze greeting",
            "Step 2: Respond politely",
        ]
        assert (
            reasoning["complete_summary"]
            == "User is greeting me. I should respond politely and ask how I can help."
        )
        assert reasoning["response_id"] == "resp_123"

    def test_get_reasoning_data_authentication_required(
        self, client, setup_conversation_with_reasoning
    ):
        """Test endpoint without authentication."""
        data = setup_conversation_with_reasoning

        # Don't set session username
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")

        assert response.status_code == 401
        response_data = json.loads(response.data)
        assert response_data["error"] == "Authentication required"

    def test_get_reasoning_data_conversation_not_found(
        self, client, setup_conversation_with_reasoning
    ):
        """Test with non-existent conversation."""
        data = setup_conversation_with_reasoning

        with client.session_transaction() as sess:
            sess["username"] = data["username"]

        fake_conversation_id = "fake-conversation-id"
        response = client.get(f"/chat/reasoning/{fake_conversation_id}/0")

        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "Conversation not found"

    def test_get_reasoning_data_invalid_message_index(
        self, client, setup_conversation_with_reasoning
    ):
        """Test with invalid message index."""
        data = setup_conversation_with_reasoning

        with client.session_transaction() as sess:
            sess["username"] = data["username"]

        # Test index too high (this should reach our endpoint)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/999")
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data["error"] == "Invalid message index"

    def test_get_reasoning_data_user_message(
        self, client, setup_conversation_with_reasoning
    ):
        """Test requesting reasoning data for user message."""
        data = setup_conversation_with_reasoning

        with client.session_transaction() as sess:
            sess["username"] = data["username"]

        # Request reasoning data for user message (index 0)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/0")

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data["error"] == "No reasoning available"
        assert "assistant messages" in response_data["message"]

    def test_get_reasoning_data_assistant_message_no_reasoning(
        self, client, setup_conversation_with_reasoning
    ):
        """Test requesting reasoning data for assistant message without reasoning."""
        data = setup_conversation_with_reasoning

        with client.session_transaction() as sess:
            sess["username"] = data["username"]

        # Request reasoning data for assistant message without reasoning (index 2)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/2")

        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "No reasoning data"
        assert "No reasoning data is available" in response_data["message"]

    def test_cross_user_security(self, client, setup_conversation_with_reasoning):
        """Test that users cannot access other users' reasoning data."""
        data = setup_conversation_with_reasoning

        # Login as different user
        with client.session_transaction() as sess:
            sess["username"] = "different_user"

        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")

        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "Conversation not found"


class TestReasoningIntegration:
    """Test end-to-end reasoning integration."""

    def test_end_to_end_reasoning_capture(self, tmp_path):
        """Test complete reasoning data capture from stream to storage."""
        # Set up conversation manager with temporary directory
        conversation_manager = ConversationManager(str(tmp_path))

        # Create a conversation
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Set up stream processor
        queue = Queue()
        processor = StreamEventProcessor(queue)

        # Simulate a complete stream with reasoning events
        events = [
            # Response created
            Mock(type="response.created", response=Mock(id="resp_123")),
            # Text events
            Mock(type="response.output_text.delta", delta=Mock(text="Hello")),
            Mock(type="response.output_text.delta", delta=Mock(text=" world")),
            # Reasoning events
            Mock(
                type="response.reasoning_summary_part.added",
                part=Mock(text="Step 1: Analyze the request"),
            ),
            Mock(
                type="response.reasoning_summary_part.added",
                part=Mock(text="Step 2: Generate response"),
            ),
            Mock(
                type="response.reasoning_summary_text.done",
                text="The user is asking for a greeting. I should respond politely.",
            ),
            # Final text event
            Mock(type="response.output_text.done", text="Hello world"),
            Mock(type="response.completed", response=Mock(id="resp_123")),
        ]

        # Process all events
        for event in events:
            processor._handle_stream_event(event)

        # Verify reasoning data was captured
        reasoning_data = processor.get_reasoning_data()
        assert reasoning_data is not None
        assert reasoning_data["summary_parts"] == [
            "Step 1: Analyze the request",
            "Step 2: Generate response",
        ]
        assert (
            reasoning_data["complete_summary"]
            == "The user is asking for a greeting. I should respond politely."
        )
        assert reasoning_data["response_id"] == "resp_123"

        # Store the message with reasoning data
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            processor.accumulated_text,
            processor.get_response_id(),
            reasoning_data,
        )

        # Verify the message was stored with reasoning data
        conversation = conversation_manager.get_conversation(username, conversation_id)
        assert conversation is not None
        assert len(conversation.messages) == 1

        message = conversation.messages[0]
        assert message.role == "assistant"
        assert message.text == "Hello world"
        assert message.response_id == "resp_123"
        assert message.reasoning_data is not None

    def test_mixed_messages_with_and_without_reasoning(self, tmp_path):
        """Test conversations with mixed messages (some with reasoning, some without)."""
        conversation_manager = ConversationManager(str(tmp_path))

        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add user message (no reasoning)
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello, how are you?", None, None
        )

        # Add assistant message with reasoning
        reasoning_data = {
            "summary_parts": ["User is greeting", "Should respond politely"],
            "complete_summary": "User is greeting me. I should respond politely and ask how I can help.",
            "timestamp": 1234567890,
            "response_id": "resp_001",
        }

        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Hello! I'm doing well, thank you. How can I help you today?",
            "resp_001",
            reasoning_data,
        )

        # Add another assistant message without reasoning (simulating older API)
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Of course! I'd be happy to help you with Python.",
            "resp_002",
            None,
        )

        # Verify all messages were stored correctly
        conversation = conversation_manager.get_conversation(username, conversation_id)
        assert conversation is not None
        assert len(conversation.messages) == 3

        # Check user messages have no reasoning data
        assert conversation.messages[0].reasoning_data is None

        # Check first assistant message has reasoning data
        assert conversation.messages[1].reasoning_data is not None
        assert (
            conversation.messages[1].reasoning_data["complete_summary"]
            == "User is greeting me. I should respond politely and ask how I can help."
        )

        # Check second assistant message has no reasoning data
        assert conversation.messages[2].reasoning_data is None


class TestReasoningErrorHandling:
    """Test comprehensive error handling for reasoning functionality."""

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

    def test_responses_api_client_error_handling(self):
        """Test ResponsesAPIClient handles various error conditions."""
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)

        # Test rate limit error
        from openai import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        rate_limit_error = RateLimitError(
            "Rate limit exceeded", response=mock_response, body=None
        )
        rate_limit_error.retry_after = 60
        mock_client.responses.create.side_effect = rate_limit_error

        result = responses_client.create_response("test input")
        assert isinstance(result, dict)
        assert result["error"] == "rate_limit"
        assert "Too many requests" in result["message"]

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
