"""Tests for reasoning data models and validation."""

import pytest
import time
from typing import Dict, Any
from pydantic import ValidationError

from app import ChatMessage, validate_reasoning_data, Conversation, ConversationManager, ConversationData


class TestReasoningDataValidation:
    """Test reasoning data validation function."""

    def test_validate_reasoning_data_none(self):
        """Test validation with None reasoning data."""
        result = validate_reasoning_data(None)
        assert result is None

    def test_validate_reasoning_data_valid(self):
        """Test validation with valid reasoning data."""
        reasoning_data = {
            "summary_parts": ["First part", "Second part"],
            "complete_summary": "Complete reasoning summary",
            "timestamp": int(time.time()),
            "response_id": "resp_123"
        }
        
        result = validate_reasoning_data(reasoning_data)
        assert result == reasoning_data

    def test_validate_reasoning_data_partial_valid(self):
        """Test validation with partial but valid reasoning data."""
        reasoning_data = {
            "complete_summary": "Just a summary",
            "timestamp": time.time()
        }
        
        result = validate_reasoning_data(reasoning_data)
        assert result == reasoning_data

    def test_validate_reasoning_data_invalid_type(self):
        """Test validation with invalid data type."""
        with pytest.raises(ValueError, match="Reasoning data must be a dictionary"):
            validate_reasoning_data("not a dict")

    def test_validate_reasoning_data_invalid_summary_parts_type(self):
        """Test validation with invalid summary_parts type."""
        reasoning_data = {
            "summary_parts": "not a list",
            "complete_summary": "Summary"
        }
        
        with pytest.raises(ValueError, match="Reasoning data field 'summary_parts' must be of type"):
            validate_reasoning_data(reasoning_data)

    def test_validate_reasoning_data_invalid_summary_parts_content(self):
        """Test validation with invalid summary_parts content."""
        reasoning_data = {
            "summary_parts": ["valid string", 123, "another string"],
            "complete_summary": "Summary"
        }
        
        with pytest.raises(ValueError, match="All items in summary_parts must be strings"):
            validate_reasoning_data(reasoning_data)

    def test_validate_reasoning_data_invalid_complete_summary_type(self):
        """Test validation with invalid complete_summary type."""
        reasoning_data = {
            "complete_summary": 123,
            "timestamp": time.time()
        }
        
        with pytest.raises(ValueError, match="Reasoning data field 'complete_summary' must be of type"):
            validate_reasoning_data(reasoning_data)

    def test_validate_reasoning_data_invalid_timestamp_type(self):
        """Test validation with invalid timestamp type."""
        reasoning_data = {
            "complete_summary": "Summary",
            "timestamp": "not a number"
        }
        
        with pytest.raises(ValueError, match="Reasoning data field 'timestamp' must be of type"):
            validate_reasoning_data(reasoning_data)

    def test_validate_reasoning_data_invalid_response_id_type(self):
        """Test validation with invalid response_id type."""
        reasoning_data = {
            "complete_summary": "Summary",
            "response_id": 123
        }
        
        with pytest.raises(ValueError, match="Reasoning data field 'response_id' must be of type"):
            validate_reasoning_data(reasoning_data)


class TestChatMessageModel:
    """Test ChatMessage Pydantic model with reasoning data."""

    def test_chat_message_basic(self):
        """Test basic ChatMessage creation without reasoning data."""
        message = ChatMessage(
            role="user",
            text="Hello",
            timestamp=int(time.time())
        )
        
        assert message.role == "user"
        assert message.text == "Hello"
        assert message.reasoning_data is None
        assert message.response_id is None

    def test_chat_message_with_valid_reasoning_data(self):
        """Test ChatMessage creation with valid reasoning data."""
        reasoning_data = {
            "summary_parts": ["First part", "Second part"],
            "complete_summary": "Complete reasoning summary",
            "timestamp": int(time.time()),
            "response_id": "resp_123"
        }
        
        message = ChatMessage(
            role="assistant",
            text="Response",
            timestamp=int(time.time()),
            response_id="resp_123",
            reasoning_data=reasoning_data
        )
        
        assert message.role == "assistant"
        assert message.text == "Response"
        assert message.response_id == "resp_123"
        assert message.reasoning_data == reasoning_data

    def test_chat_message_with_invalid_reasoning_data(self):
        """Test ChatMessage creation with invalid reasoning data."""
        invalid_reasoning_data = {
            "summary_parts": ["valid", 123],  # Invalid: contains non-string
            "complete_summary": "Summary"
        }
        
        with pytest.raises(ValidationError):
            ChatMessage(
                role="assistant",
                text="Response",
                timestamp=int(time.time()),
                reasoning_data=invalid_reasoning_data
            )

    def test_chat_message_serialization(self):
        """Test ChatMessage serialization with reasoning data."""
        reasoning_data = {
            "summary_parts": ["Part 1", "Part 2"],
            "complete_summary": "Full summary",
            "timestamp": 1234567890,
            "response_id": "resp_456"
        }
        
        message = ChatMessage(
            role="assistant",
            text="Test response",
            timestamp=1234567890,
            response_id="resp_456",
            reasoning_data=reasoning_data
        )
        
        # Test model_dump (Pydantic v2)
        data = message.model_dump()
        assert data["reasoning_data"] == reasoning_data
        
        # Test round-trip serialization
        recreated = ChatMessage(**data)
        assert recreated.reasoning_data == reasoning_data


