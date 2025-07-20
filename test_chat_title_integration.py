#!/usr/bin/env python3
"""
Integration tests for automatic title generation in the chat route.
Tests the complete flow of creating conversations with automatic titles.
"""

import os
import tempfile
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

# Set a dummy API key for testing to avoid initialization errors
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-unit-tests')

# Import the necessary components from app.py
from app import app, ConversationManager, ResponsesAPIClient


class MockResponse:
    """Mock OpenAI response for testing."""
    
    def __init__(self, output: str):
        self.output = output


def test_chat_route_title_integration_exists():
    """Test that the chat route has title generation integration."""
    print("\n🧪 Testing chat route title integration exists...")
    
    # Test that the chat route exists
    with app.test_client() as client:
        # Test without session (should redirect to login)
        response = client.post('/chat', json={'user_input': 'test'})
        assert response.status_code == 302, "Should redirect to login without session"
    
    print("✓ Chat route title integration exists")


def test_new_conversation_title_generation():
    """Test that new conversations get automatic title generation."""
    print("\n🧪 Testing new conversation title generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock successful title generation
        mock_response = MockResponse("Python Help Guide")
        mock_client.responses.create.return_value = mock_response
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Create a new conversation by sending a message without conversation_id
                response = client.post('/chat', json={
                    'user_input': 'How do I write a Python function?',
                    'chat_name': 'Temporary Title'
                })
                
                assert response.status_code == 200, f"Chat request should succeed, got {response.status_code}"
                
                # Give the background thread time to complete title generation
                time.sleep(0.1)
                
                # Verify that title generation was called
                mock_client.responses.create.assert_called()
                
                # Check that the call was made with o3-mini model
                call_args = mock_client.responses.create.call_args
                assert call_args[1]["model"] == "o3-mini", "Should use o3-mini for title generation"
                assert "How do I write a Python function?" in call_args[1]["input"], "Should include user message"
    
    print("✓ New conversation title generation works correctly")


def test_existing_conversation_no_title_generation():
    """Test that existing conversations don't trigger title generation."""
    print("\n🧪 Testing existing conversation doesn't trigger title generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Create an existing conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(test_username, "Existing Chat")
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = test_username
                
                # Send a message to existing conversation
                response = client.post('/chat', json={
                    'user_input': 'Follow up question',
                    'thread_id': conversation_id  # Using existing conversation
                })
                
                assert response.status_code == 200, f"Chat request should succeed, got {response.status_code}"
                
                # Give time for any potential background processing
                time.sleep(0.1)
                
                # Verify that title generation was NOT called for existing conversation
                mock_client.responses.create.assert_not_called()
    
    print("✓ Existing conversation doesn't trigger title generation")


def test_title_generation_error_handling():
    """Test that title generation errors don't break the chat flow."""
    print("\n🧪 Testing title generation error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client to raise an error during title generation
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock the main chat response (should succeed)
        mock_chat_response = Mock()
        mock_chat_response.__iter__ = Mock(return_value=iter([]))  # Empty stream
        
        # Mock title generation to fail
        def mock_create(*args, **kwargs):
            if kwargs.get("model") == "o3-mini":
                raise Exception("Title generation failed")
            return mock_chat_response
        
        mock_client.responses.create.side_effect = mock_create
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Create a new conversation (should succeed despite title generation failure)
                response = client.post('/chat', json={
                    'user_input': 'Test message',
                    'chat_name': 'Temporary Title'
                })
                
                assert response.status_code == 200, f"Chat should succeed despite title generation error, got {response.status_code}"
                
                # Give time for background thread to complete (and fail)
                time.sleep(0.1)
                
                # Verify that the conversation was still created
                conversations = conversation_manager.list_conversations('test_user')
                assert len(conversations) == 1, "Conversation should be created despite title generation failure"
    
    print("✓ Title generation error handling works correctly")


def test_title_update_persistence():
    """Test that generated titles are properly persisted."""
    print("\n🧪 Testing title update persistence...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock successful title generation
        mock_response = MockResponse("JavaScript Arrays Guide")
        mock_client.responses.create.return_value = mock_response
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with app.test_client() as client:
                # Set up session
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                # Create a new conversation
                response = client.post('/chat', json={
                    'user_input': 'How do I work with arrays in JavaScript?',
                    'chat_name': 'Temporary Title'
                })
                
                assert response.status_code == 200, f"Chat request should succeed, got {response.status_code}"
                
                # Give the background thread time to complete title generation
                time.sleep(0.2)
                
                # Verify that the title was updated
                conversations = conversation_manager.list_conversations('test_user')
                assert len(conversations) == 1, "Should have one conversation"
                
                conversation_id = list(conversations.keys())[0]
                conversation_data = conversations[conversation_id]
                
                # The title should be updated from the temporary title
                assert conversation_data['chat_name'] == "JavaScript Arrays Guide", \
                    f"Expected 'JavaScript Arrays Guide', got '{conversation_data['chat_name']}'"
    
    print("✓ Title update persistence works correctly")


def test_concurrent_conversation_creation():
    """Test concurrent conversation creation with title generation."""
    print("\n🧪 Testing concurrent conversation creation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock successful title generation with different titles
        def mock_create(*args, **kwargs):
            if kwargs.get("model") == "o3-mini":
                # Return different titles based on input
                if "Python" in kwargs.get("input", ""):
                    return MockResponse("Python Guide")
                elif "JavaScript" in kwargs.get("input", ""):
                    return MockResponse("JavaScript Guide")
                else:
                    return MockResponse("General Guide")
            # Mock main chat response
            mock_response = Mock()
            mock_response.__iter__ = Mock(return_value=iter([]))
            return mock_response
        
        mock_client.responses.create.side_effect = mock_create
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            results = []
            errors = []
            
            def create_conversation_thread(user_input):
                try:
                    with app.test_client() as client:
                        # Set up session
                        with client.session_transaction() as sess:
                            sess['username'] = 'test_user'
                        
                        # Create a new conversation
                        response = client.post('/chat', json={
                            'user_input': user_input,
                            'chat_name': 'Temporary Title'
                        })
                        
                        results.append(response.status_code)
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads
            threads = []
            test_inputs = [
                "How do I use Python lists?",
                "JavaScript array methods?",
                "General programming question?"
            ]
            
            for user_input in test_inputs:
                thread = threading.Thread(target=create_conversation_thread, args=(user_input,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Give time for background title generation
            time.sleep(0.3)
            
            assert len(errors) == 0, f"No errors should occur in concurrent execution: {errors}"
            assert len(results) == 3, f"All threads should complete: {len(results)}"
            assert all(status == 200 for status in results), f"All requests should succeed: {results}"
            
            # Verify that multiple conversations were created
            conversations = conversation_manager.list_conversations('test_user')
            assert len(conversations) == 3, f"Should have 3 conversations, got {len(conversations)}"
    
    print("✓ Concurrent conversation creation works correctly")


def test_title_generation_logging():
    """Test that title generation produces appropriate logging."""
    print("\n🧪 Testing title generation logging...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test conversation manager
        conversation_manager = ConversationManager(temp_dir)
        
        # Mock the responses client
        mock_client = Mock()
        responses_client = ResponsesAPIClient(mock_client)
        
        # Mock successful title generation
        mock_response = MockResponse("Test Title")
        mock_client.responses.create.return_value = mock_response
        
        # Patch the global instances in app.py
        with patch('app.conversation_manager', conversation_manager), \
             patch('app.responses_client', responses_client):
            
            with patch('logging.info') as mock_info, \
                 patch('logging.error') as mock_error:
                
                with app.test_client() as client:
                    # Set up session
                    with client.session_transaction() as sess:
                        sess['username'] = 'test_user'
                    
                    # Create a new conversation
                    response = client.post('/chat', json={
                        'user_input': 'Test message for logging',
                        'chat_name': 'Temporary Title'
                    })
                    
                    assert response.status_code == 200, f"Chat request should succeed, got {response.status_code}"
                    
                    # Give time for background processing
                    time.sleep(0.2)
                    
                    # Verify that success logging occurred
                    mock_info.assert_called()
                    info_calls = [str(call) for call in mock_info.call_args_list]
                    success_logged = any("Successfully generated title" in call for call in info_calls)
                    assert success_logged, f"Should log successful title generation: {info_calls}"
                    
                    # Should not have error logging for successful case
                    mock_error.assert_not_called()
    
    print("✓ Title generation logging works correctly")


def run_all_tests():
    """Run all chat title integration tests."""
    print("🚀 Starting chat title integration tests...")
    
    try:
        test_chat_route_title_integration_exists()
        test_new_conversation_title_generation()
        test_existing_conversation_no_title_generation()
        test_title_generation_error_handling()
        test_title_update_persistence()
        test_concurrent_conversation_creation()
        test_title_generation_logging()
        
        print("\n✅ All chat title integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)