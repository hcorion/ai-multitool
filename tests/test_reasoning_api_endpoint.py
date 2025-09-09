"""Tests for the reasoning data API endpoint."""

import json
import pytest
import tempfile
from app import app, ConversationManager


class TestReasoningAPIEndpoint:
    """Test the /chat/reasoning/<conversation_id>/<message_index> endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        app.config['TESTING'] = True
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
        conversation_id = conversation_manager.create_conversation(username, "Test Chat")
        
        # Add user message
        conversation_manager.add_message(
            username, conversation_id, "user", "Hello, how are you?", None, None
        )
        
        # Add assistant message with reasoning data
        reasoning_data = {
            "summary_parts": ["Step 1: Analyze greeting", "Step 2: Respond politely"],
            "complete_summary": "User is greeting me. I should respond politely and ask how I can help.",
            "timestamp": 1234567890,
            "response_id": "resp_123"
        }
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Hello! I'm doing well, thank you. How can I help you today?", 
            "resp_123", reasoning_data
        )
        
        # Add another user message
        conversation_manager.add_message(
            username, conversation_id, "user", "Can you help me with Python?", None, None
        )
        
        # Add assistant message without reasoning data
        conversation_manager.add_message(
            username, conversation_id, "assistant", "Of course! I'd be happy to help you with Python.", 
            "resp_124", None
        )
        
        yield {
            "username": username,
            "conversation_id": conversation_id,
            "conversation_manager": conversation_manager
        }
        
        # Restore original manager
        app.conversation_manager = original_manager

    def test_get_reasoning_data_success(self, client, setup_conversation_with_reasoning):
        """Test successful retrieval of reasoning data."""
        data = setup_conversation_with_reasoning
        
        # Login as the test user
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Request reasoning data for assistant message with reasoning (index 1)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")
        
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert response_data["success"] is True
        assert response_data["conversation_id"] == data['conversation_id']
        assert response_data["message_index"] == 1
        assert response_data["message_role"] == "assistant"
        assert response_data["message_text"] == "Hello! I'm doing well, thank you. How can I help you today?"
        assert response_data["response_id"] == "resp_123"
        
        reasoning = response_data["reasoning"]
        assert reasoning["summary_parts"] == ["Step 1: Analyze greeting", "Step 2: Respond politely"]
        assert reasoning["complete_summary"] == "User is greeting me. I should respond politely and ask how I can help."
        assert reasoning["timestamp"] == 1234567890
        assert reasoning["response_id"] == "resp_123"

    def test_get_reasoning_data_no_authentication(self, client, setup_conversation_with_reasoning):
        """Test endpoint without authentication."""
        data = setup_conversation_with_reasoning
        
        # Don't set session username
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")
        
        assert response.status_code == 401
        response_data = json.loads(response.data)
        assert response_data["error"] == "Authentication required"

    def test_get_reasoning_data_conversation_not_found(self, client, setup_conversation_with_reasoning):
        """Test with non-existent conversation."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        fake_conversation_id = "fake-conversation-id"
        response = client.get(f"/chat/reasoning/{fake_conversation_id}/0")
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "Conversation not found"
        assert "does not exist" in response_data["message"]

    def test_get_reasoning_data_invalid_message_index(self, client, setup_conversation_with_reasoning):
        """Test with invalid message index."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Test negative index (Flask routing returns 404 for negative integers)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/-1")
        assert response.status_code == 404  # Flask routing issue, not our endpoint
        
        # Test index too high (this should reach our endpoint)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/999")
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data["error"] == "Invalid message index"

    def test_get_reasoning_data_user_message(self, client, setup_conversation_with_reasoning):
        """Test requesting reasoning data for user message."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Request reasoning data for user message (index 0)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/0")
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data["error"] == "No reasoning available"
        assert "assistant messages" in response_data["message"]

    def test_get_reasoning_data_assistant_message_no_reasoning(self, client, setup_conversation_with_reasoning):
        """Test requesting reasoning data for assistant message without reasoning."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Request reasoning data for assistant message without reasoning (index 3)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/3")
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "No reasoning data"
        assert "No reasoning data is available" in response_data["message"]

    def test_get_reasoning_data_different_user(self, client, setup_conversation_with_reasoning):
        """Test accessing conversation from different user."""
        data = setup_conversation_with_reasoning
        
        # Login as different user
        with client.session_transaction() as sess:
            sess['username'] = "different_user"
        
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data["error"] == "Conversation not found"

    def test_get_reasoning_data_malformed_conversation_id(self, client, setup_conversation_with_reasoning):
        """Test with malformed conversation ID."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Test with empty conversation ID (should be handled by Flask routing)
        response = client.get("/chat/reasoning//1")
        assert response.status_code == 404  # Flask routing will return 404

    def test_get_reasoning_data_malformed_message_index(self, client, setup_conversation_with_reasoning):
        """Test with malformed message index."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Test with non-integer message index (should be handled by Flask routing)
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/not_a_number")
        assert response.status_code == 404  # Flask routing will return 404

    def test_reasoning_endpoint_only_accepts_get(self, client, setup_conversation_with_reasoning):
        """Test that the endpoint only accepts GET requests."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        # Test POST request
        response = client.post(f"/chat/reasoning/{data['conversation_id']}/1")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test PUT request
        response = client.put(f"/chat/reasoning/{data['conversation_id']}/1")
        assert response.status_code == 405  # Method Not Allowed
        
        # Test DELETE request
        response = client.delete(f"/chat/reasoning/{data['conversation_id']}/1")
        assert response.status_code == 405  # Method Not Allowed

    def test_reasoning_data_structure_validation(self, client, setup_conversation_with_reasoning):
        """Test that returned reasoning data has correct structure."""
        data = setup_conversation_with_reasoning
        
        with client.session_transaction() as sess:
            sess['username'] = data['username']
        
        response = client.get(f"/chat/reasoning/{data['conversation_id']}/1")
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        
        # Verify top-level structure
        required_fields = ["success", "conversation_id", "message_index", "message_role", 
                          "message_text", "response_id", "reasoning"]
        for field in required_fields:
            assert field in response_data
        
        # Verify reasoning structure
        reasoning = response_data["reasoning"]
        reasoning_fields = ["summary_parts", "complete_summary", "timestamp", "response_id"]
        for field in reasoning_fields:
            assert field in reasoning
        
        # Verify data types
        assert isinstance(response_data["success"], bool)
        assert isinstance(response_data["message_index"], int)
        assert isinstance(reasoning["summary_parts"], list)
        assert isinstance(reasoning["complete_summary"], str)
        assert isinstance(reasoning["timestamp"], (int, float))
        assert isinstance(reasoning["response_id"], str)

    def test_reasoning_endpoint_with_empty_conversation(self, client, temp_dir):
        """Test reasoning endpoint with empty conversation."""
        # Create conversation manager and empty conversation
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            username = "testuser"
            conversation_id = conversation_manager.create_conversation(username, "Empty Chat")
            
            with client.session_transaction() as sess:
                sess['username'] = username
            
            # Try to get reasoning for non-existent message
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            
            assert response.status_code == 400
            response_data = json.loads(response.data)
            assert response_data["error"] == "Invalid message index"
            
        finally:
            app.conversation_manager = original_manager