class TestConversationWithReasoningData:
    """Test Conversation model with reasoning data support."""

    def test_conversation_add_message_with_reasoning_data(self):
        """Test adding message with reasoning data to conversation."""
        current_time = int(time.time())
        conversation_data = ConversationData(
            id="test_conv",
            created_at=current_time
        )
        conversation = Conversation(
            data=conversation_data,
            chat_name="Test Conversation",
            last_update=current_time
        )
        
        reasoning_data = {
            "summary_parts": ["Reasoning step 1", "Reasoning step 2"],
            "complete_summary": "Complete reasoning process",
            "timestamp": int(time.time()),
            "response_id": "resp_789"
        }
        
        conversation.add_message(
            role="assistant",
            content="Response with reasoning",
            response_id="resp_789",
            reasoning_data=reasoning_data
        )
        
        assert len(conversation.messages) == 1
        message = conversation.messages[0]
        assert message.role == "assistant"
        assert message.text == "Response with reasoning"
        assert message.response_id == "resp_789"
        assert message.reasoning_data == reasoning_data

    def test_conversation_add_message_without_reasoning_data(self):
        """Test adding message without reasoning data to conversation."""
        current_time = int(time.time())
        conversation_data = ConversationData(
            id="test_conv",
            created_at=current_time
        )
        conversation = Conversation(
            data=conversation_data,
            chat_name="Test Conversation",
            last_update=current_time
        )
        
        conversation.add_message(
            role="user",
            content="User message"
        )
        
        assert len(conversation.messages) == 1
        message = conversation.messages[0]
        assert message.role == "user"
        assert message.text == "User message"
        assert message.reasoning_data is None
        assert message.response_id is None


class TestConversationManagerWithReasoningData:
    """Test ConversationManager with reasoning data support."""

    def test_conversation_manager_add_message_with_reasoning_data(self, tmp_path):
        """Test ConversationManager adding message with reasoning data."""
        # Create temporary directory for test
        static_folder = str(tmp_path)
        manager = ConversationManager(static_folder)
        
        # Create a conversation
        conversation_id = manager.create_conversation("testuser", "Test Chat")
        
        reasoning_data = {
            "summary_parts": ["Step A", "Step B"],
            "complete_summary": "Full reasoning chain",
            "timestamp": int(time.time()),
            "response_id": "resp_abc"
        }
        
        # Add message with reasoning data
        manager.add_message(
            username="testuser",
            conversation_id=conversation_id,
            role="assistant",
            content="AI response with reasoning",
            response_id="resp_abc",
            reasoning_data=reasoning_data
        )
        
        # Verify the message was stored correctly
        conversation = manager.get_conversation("testuser", conversation_id)
        assert conversation is not None
        assert len(conversation.messages) == 1
        
        message = conversation.messages[0]
        assert message.role == "assistant"
        assert message.text == "AI response with reasoning"
        assert message.response_id == "resp_abc"
        assert message.reasoning_data == reasoning_data

    def test_conversation_manager_persistence_with_reasoning_data(self, tmp_path):
        """Test that reasoning data persists across ConversationManager instances."""
        static_folder = str(tmp_path)
        
        # Create first manager instance and add message with reasoning data
        manager1 = ConversationManager(static_folder)
        conversation_id = manager1.create_conversation("testuser", "Persistent Chat")
        
        reasoning_data = {
            "summary_parts": ["Persistent step 1", "Persistent step 2"],
            "complete_summary": "Persistent reasoning",
            "timestamp": int(time.time()),
            "response_id": "resp_persist"
        }
        
        manager1.add_message(
            username="testuser",
            conversation_id=conversation_id,
            role="assistant",
            content="Persistent message",
            response_id="resp_persist",
            reasoning_data=reasoning_data
        )
        
        # Create second manager instance and verify data persists
        manager2 = ConversationManager(static_folder)
        conversation = manager2.get_conversation("testuser", conversation_id)
        
        assert conversation is not None
        assert len(conversation.messages) == 1
        
        message = conversation.messages[0]
        assert message.reasoning_data == reasoning_data
        assert message.response_id == "resp_persist"