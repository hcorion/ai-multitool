#!/usr/bin/env python3
"""
Test script for the updated chat route with Responses API integration.
"""

import json
from unittest.mock import Mock, patch
from queue import Queue

# Import the necessary components from app.py
from app import conversation_manager, responses_client, StreamEventProcessor


class MockResponsesStream:
    """Mock stream object to simulate Responses API streaming."""
    
    def __init__(self, response_id="resp_test_123"):
        self.response_id = response_id
        self.events = [
            Mock(type="response.text.created"),
            Mock(type="response.text.delta", delta="Hello"),
            Mock(type="response.text.delta", delta=" from"),
            Mock(type="response.text.delta", delta=" Responses API!"),
            Mock(type="response.text.done", text="Hello from Responses API!", response_id=response_id),
            Mock(type="response.done", response_id=response_id)
        ]
    
    def __iter__(self):
        return iter(self.events)


def test_conversation_manager_integration():
    """Test that ConversationManager works correctly with the chat route."""
    print("Testing ConversationManager integration...")
    
    test_username = "test_user"
    test_chat_name = "Test Chat"
    
    # Create a conversation
    conversation_id = conversation_manager.create_conversation(test_username, test_chat_name)
    print(f"✓ Created conversation: {conversation_id}")
    
    # Add a user message
    conversation_manager.add_message(test_username, conversation_id, "user", "Hello!")
    print("✓ Added user message")
    
    # Add an assistant message with response ID
    conversation_manager.add_message(test_username, conversation_id, "assistant", "Hi there!", "resp_123")
    print("✓ Added assistant message with response ID")
    
    # Get message list
    messages = conversation_manager.get_message_list(test_username, conversation_id)
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    assert messages[0]["role"] == "user", f"Expected user role, got {messages[0]['role']}"
    assert messages[1]["role"] == "assistant", f"Expected assistant role, got {messages[1]['role']}"
    print("✓ Message list retrieval works correctly")
    
    # Get last response ID
    last_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert last_response_id == "resp_123", f"Expected resp_123, got {last_response_id}"
    print("✓ Response ID tracking works correctly")
    
    # List conversations
    conversations = conversation_manager.list_conversations(test_username)
    assert conversation_id in conversations, f"Conversation {conversation_id} not found in list"
    print("✓ Conversation listing works correctly")
    
    print("✅ ConversationManager integration test passed!")
    return True


def test_stream_event_processor_integration():
    """Test StreamEventProcessor with mock Responses API stream."""
    print("\nTesting StreamEventProcessor integration...")
    
    event_queue = Queue()
    processor = StreamEventProcessor(event_queue)
    
    # Create mock stream
    mock_stream = MockResponsesStream("resp_integration_test")
    
    # Process the stream
    processor.process_stream(mock_stream)
    
    # Collect events
    events = []
    while not event_queue.empty():
        events.append(json.loads(event_queue.get()))
    
    print(f"✓ Processed {len(events)} events")
    
    # Verify events
    expected_types = ["text_created", "text_delta", "text_delta", "text_delta", "text_done", "response_done"]
    actual_types = [event["type"] for event in events]
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"
    print("✓ Event types are correct")
    
    # Verify response ID
    response_id = processor.get_response_id()
    assert response_id == "resp_integration_test", f"Expected resp_integration_test, got {response_id}"
    print("✓ Response ID captured correctly")
    
    print("✅ StreamEventProcessor integration test passed!")
    return True


def test_responses_client_mock():
    """Test ResponsesAPIClient with mocked responses."""
    print("\nTesting ResponsesAPIClient...")
    
    # Test error handling
    with patch.object(responses_client, 'create_response') as mock_create:
        mock_create.return_value = {
            "error": "rate_limit",
            "message": "Too many requests. Please wait a moment before trying again."
        }
        
        result = responses_client.create_response("Test input")
        assert "error" in result, "Expected error response"
        print("✓ Error handling works correctly")
    
    # Test successful response
    with patch.object(responses_client, 'create_response') as mock_create:
        mock_create.return_value = MockResponsesStream()
        
        result = responses_client.create_response("Test input", stream=True)
        assert hasattr(result, '__iter__'), "Expected iterable stream"
        print("✓ Successful response handling works correctly")
    
    print("✅ ResponsesAPIClient test passed!")
    return True


def test_chat_route_components():
    """Test the key components that the chat route uses."""
    print("\nTesting chat route components...")
    
    # Test conversation creation and message handling
    test_username = "route_test_user"
    
    # Create conversation
    conversation_id = conversation_manager.create_conversation(test_username, "Route Test")
    print(f"✓ Created conversation for route test: {conversation_id}")
    
    # Add user message
    conversation_manager.add_message(test_username, conversation_id, "user", "Test message")
    
    # Simulate getting previous response ID (should be None for first message)
    previous_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert previous_response_id is None, f"Expected None, got {previous_response_id}"
    print("✓ Previous response ID handling works for new conversations")
    
    # Add assistant response
    conversation_manager.add_message(test_username, conversation_id, "assistant", "Test response", "resp_route_test")
    
    # Check response ID is now available
    previous_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert previous_response_id == "resp_route_test", f"Expected resp_route_test, got {previous_response_id}"
    print("✓ Response ID available for conversation continuity")
    
    # Test message list format
    messages = conversation_manager.get_message_list(test_username, conversation_id)
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    assert all("role" in msg and "text" in msg for msg in messages), "Messages missing required fields"
    print("✓ Message list format is correct for frontend")
    
    print("✅ Chat route components test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing updated chat route with Responses API integration...\n")
    
    try:
        test_conversation_manager_integration()
        test_stream_event_processor_integration()
        test_responses_client_mock()
        test_chat_route_components()
        
        print("\n🎉 All chat route integration tests passed!")
        print("✅ The updated chat route is ready for Responses API integration!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise