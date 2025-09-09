"""Tests for ConversationManager reasoning data storage and retrieval functionality."""

import pytest
import tempfile
import os
from app import ConversationManager, ChatMessage, validate_reasoning_data


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
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add a user message (no reasoning data)
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        
        # Add an assistant message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1: Analyze request", "Step 2: Generate response"],
            "complete_summary": "User is greeting. I should respond politely.",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Hello! How can I help?", "resp_123", reasoning_data
        )
        
        # Test retrieving reasoning data
        retrieved_data = conversation_manager.get_message_reasoning_data(
            username, conversation_id, 1  # Assistant message index
        )
        
        assert retrieved_data is not None
        assert retrieved_data["summary_parts"] == ["Step 1: Analyze request", "Step 2: Generate response"]
        assert retrieved_data["complete_summary"] == "User is greeting. I should respond politely."
        assert retrieved_data["response_id"] == "resp_123"

    def test_get_message_reasoning_data_no_data(self, conversation_manager):
        """Test retrieving reasoning data when none exists."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add a message without reasoning data
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        
        # Test retrieving reasoning data (should return None)
        retrieved_data = conversation_manager.get_message_reasoning_data(
            username, conversation_id, 0
        )
        
        assert retrieved_data is None

    def test_get_message_reasoning_data_invalid_index(self, conversation_manager):
        """Test retrieving reasoning data with invalid message index."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add one message
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        
        # Test with invalid indices
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, -1) is None
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 1) is None
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 999) is None

    def test_get_message_reasoning_data_invalid_conversation(self, conversation_manager):
        """Test retrieving reasoning data for non-existent conversation."""
        username = "testuser"
        fake_conversation_id = "fake-id"
        
        retrieved_data = conversation_manager.get_message_reasoning_data(
            username, fake_conversation_id, 0
        )
        
        assert retrieved_data is None

    def test_get_message_by_index_valid(self, conversation_manager):
        """Test retrieving a message by valid index."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add messages
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Hi there!", "resp_123", None
        )
        
        # Test retrieving messages
        user_message = conversation_manager.get_message_by_index(username, conversation_id, 0)
        assistant_message = conversation_manager.get_message_by_index(username, conversation_id, 1)
        
        assert user_message is not None
        assert user_message.role == "user"
        assert user_message.text == "Hello"
        
        assert assistant_message is not None
        assert assistant_message.role == "assistant"
        assert assistant_message.text == "Hi there!"
        assert assistant_message.response_id == "resp_123"

    def test_get_message_by_index_invalid(self, conversation_manager):
        """Test retrieving a message by invalid index."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add one message
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        
        # Test with invalid indices
        assert conversation_manager.get_message_by_index(username, conversation_id, -1) is None
        assert conversation_manager.get_message_by_index(username, conversation_id, 1) is None
        assert conversation_manager.get_message_by_index(username, conversation_id, 999) is None

    def test_has_reasoning_data(self, conversation_manager):
        """Test checking if a message has reasoning data."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add message without reasoning data
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        
        # Add message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1"],
            "complete_summary": "Summary",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Response", "resp_123", reasoning_data
        )
        
        # Test has_reasoning_data
        assert conversation_manager.has_reasoning_data(username, conversation_id, 0) is False
        assert conversation_manager.has_reasoning_data(username, conversation_id, 1) is True
        assert conversation_manager.has_reasoning_data(username, conversation_id, 999) is False

    def test_get_conversation_message_count(self, conversation_manager):
        """Test getting the message count for a conversation."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Initially no messages
        assert conversation_manager.get_conversation_message_count(username, conversation_id) == 0
        
        # Add messages
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello", None, None
        )
        assert conversation_manager.get_conversation_message_count(username, conversation_id) == 1
        
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Hi!", "resp_123", None
        )
        assert conversation_manager.get_conversation_message_count(username, conversation_id) == 2

    def test_get_conversation_message_count_invalid_conversation(self, conversation_manager):
        """Test getting message count for non-existent conversation."""
        username = "testuser"
        fake_conversation_id = "fake-id"
        
        count = conversation_manager.get_conversation_message_count(username, fake_conversation_id)
        assert count == 0

    def test_reasoning_data_persistence_across_manager_instances(self, temp_dir):
        """Test that reasoning data persists across ConversationManager instances."""
        username = "testuser"
        
        # Create first manager instance and add data
        manager1 = ConversationManager(temp_dir)
        conversation_id = manager1.create_conversation(username, "Test Chat")
        
        reasoning_data = {
            "summary_parts": ["Persistent step"],
            "complete_summary": "This should persist",
            "timestamp": 1234567890,
            "response_id": "resp_persist"
        }
        
        manager1.add_message(
            username, conversation_id, "assistant", "Persistent message", "resp_persist", reasoning_data
        )
        
        # Create second manager instance and retrieve data
        manager2 = ConversationManager(temp_dir)
        retrieved_data = manager2.get_message_reasoning_data(username, conversation_id, 0)
        
        assert retrieved_data is not None
        assert retrieved_data["complete_summary"] == "This should persist"
        assert retrieved_data["response_id"] == "resp_persist"

    def test_reasoning_data_validation_on_retrieval(self, conversation_manager):
        """Test that reasoning data is validated when retrieved."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add message with valid reasoning data
        valid_reasoning_data = {
            "summary_parts": ["Valid step"],
            "complete_summary": "Valid summary",
            "timestamp": 1234567890,
            "response_id": "resp_valid"
        }
        
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Valid message", "resp_valid", valid_reasoning_data
        )
        
        # Retrieve and verify validation occurs
        retrieved_data = conversation_manager.get_message_reasoning_data(username, conversation_id, 0)
        
        assert retrieved_data is not None
        # The data should be validated and returned as-is if valid
        assert retrieved_data == valid_reasoning_data

    def test_mixed_messages_reasoning_retrieval(self, conversation_manager):
        """Test retrieving reasoning data from conversations with mixed message types."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add various message types
        conversation_manager.add_message(username, conversation_id, "user", "Question 1", None, None)
        
        reasoning_data_1 = {
            "summary_parts": ["Answer 1 step"],
            "complete_summary": "First answer reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_1"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Answer 1", "resp_1", reasoning_data_1
        )
        
        conversation_manager.add_message(username, conversation_id, "user", "Question 2", None, None)
        
        # Assistant message without reasoning (simulating older API)
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Answer 2", "resp_2", None
        )
        
        reasoning_data_3 = {
            "summary_parts": ["Answer 3 step"],
            "complete_summary": "Third answer reasoning",
            "timestamp": 1234567891,
            "response_id": "resp_3"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Answer 3", "resp_3", reasoning_data_3
        )
        
        # Test retrieving reasoning data for each message
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 0) is None  # User message
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 1) is not None  # Assistant with reasoning
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 2) is None  # User message
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 3) is None  # Assistant without reasoning
        assert conversation_manager.get_message_reasoning_data(username, conversation_id, 4) is not None  # Assistant with reasoning
        
        # Verify specific reasoning data
        retrieved_1 = conversation_manager.get_message_reasoning_data(username, conversation_id, 1)
        retrieved_3 = conversation_manager.get_message_reasoning_data(username, conversation_id, 4)
        
        assert retrieved_1["complete_summary"] == "First answer reasoning"
        assert retrieved_3["complete_summary"] == "Third answer reasoning"

    def test_error_handling_in_reasoning_methods(self, conversation_manager):
        """Test error handling in reasoning-related methods."""
        username = "testuser"
        
        # Test with non-existent conversation
        assert conversation_manager.get_message_reasoning_data(username, "fake-id", 0) is None
        assert conversation_manager.get_message_by_index(username, "fake-id", 0) is None
        assert conversation_manager.has_reasoning_data(username, "fake-id", 0) is False
        assert conversation_manager.get_conversation_message_count(username, "fake-id") == 0