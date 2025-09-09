"""Integration tests for ConversationManager reasoning functionality with existing system."""

import pytest
import tempfile
from app import ConversationManager


class TestConversationManagerIntegration:
    """Test ConversationManager integration with existing functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def conversation_manager(self, temp_dir):
        """Create a ConversationManager instance for testing."""
        return ConversationManager(temp_dir)

    def test_backward_compatibility_with_existing_conversations(self, conversation_manager):
        """Test that new methods work with conversations created using existing methods."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Legacy Chat")
        
        # Add messages using existing method (without reasoning data)
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello"
        )
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Hi there!", "resp_123"
        )
        
        # Test new methods with legacy data
        assert conversation_manager.get_conversation_message_count(username, conversation_id) == 2
        assert conversation_manager.has_reasoning_data(username, conversation_id, 0) is False
        assert conversation_manager.has_reasoning_data(username, conversation_id, 1) is False
        
        user_message = conversation_manager.get_message_by_index(username, conversation_id, 0)
        assistant_message = conversation_manager.get_message_by_index(username, conversation_id, 1)
        
        assert user_message is not None
        assert user_message.role == "user"
        assert user_message.reasoning_data is None
        
        assert assistant_message is not None
        assert assistant_message.role == "assistant"
        assert assistant_message.response_id == "resp_123"
        assert assistant_message.reasoning_data is None

    def test_mixed_legacy_and_new_messages(self, conversation_manager):
        """Test conversations with both legacy and new messages."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Mixed Chat")
        
        # Add legacy message (old method signature)
        conversation_manager.add_message(
            username, conversation_id, "user", "Legacy question"
        )
        
        # Add new message with reasoning data
        reasoning_data = {
            "summary_parts": ["Modern reasoning step"],
            "complete_summary": "This is a modern response with reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_modern"
        }
        
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Modern response", "resp_modern", reasoning_data
        )
        
        # Add another legacy message
        conversation_manager.add_message(
            username, conversation_id, "user", "Another legacy question"
        )
        
        # Test retrieval
        assert conversation_manager.get_conversation_message_count(username, conversation_id) == 3
        
        # Legacy messages should have no reasoning data
        assert conversation_manager.has_reasoning_data(username, conversation_id, 0) is False
        assert conversation_manager.has_reasoning_data(username, conversation_id, 2) is False
        
        # Modern message should have reasoning data
        assert conversation_manager.has_reasoning_data(username, conversation_id, 1) is True
        
        retrieved_reasoning = conversation_manager.get_message_reasoning_data(username, conversation_id, 1)
        assert retrieved_reasoning is not None
        assert retrieved_reasoning["complete_summary"] == "This is a modern response with reasoning"

    def test_conversation_listing_with_reasoning_messages(self, conversation_manager):
        """Test that conversation listing works correctly with reasoning data."""
        username = "testuser"
        
        # Create multiple conversations with different message types
        conv1_id = conversation_manager.create_conversation(username, "Legacy Only")
        conversation_manager.add_message(username, conv1_id, "user", "Legacy message")
        
        conv2_id = conversation_manager.create_conversation(username, "With Reasoning")
        conversation_manager.add_message(username, conv2_id, "user", "Question")
        
        reasoning_data = {
            "summary_parts": ["Reasoning step"],
            "complete_summary": "Response with reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        conversation_manager.add_message(
            username, conv2_id, "assistant", "Answer", "resp_123", reasoning_data
        )
        
        # Test conversation listing
        conversations = conversation_manager.list_conversations(username)
        
        assert len(conversations) == 2
        assert conv1_id in conversations
        assert conv2_id in conversations
        
        # Verify conversation data integrity
        assert conversations[conv1_id]["chat_name"] == "Legacy Only"
        assert conversations[conv2_id]["chat_name"] == "With Reasoning"

    def test_message_list_compatibility(self, conversation_manager):
        """Test that get_message_list works correctly with reasoning data."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add messages with and without reasoning data
        conversation_manager.add_message(username, conversation_id, "user", "Question")
        
        reasoning_data = {
            "summary_parts": ["Step 1"],
            "complete_summary": "Answer reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Answer", "resp_123", reasoning_data
        )
        
        # Test get_message_list (should work as before, not exposing reasoning data)
        message_list = conversation_manager.get_message_list(username, conversation_id)
        
        assert len(message_list) == 2
        assert message_list[0] == {"role": "user", "text": "Question"}
        assert message_list[1] == {"role": "assistant", "text": "Answer"}
        
        # Reasoning data should not be in the message list (frontend compatibility)
        assert "reasoning_data" not in message_list[1]

    def test_conversation_metadata_operations_with_reasoning(self, conversation_manager):
        """Test conversation metadata operations work with reasoning data."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add message with reasoning data
        reasoning_data = {
            "summary_parts": ["Metadata test"],
            "complete_summary": "Testing metadata operations",
            "timestamp": 1234567890,
            "response_id": "resp_meta"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Response", "resp_meta", reasoning_data
        )
        
        # Test title update
        success = conversation_manager.update_conversation_title(
            username, conversation_id, "Updated Title"
        )
        assert success is True
        
        # Verify reasoning data is preserved after metadata update
        retrieved_reasoning = conversation_manager.get_message_reasoning_data(username, conversation_id, 0)
        assert retrieved_reasoning is not None
        assert retrieved_reasoning["complete_summary"] == "Testing metadata operations"
        
        # Verify title was updated
        conversation = conversation_manager.get_conversation(username, conversation_id)
        assert conversation is not None
        assert conversation.chat_name == "Updated Title"

    def test_response_id_tracking_with_reasoning(self, conversation_manager):
        """Test that response ID tracking works correctly with reasoning data."""
        username = "testuser"
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add messages with response IDs and reasoning data
        reasoning_data_1 = {
            "summary_parts": ["First response"],
            "complete_summary": "First reasoning",
            "timestamp": 1234567890,
            "response_id": "resp_1"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "First response", "resp_1", reasoning_data_1
        )
        
        reasoning_data_2 = {
            "summary_parts": ["Second response"],
            "complete_summary": "Second reasoning",
            "timestamp": 1234567891,
            "response_id": "resp_2"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Second response", "resp_2", reasoning_data_2
        )
        
        # Test last response ID tracking
        last_response_id = conversation_manager.get_last_response_id(username, conversation_id)
        assert last_response_id == "resp_2"
        
        # Verify both reasoning data entries are preserved
        reasoning_1 = conversation_manager.get_message_reasoning_data(username, conversation_id, 0)
        reasoning_2 = conversation_manager.get_message_reasoning_data(username, conversation_id, 1)
        
        assert reasoning_1["response_id"] == "resp_1"
        assert reasoning_2["response_id"] == "resp_2"