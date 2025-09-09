"""Integration tests for the reasoning API endpoint with the full system."""

import json
import pytest
import tempfile
from app import app, ConversationManager


class TestReasoningAPIIntegration:
    """Test reasoning API endpoint integration with the full system."""

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

    def test_full_conversation_flow_with_reasoning_api(self, client, temp_dir):
        """Test complete flow: create conversation, add messages, retrieve via API."""
        # Set up conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            username = "integration_user"
            
            # Create conversation
            conversation_id = conversation_manager.create_conversation(username, "Integration Test")
            
            # Add messages simulating a real conversation
            conversation_manager.add_message(
                username, conversation_id, "user", "What is Python?", None, None
            )
            
            # Add assistant response with reasoning
            reasoning_data = {
                "summary_parts": [
                    "User is asking about Python programming language",
                    "Should provide clear, informative explanation",
                    "Include key features and use cases"
                ],
                "complete_summary": "The user is asking about Python. I should provide a comprehensive explanation covering what Python is, its key features, and common use cases. This is a straightforward informational request.",
                "timestamp": 1234567890,
                "response_id": "resp_python_explanation"
            }
            
            conversation_manager.add_message(
                username, conversation_id, "assistant", 
                "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used for web development, data science, automation, and more.",
                "resp_python_explanation", reasoning_data
            )
            
            # Add follow-up user question
            conversation_manager.add_message(
                username, conversation_id, "user", "Can you give me an example?", None, None
            )
            
            # Add assistant response without reasoning (simulating older API)
            conversation_manager.add_message(
                username, conversation_id, "assistant",
                "Sure! Here's a simple Python example:\n\nprint('Hello, World!')\n\nThis prints 'Hello, World!' to the console.",
                "resp_example", None
            )
            
            # Test API endpoint with authentication
            with client.session_transaction() as sess:
                sess['username'] = username
            
            # Test retrieving reasoning for the first assistant message (index 1)
            response = client.get(f"/chat/reasoning/{conversation_id}/1")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["message_index"] == 1
            assert data["message_role"] == "assistant"
            assert "Python is a high-level" in data["message_text"]
            assert data["response_id"] == "resp_python_explanation"
            
            reasoning = data["reasoning"]
            assert len(reasoning["summary_parts"]) == 3
            assert "Python programming language" in reasoning["summary_parts"][0]
            assert "comprehensive explanation" in reasoning["complete_summary"]
            assert reasoning["response_id"] == "resp_python_explanation"
            
            # Test that user messages don't have reasoning
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["error"] == "No reasoning available"
            
            # Test that assistant message without reasoning returns 404
            response = client.get(f"/chat/reasoning/{conversation_id}/3")
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data["error"] == "No reasoning data"
            
        finally:
            app.conversation_manager = original_manager

    def test_api_endpoint_with_conversation_manager_methods(self, client, temp_dir):
        """Test API endpoint using ConversationManager methods directly."""
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            username = "method_test_user"
            conversation_id = conversation_manager.create_conversation(username, "Method Test")
            
            # Use ConversationManager methods to set up data
            reasoning_data = {
                "summary_parts": ["Method test reasoning"],
                "complete_summary": "Testing ConversationManager integration with API",
                "timestamp": 1234567891,
                "response_id": "resp_method_test"
            }
            
            conversation_manager.add_message(
                username, conversation_id, "assistant", "Method test response", 
                "resp_method_test", reasoning_data
            )
            
            # Verify using ConversationManager methods
            assert conversation_manager.has_reasoning_data(username, conversation_id, 0) is True
            retrieved_data = conversation_manager.get_message_reasoning_data(username, conversation_id, 0)
            assert retrieved_data is not None
            assert retrieved_data["complete_summary"] == "Testing ConversationManager integration with API"
            
            # Test via API endpoint
            with client.session_transaction() as sess:
                sess['username'] = username
            
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            assert response.status_code == 200
            
            api_data = json.loads(response.data)
            assert api_data["reasoning"]["complete_summary"] == "Testing ConversationManager integration with API"
            assert api_data["reasoning"]["response_id"] == "resp_method_test"
            
        finally:
            app.conversation_manager = original_manager

    def test_api_endpoint_error_handling_integration(self, client, temp_dir):
        """Test API endpoint error handling with real ConversationManager."""
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            username = "error_test_user"
            
            with client.session_transaction() as sess:
                sess['username'] = username
            
            # Test with completely non-existent conversation
            response = client.get("/chat/reasoning/non-existent-id/0")
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data["error"] == "Conversation not found"
            
            # Create conversation and test with out-of-bounds index
            conversation_id = conversation_manager.create_conversation(username, "Error Test")
            conversation_manager.add_message(username, conversation_id, "user", "Test message", None, None)
            
            response = client.get(f"/chat/reasoning/{conversation_id}/999")
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["error"] == "Invalid message index"
            assert "Valid range: 0-0" in data["message"]
            
        finally:
            app.conversation_manager = original_manager

    def test_api_endpoint_cross_user_security(self, client, temp_dir):
        """Test that users cannot access other users' reasoning data."""
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            # Create conversation for user1
            user1 = "user1"
            conversation_id = conversation_manager.create_conversation(user1, "User1 Chat")
            
            reasoning_data = {
                "summary_parts": ["Private reasoning"],
                "complete_summary": "This is private reasoning data for user1",
                "timestamp": 1234567892,
                "response_id": "resp_private"
            }
            
            conversation_manager.add_message(
                user1, conversation_id, "assistant", "Private response", 
                "resp_private", reasoning_data
            )
            
            # Try to access as user2
            with client.session_transaction() as sess:
                sess['username'] = "user2"
            
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data["error"] == "Conversation not found"
            
            # Verify user1 can access their own data
            with client.session_transaction() as sess:
                sess['username'] = user1
            
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["reasoning"]["complete_summary"] == "This is private reasoning data for user1"
            
        finally:
            app.conversation_manager = original_manager

    def test_api_response_format_consistency(self, client, temp_dir):
        """Test that API response format is consistent and complete."""
        conversation_manager = ConversationManager(temp_dir)
        
        import app
        original_manager = app.conversation_manager
        app.conversation_manager = conversation_manager
        
        try:
            username = "format_test_user"
            conversation_id = conversation_manager.create_conversation(username, "Format Test")
            
            # Test with minimal reasoning data
            minimal_reasoning = {
                "summary_parts": [],
                "complete_summary": "",
                "timestamp": 0,
                "response_id": ""
            }
            
            conversation_manager.add_message(
                username, conversation_id, "assistant", "Minimal response", 
                "resp_minimal", minimal_reasoning
            )
            
            # Test with complete reasoning data
            complete_reasoning = {
                "summary_parts": ["Part 1", "Part 2", "Part 3"],
                "complete_summary": "Complete reasoning summary with details",
                "timestamp": 1234567893,
                "response_id": "resp_complete"
            }
            
            conversation_manager.add_message(
                username, conversation_id, "assistant", "Complete response", 
                "resp_complete", complete_reasoning
            )
            
            with client.session_transaction() as sess:
                sess['username'] = username
            
            # Test minimal data response format
            response = client.get(f"/chat/reasoning/{conversation_id}/0")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            required_fields = ["success", "conversation_id", "message_index", "message_role", 
                              "message_text", "response_id", "reasoning"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            assert data["reasoning"]["summary_parts"] == []
            assert data["reasoning"]["complete_summary"] == ""
            
            # Test complete data response format
            response = client.get(f"/chat/reasoning/{conversation_id}/1")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data["reasoning"]["summary_parts"] == ["Part 1", "Part 2", "Part 3"]
            assert data["reasoning"]["complete_summary"] == "Complete reasoning summary with details"
            assert data["reasoning"]["timestamp"] == 1234567893
            
        finally:
            app.conversation_manager = original_manager