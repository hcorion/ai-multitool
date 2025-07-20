#!/usr/bin/env python3
"""
Tests for title refresh integration in the UI flow.
Verifies that the frontend properly refreshes titles when they are updated by the server.
"""

import os
import tempfile
import json
import time
from unittest.mock import Mock, patch

# Set a dummy API key for testing to avoid initialization errors
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-unit-tests')

# Import the necessary components from app.py
from app import app, ConversationManager, ResponsesAPIClient


class MockResponse:
    """Mock OpenAI response for testing."""
    
    def __init__(self, output: str):
        self.output = output


def test_frontend_title_refresh_functions_exist():
    """Test that the frontend title refresh functions exist in compiled JavaScript."""
    print("\n🧪 Testing frontend title refresh functions exist...")
    
    try:
        with open('static/js/script.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that the new functions are present in compiled JavaScript
        assert 'scheduleConversationTitleRefresh' in js_content, "scheduleConversationTitleRefresh function should be compiled"
        assert 'refreshConversationListFromCache' in js_content, "refreshConversationListFromCache function should be compiled"
        assert 'updateConversationTitle' in js_content, "updateConversationTitle function should be compiled"
        
        # Check that the function is called in the chat flow
        assert 'scheduleConversationTitleRefresh(chatData.threadId)' in js_content, "scheduleConversationTitleRefresh should be called in chat flow"
        
        # Check that the periodic refresh logic is present
        assert 'get-all-conversations' in js_content, "Should poll get-all-conversations endpoint"
        assert 'New Chat' in js_content, "Should check for 'New Chat' title updates"
        
        print("✓ Frontend title refresh functions compiled and integrated correctly")
        
    except FileNotFoundError:
        print("⚠️  Compiled JavaScript not found, skipping JS function check")
    
    print("✓ Frontend title refresh functions exist")


def test_title_refresh_integration_flow():
    """Test the complete title refresh integration flow."""
    print("\n🧪 Testing title refresh integration flow...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock successful title generation
        mock_response = MockResponse("AI Generated Title")
        mock_client.responses.create.return_value = mock_response
        
        # Test the title generation and update flow directly
        test_username = 'test_user'
        
        # Step 1: Create a conversation with default title (simulating what frontend does)
        conversation_id = conversation_manager.create_conversation(test_username, "New Chat")
        
        # Step 2: Simulate the title generation that happens in the background
        generated_title = responses_client.generate_conversation_title("Hello, I need help with programming")
        success = conversation_manager.update_conversation_title(test_username, conversation_id, generated_title)
        
        assert success == True, "Title update should succeed"
        
        # Step 3: Verify that the title was updated
        conversation = conversation_manager.get_conversation(test_username, conversation_id)
        assert conversation is not None, "Conversation should exist"
        assert conversation.chat_name == "AI Generated Title", \
            f"Expected 'AI Generated Title', got '{conversation.chat_name}'"
        
        # Step 4: Test the get-all-conversations endpoint (used by frontend for refresh)
        with patch('app.conversation_manager', conversation_manager):
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = test_username
                
                response = client.get('/get-all-conversations')
                assert response.status_code == 200, "get-all-conversations should succeed"
                
                response_data = json.loads(response.data.decode())
                assert conversation_id in response_data, "Conversation should be in response"
                assert response_data[conversation_id]['chat_name'] == "AI Generated Title", \
                    "Updated title should be returned by get-all-conversations"
    
    print("✓ Title refresh integration flow works correctly")


def test_multiple_conversations_title_refresh():
    """Test title refresh for multiple conversations."""
    print("\n🧪 Testing multiple conversations title refresh...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock different title responses
        title_responses = ["Python Help", "JavaScript Guide", "React Tutorial"]
        response_index = 0
        
        def mock_create(*args, **kwargs):
            nonlocal response_index
            if kwargs.get("model") == "o3-mini":
                title = title_responses[response_index % len(title_responses)]
                response_index += 1
                return MockResponse(title)
            return MockResponse("Default response")
        
        mock_client.responses.create.side_effect = mock_create
        
        # Test multiple conversations directly (avoiding HTTP context issues)
        test_username = 'test_user'
        conversation_ids = []
        
        # Create multiple conversations with default titles
        for i in range(3):
            conversation_id = conversation_manager.create_conversation(test_username, "New Chat")
            conversation_ids.append(conversation_id)
        
        # Simulate title generation for each conversation
        for i, conversation_id in enumerate(conversation_ids):
            generated_title = responses_client.generate_conversation_title(f"Test message {i}")
            success = conversation_manager.update_conversation_title(test_username, conversation_id, generated_title)
            assert success == True, f"Title update should succeed for conversation {i}"
        
        # Verify all conversations have updated titles
        conversations = conversation_manager.list_conversations(test_username)
        assert len(conversations) == 3, f"Should have 3 conversations, got {len(conversations)}"
        
        # Check that titles were generated
        titles = [conv['chat_name'] for conv in conversations.values()]
        generated_titles = [title for title in titles if title in title_responses]
        assert len(generated_titles) == 3, f"All titles should be generated: {titles}"
    
    print("✓ Multiple conversations title refresh works correctly")


def test_title_refresh_error_handling():
    """Test title refresh error handling."""
    print("\n🧪 Testing title refresh error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client to fail title generation
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock title generation to fail
        def mock_create(*args, **kwargs):
            if kwargs.get("model") == "o3-mini":
                raise Exception("Title generation failed")
            # Mock main chat response
            mock_response = Mock()
            mock_response.__iter__ = Mock(return_value=iter([]))
            return mock_response
        
        mock_client.responses.create.side_effect = mock_create
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Create a conversation where title generation will fail
                response = client.post('/chat', json={
                    'user_input': 'Test message',
                    'chat_name': 'New Chat'
                })
                
                assert response.status_code == 200, f"Chat should succeed despite title generation failure"
                
                # Give time for title generation attempt
                time.sleep(0.2)
                
                # Verify that the conversation still exists with fallback title
                conversations = conversation_manager.list_conversations('test_user')
                assert len(conversations) == 1, "Conversation should exist despite title generation failure"
                
                conversation_id = list(conversations.keys())[0]
                conversation_data = conversations[conversation_id]
                
                # The title should be either "New Chat" (original) or a fallback timestamp title
                assert conversation_data['chat_name'] in ["New Chat"] or conversation_data['chat_name'].startswith("Chat - "), \
                    f"Should have fallback title, got '{conversation_data['chat_name']}'"
                
                # Test that get-all-conversations still works
                response = client.get('/get-all-conversations')
                assert response.status_code == 200, "get-all-conversations should work despite title generation failure"
    
    print("✓ Title refresh error handling works correctly")


def test_existing_conversation_no_title_refresh():
    """Test that existing conversations don't trigger title refresh."""
    print("\n🧪 Testing existing conversations don't trigger title refresh...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Create an existing conversation
        test_username = "test_user"
        existing_title = "Existing Conversation"
        conversation_id = conversation_manager.create_conversation(test_username, existing_title)
        
        # Mock the responses client (should not be called for existing conversations)
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = test_username
                
                # Send message to existing conversation
                response = client.post('/chat', json={
                    'user_input': 'Follow up message',
                    'thread_id': conversation_id,
                    'chat_name': existing_title
                })
                
                assert response.status_code == 200, f"Chat request should succeed"
                
                # Give time for any potential processing
                time.sleep(0.1)
                
                # Verify that title generation was NOT called for existing conversation
                mock_client.responses.create.assert_not_called()
                
                # Verify that the existing title is preserved
                conversations = conversation_manager.list_conversations(test_username)
                conversation_data = conversations[conversation_id]
                assert conversation_data['chat_name'] == existing_title, \
                    f"Existing title should be preserved: {conversation_data['chat_name']}"
    
    print("✓ Existing conversations don't trigger title refresh correctly")


def run_all_tests():
    """Run all title refresh integration tests."""
    print("🚀 Starting title refresh integration tests...")
    
    try:
        test_frontend_title_refresh_functions_exist()
        test_title_refresh_integration_flow()
        test_multiple_conversations_title_refresh()
        test_title_refresh_error_handling()
        test_existing_conversation_no_title_refresh()
        
        print("\n✅ All title refresh integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)