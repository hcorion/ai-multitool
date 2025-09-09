"""Integration tests for reasoning data capture in the chat system."""

import json
import pytest
from queue import Queue
from unittest.mock import Mock, patch
from app import StreamEventProcessor, ConversationManager


class TestReasoningIntegration:
    """Test reasoning data integration with the chat system."""

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
                part="Step 1: Analyze the request",
            ),
            Mock(
                type="response.reasoning_summary_part.added",
                part="Step 2: Generate response",
            ),
            Mock(
                type="response.reasoning_summary_text.delta", delta="The user is asking"
            ),
            Mock(type="response.reasoning_summary_text.delta", delta=" for a greeting"),
            Mock(
                type="response.reasoning_summary_text.done",
                text="The user is asking for a greeting. I should respond politely.",
            ),
            # Response completion
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
        assert (
            message.reasoning_data["complete_summary"]
            == "The user is asking for a greeting. I should respond politely."
        )

    def test_reasoning_data_persistence(self, tmp_path):
        """Test that reasoning data persists across conversation manager operations."""
        # Set up conversation manager with temporary directory
        conversation_manager = ConversationManager(str(tmp_path))

        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add a message with reasoning data
        reasoning_data = {
            "summary_parts": ["Reasoning step 1", "Reasoning step 2"],
            "complete_summary": "Complete reasoning explanation",
            "timestamp": 1234567890,
            "response_id": "resp_456",
        }

        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Test response",
            "resp_456",
            reasoning_data,
        )

        # Create a new conversation manager instance (simulating app restart)
        new_conversation_manager = ConversationManager(str(tmp_path))

        # Retrieve the conversation
        conversation = new_conversation_manager.get_conversation(
            username, conversation_id
        )
        assert conversation is not None

        # Verify reasoning data was persisted
        message = conversation.messages[0]
        assert message.reasoning_data is not None
        assert message.reasoning_data["summary_parts"] == [
            "Reasoning step 1",
            "Reasoning step 2",
        ]
        assert (
            message.reasoning_data["complete_summary"]
            == "Complete reasoning explanation"
        )
        assert message.reasoning_data["response_id"] == "resp_456"

    def test_reasoning_data_optional(self, tmp_path):
        """Test that messages work correctly without reasoning data."""
        conversation_manager = ConversationManager(str(tmp_path))

        username = "testuser"
        conversation_id = conversation_manager.create_conversation(
            username, "Test Chat"
        )

        # Add a message without reasoning data
        conversation_manager.add_message(
            username,
            conversation_id,
            "assistant",
            "Response without reasoning",
            "resp_789",
            None,  # No reasoning data
        )

        # Verify the message was stored correctly
        conversation = conversation_manager.get_conversation(username, conversation_id)
        assert conversation is not None

        message = conversation.messages[0]
        assert message.role == "assistant"
        assert message.text == "Response without reasoning"
        assert message.response_id == "resp_789"
        assert message.reasoning_data is None

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

        # Add another user message (no reasoning)
        conversation_manager.add_message(
            username,
            conversation_id,
            "user",
            "Can you help me with Python?",
            None,
            None,
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
        assert len(conversation.messages) == 4

        # Check user messages have no reasoning data
        assert conversation.messages[0].reasoning_data is None
        assert conversation.messages[2].reasoning_data is None

        # Check first assistant message has reasoning data
        assert conversation.messages[1].reasoning_data is not None
        assert (
            conversation.messages[1].reasoning_data["complete_summary"]
            == "User is greeting me. I should respond politely and ask how I can help."
        )

        # Check second assistant message has no reasoning data
        assert conversation.messages[3].reasoning_data is None
