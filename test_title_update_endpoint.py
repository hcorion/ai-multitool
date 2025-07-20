#!/usr/bin/env python3
"""
Tests for title update endpoint and frontend handling.
Verifies that the /update-conversation-title endpoint works correctly.
"""

import os
import tempfile
import json
from unittest.mock import Mock, patch

# Set a dummy API key for testing to avoid initialization errors
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-unit-tests')

# Import the necessary components from app.py
from app import app, ConversationManager


def test_title_update_endpoint_exists():
    """Test that the title update endpoint exists."""
    print("\n🧪 Testing title update endpoint exists...")
    
    with app.test_client() as client:
        # Test without session (should return 401)
        response = client.post('/update-conversation-title', json={
            'conversation_id': 'test-id',
            'title': 'Test Title'
        })
        assert response.status_code == 401, "Should return 401 without session"
        
        response_data = response.get_json()
        assert "error" in response_data, "Should return error message"
        assert "Username not in session" in response_data["error"], "Should indicate session issue"
    
    print("✓ Title update endpoint exists and handles authentication")


def test_successful_title_update():
    """Test successful title update via endpoint."""
    print("\n🧪 Testing successful title update...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Create a test conversation
        test_username = "test_user"
        original_title = "Original Title"
        conversation_id = conversation_manager.create_conversation(test_username, original_title)
        
        # Patch the global conversation manager
        with patch('app.conversation_manager', conversation_manager):
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = test_username
                
                # Update the conversation title
                new_title = "Updated Title"
                response = client.post('/update-conversation-title', json={
                    'conversation_id': conversation_id,
                    'title': new_title
                })
                
                assert response.status_code == 200, f"Request should succeed, got {response.status_code}"
                
                response_data = response.get_json()
                assert response_data["success"] == True, "Should indicate success"
                assert "conversations" in response_data, "Should return updated conversations"
                assert response_data["message"] == "Title updated successfully", "Should have success message"
                
                # Verify the title was actually updated
                conversations = response_data["conversations"]
                assert conversation_id in conversations, "Updated conversation should be in response"
                assert conversations[conversation_id]["chat_name"] == new_title, \
                    f"Expected '{new_title}', got '{conversations[conversation_id]['chat_name']}'"
    
    print("✓ Successful title update works correctly")


def test_invalid_request_formats():
    """Test handling of invalid request formats."""
    print("\n🧪 Testing invalid request formats...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)
        
        with patch('app.conversation_manager', conversation_manager):
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Test missing JSON body (Flask returns 415 for missing content-type)
                response = client.post('/update-conversation-title')
                # Flask returns 415 (Unsupported Media Type) when no JSON is provided
                assert response.status_code in [400, 415], f"Should return 400 or 415 for missing JSON, got {response.status_code}"
                
                # Test with explicit content-type but no JSON
                response = client.post('/update-conversation-title', 
                                     headers={'Content-Type': 'application/json'})
                assert response.status_code == 400, f"Should return 400 for empty JSON, got {response.status_code}"
                response_data = response.get_json()
                if response_data:  # Only check if response has JSON data
                    assert "Invalid request format" in response_data["error"], "Should indicate format error"
                
                # Test missing conversation_id
                response = client.post('/update-conversation-title', json={
                    'title': 'Test Title'
                })
                assert response.status_code == 400, "Should return 400 for missing conversation_id"
                response_data = response.get_json()
                assert "Missing conversation_id or title" in response_data["error"], "Should indicate missing fields"
                
                # Test missing title
                response = client.post('/update-conversation-title', json={
                    'conversation_id': 'test-id'
                })
                assert response.status_code == 400, "Should return 400 for missing title"
                response_data = response.get_json()
                assert "Missing conversation_id or title" in response_data["error"], "Should indicate missing fields"
                
                # Test empty values
                response = client.post('/update-conversation-title', json={
                    'conversation_id': '',
                    'title': ''
                })
                assert response.status_code == 400, "Should return 400 for empty values"
    
    print("✓ Invalid request format handling works correctly")


def test_nonexistent_conversation():
    """Test updating title for nonexistent conversation."""
    print("\n🧪 Testing nonexistent conversation handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)
        
        with patch('app.conversation_manager', conversation_manager):
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Try to update nonexistent conversation
                response = client.post('/update-conversation-title', json={
                    'conversation_id': 'nonexistent-id',
                    'title': 'New Title'
                })
                
                assert response.status_code == 400, "Should return 400 for nonexistent conversation"
                response_data = response.get_json()
                assert response_data["success"] == False, "Should indicate failure"
                assert "Failed to update conversation title" in response_data["error"], "Should indicate update failure"
    
    print("✓ Nonexistent conversation handling works correctly")


def test_server_error_handling():
    """Test handling of server errors during title update."""
    print("\n🧪 Testing server error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the update method to raise an exception
        with patch.object(conversation_manager, 'update_conversation_title') as mock_update:
            mock_update.side_effect = Exception("Simulated server error")
            
            with patch('app.conversation_manager', conversation_manager):
                with app.test_client() as client:
                    # Set up session
                    with client.session_transaction() as sess:
                        sess['username'] = 'test_user'
                    
                    # Try to update conversation title
                    response = client.post('/update-conversation-title', json={
                        'conversation_id': 'test-id',
                        'title': 'New Title'
                    })
                    
                    assert response.status_code == 500, "Should return 500 for server error"
                    response_data = response.get_json()
                    assert response_data["success"] == False, "Should indicate failure"
                    assert "Internal server error" in response_data["error"], "Should indicate server error"
    
    print("✓ Server error handling works correctly")


def test_response_format():
    """Test that the response format is correct."""
    print("\n🧪 Testing response format...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)
        
        # Create test conversations
        test_username = "test_user"
        conversation_id1 = conversation_manager.create_conversation(test_username, "Title 1")
        conversation_id2 = conversation_manager.create_conversation(test_username, "Title 2")
        
        with patch('app.conversation_manager', conversation_manager):
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = test_username
                
                # Update one conversation title
                response = client.post('/update-conversation-title', json={
                    'conversation_id': conversation_id1,
                    'title': 'Updated Title 1'
                })
                
                assert response.status_code == 200, "Request should succeed"
                response_data = response.get_json()
                
                # Verify response structure
                required_fields = ["success", "message", "conversations"]
                for field in required_fields:
                    assert field in response_data, f"Response should contain '{field}'"
                
                assert response_data["success"] == True, "Should indicate success"
                assert isinstance(response_data["message"], str), "Message should be string"
                assert isinstance(response_data["conversations"], dict), "Conversations should be dict"
                
                # Verify conversations structure
                conversations = response_data["conversations"]
                assert len(conversations) == 2, "Should return all conversations"
                
                for conv_id, conv_data in conversations.items():
                    assert "data" in conv_data, "Each conversation should have 'data'"
                    assert "chat_name" in conv_data, "Each conversation should have 'chat_name'"
                    assert "last_update" in conv_data, "Each conversation should have 'last_update'"
                
                # Verify the updated conversation
                assert conversations[conversation_id1]["chat_name"] == "Updated Title 1", \
                    "Updated conversation should have new title"
                assert conversations[conversation_id2]["chat_name"] == "Title 2", \
                    "Other conversation should be unchanged"
    
    print("✓ Response format is correct")


def test_concurrent_title_updates():
    """Test concurrent title updates."""
    print("\n🧪 Testing concurrent title updates...")
    
    import threading
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)
        
        # Create test conversations
        test_username = "test_user"
        conversation_ids = []
        for i in range(3):
            conv_id = conversation_manager.create_conversation(test_username, f"Title {i}")
            conversation_ids.append(conv_id)
        
        results = []
        errors = []
        
        def update_title_thread(conv_id, title):
            try:
                with patch('app.conversation_manager', conversation_manager):
                    with app.test_client() as client:
                        # Set up session
                        with client.session_transaction() as sess:
                            sess['username'] = test_username
                        
                        response = client.post('/update-conversation-title', json={
                            'conversation_id': conv_id,
                            'title': title
                        })
                        
                        results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i, conv_id in enumerate(conversation_ids):
            thread = threading.Thread(target=update_title_thread, args=(conv_id, f"Updated Title {i}"))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"No errors should occur in concurrent execution: {errors}"
        assert len(results) == 3, f"All threads should complete: {len(results)}"
        assert all(status == 200 for status in results), f"All requests should succeed: {results}"
        
        # Verify final state
        conversations = conversation_manager.list_conversations(test_username)
        assert len(conversations) == 3, "All conversations should still exist"
    
    print("✓ Concurrent title updates work correctly")


def test_frontend_javascript_functions():
    """Test that frontend JavaScript functions are properly compiled."""
    print("\n🧪 Testing frontend JavaScript functions...")
    
    try:
        with open('static/js/script.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that the new functions are present in compiled JavaScript
        assert 'updateConversationTitle' in js_content, "updateConversationTitle function should be compiled"
        assert 'refreshConversationListFromCache' in js_content, "refreshConversationListFromCache function should be compiled"
        assert '/update-conversation-title' in js_content, "Should contain the endpoint URL"
        assert 'conversation_id' in js_content, "Should contain conversation_id parameter"
        
        print("✓ Frontend JavaScript functions compiled correctly")
        
    except FileNotFoundError:
        print("⚠️  Compiled JavaScript not found, skipping JS function check")
    
    print("✓ Frontend JavaScript functions test completed")


def run_all_tests():
    """Run all title update endpoint tests."""
    print("🚀 Starting title update endpoint tests...")
    
    try:
        test_title_update_endpoint_exists()
        test_successful_title_update()
        test_invalid_request_formats()
        test_nonexistent_conversation()
        test_server_error_handling()
        test_response_format()
        test_concurrent_title_updates()
        test_frontend_javascript_functions()
        
        print("\n✅ All title update endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)