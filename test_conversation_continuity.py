#!/usr/bin/env python3
"""
Test script for conversation continuity with response IDs.
This tests the complete conversation flow across multiple message exchanges.
"""

import json
import time
from queue import Queue
from unittest.mock import Mock, patch, MagicMock

# Import the necessary components from app.py
from app import app, conversation_manager, responses_client, StreamEventProcessor


class MockResponsesStream:
    """Mock stream object to simulate Responses API streaming with response IDs."""
    
    def __init__(self, response_id, response_text="Mock response"):
        self.response_id = response_id
        self.response_text = response_text
        self.events = [
            Mock(type="response.created", response=Mock(id=response_id)),
            Mock(type="response.in_progress"),
            Mock(type="response.output_item.added"),
            Mock(type="response.content_part.added"),
            Mock(type="response.output_text.delta", delta=response_text[:5]),
            Mock(type="response.output_text.delta", delta=response_text[5:]),
            Mock(type="response.output_text.done", content_part=Mock(text=response_text)),
            Mock(type="response.content_part.done"),
            Mock(type="response.output_item.done"),
            Mock(type="response.completed", response=Mock(id=response_id))
        ]
    
    def __iter__(self):
        return iter(self.events)


def test_conversation_continuity_flow():
    """Test complete conversation continuity across multiple exchanges."""
    print("🧪 Testing conversation continuity with response IDs...")
    
    test_username = "continuity_test_user"
    test_chat_name = "Continuity Test Chat"
    
    # Step 1: Create a new conversation
    conversation_id = conversation_manager.create_conversation(test_username, test_chat_name)
    print(f"✓ Created conversation: {conversation_id}")
    
    # Step 2: First message exchange
    print("\n--- First Message Exchange ---")
    
    # Add user message
    user_message_1 = "Hello, how are you?"
    conversation_manager.add_message(test_username, conversation_id, "user", user_message_1)
    print(f"✓ Added user message: {user_message_1}")
    
    # Check that there's no previous response ID (first message)
    previous_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert previous_response_id is None, f"Expected None for first message, got {previous_response_id}"
    print("✓ No previous response ID for first message (correct)")
    
    # Simulate assistant response
    assistant_response_1 = "Hello! I'm doing well, thank you for asking."
    response_id_1 = "resp_continuity_001"
    conversation_manager.add_message(test_username, conversation_id, "assistant", assistant_response_1, response_id_1)
    print(f"✓ Added assistant response with ID: {response_id_1}")
    
    # Verify response ID is now available
    last_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert last_response_id == response_id_1, f"Expected {response_id_1}, got {last_response_id}"
    print("✓ Response ID correctly stored and retrievable")
    
    # Step 3: Second message exchange (testing continuity)
    print("\n--- Second Message Exchange ---")
    
    # Add second user message
    user_message_2 = "What's the weather like today?"
    conversation_manager.add_message(test_username, conversation_id, "user", user_message_2)
    print(f"✓ Added second user message: {user_message_2}")
    
    # Get previous response ID for continuity
    previous_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert previous_response_id == response_id_1, f"Expected {response_id_1}, got {previous_response_id}"
    print(f"✓ Previous response ID available for continuity: {previous_response_id}")
    
    # Simulate second assistant response
    assistant_response_2 = "I don't have access to current weather data, but I can help you find weather information."
    response_id_2 = "resp_continuity_002"
    conversation_manager.add_message(test_username, conversation_id, "assistant", assistant_response_2, response_id_2)
    print(f"✓ Added second assistant response with ID: {response_id_2}")
    
    # Step 4: Third message exchange (testing continued continuity)
    print("\n--- Third Message Exchange ---")
    
    # Add third user message
    user_message_3 = "Can you remember what I asked you first?"
    conversation_manager.add_message(test_username, conversation_id, "user", user_message_3)
    print(f"✓ Added third user message: {user_message_3}")
    
    # Get previous response ID (should now be the second response)
    previous_response_id = conversation_manager.get_last_response_id(test_username, conversation_id)
    assert previous_response_id == response_id_2, f"Expected {response_id_2}, got {previous_response_id}"
    print(f"✓ Previous response ID updated correctly: {previous_response_id}")
    
    # Step 5: Verify complete conversation history
    print("\n--- Conversation History Verification ---")
    
    messages = conversation_manager.get_message_list(test_username, conversation_id)
    assert len(messages) == 5, f"Expected 5 messages, got {len(messages)}"
    print(f"✓ Conversation has {len(messages)} messages")
    
    # Verify message order and content
    expected_messages = [
        {"role": "user", "text": user_message_1},
        {"role": "assistant", "text": assistant_response_1},
        {"role": "user", "text": user_message_2},
        {"role": "assistant", "text": assistant_response_2},
        {"role": "user", "text": user_message_3},
    ]
    
    for i, expected in enumerate(expected_messages):
        actual = messages[i]
        assert actual["role"] == expected["role"], f"Message {i}: expected role {expected['role']}, got {actual['role']}"
        assert actual["text"] == expected["text"], f"Message {i}: expected text {expected['text']}, got {actual['text']}"
    
    print("✓ All messages in correct order with correct content")
    
    # Step 6: Test conversation metadata
    print("\n--- Conversation Metadata Verification ---")
    
    conversation = conversation_manager.get_conversation(test_username, conversation_id)
    assert conversation is not None, "Conversation should exist"
    assert conversation.chat_name == test_chat_name, f"Expected {test_chat_name}, got {conversation.chat_name}"
    assert conversation.last_response_id == response_id_2, f"Expected {response_id_2}, got {conversation.last_response_id}"
    print("✓ Conversation metadata is correct")
    
    print("\n🎉 Conversation continuity test passed!")
    return True


def test_stream_processor_response_id_extraction():
    """Test that StreamEventProcessor correctly extracts response IDs."""
    print("\n🧪 Testing StreamEventProcessor response ID extraction...")
    
    event_queue = Queue()
    processor = StreamEventProcessor(event_queue)
    
    # Test with mock stream
    test_response_id = "resp_extraction_test_123"
    mock_stream = MockResponsesStream(test_response_id, "Test response for ID extraction")
    
    # Process the stream
    processor.process_stream(mock_stream)
    
    # Verify response ID was extracted
    extracted_id = processor.get_response_id()
    assert extracted_id == test_response_id, f"Expected {test_response_id}, got {extracted_id}"
    print(f"✓ Response ID correctly extracted: {extracted_id}")
    
    # Verify events were generated
    events = []
    while not event_queue.empty():
        events.append(json.loads(event_queue.get()))
    
    # Check that response_done event contains the response ID
    response_done_events = [e for e in events if e["type"] == "response_done"]
    assert len(response_done_events) == 1, f"Expected 1 response_done event, got {len(response_done_events)}"
    assert response_done_events[0]["response_id"] == test_response_id, f"Expected {test_response_id} in response_done event"
    print("✓ Response ID included in response_done event")
    
    print("✅ StreamEventProcessor response ID extraction test passed!")
    return True


def test_responses_client_previous_response_id():
    """Test that ResponsesAPIClient correctly passes previous_response_id."""
    print("\n🧪 Testing ResponsesAPIClient previous_response_id handling...")
    
    test_input = "Test message for continuity"
    test_previous_id = "resp_previous_test_456"
    test_username = "api_test_user"
    
    # Mock the OpenAI client's responses.create method
    with patch.object(responses_client.client.responses, 'create') as mock_create:
        mock_create.return_value = MockResponsesStream("resp_new_789", "API response")
        
        # Call create_response with previous_response_id
        result = responses_client.create_response(
            input_text=test_input,
            previous_response_id=test_previous_id,
            stream=True,
            username=test_username
        )
        
        # Verify the API was called with correct parameters
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        
        # Check that previous_response_id was passed
        assert call_args[1]["previous_response_id"] == test_previous_id, "previous_response_id not passed correctly"
        assert call_args[1]["input"] == test_input, "input not passed correctly"
        assert call_args[1]["stream"] == True, "stream not passed correctly"
        assert call_args[1]["user"] == test_username, "user parameter not passed correctly"
        assert call_args[1]["model"] == "o4-mini", "model not set correctly"
        assert call_args[1]["store"] == True, "store parameter not set correctly"
        
        print("✓ ResponsesAPIClient correctly passes previous_response_id to OpenAI API")
        print("✓ All other parameters passed correctly")
    
    print("✅ ResponsesAPIClient previous_response_id test passed!")
    return True


def test_conversation_state_management():
    """Test proper conversation state management across multiple exchanges."""
    print("\n🧪 Testing conversation state management...")
    
    test_username = "state_test_user"
    
    # Create multiple conversations to test isolation
    conv1_id = conversation_manager.create_conversation(test_username, "Conversation 1")
    conv2_id = conversation_manager.create_conversation(test_username, "Conversation 2")
    
    print(f"✓ Created two conversations: {conv1_id[:8]}... and {conv2_id[:8]}...")
    
    # Add messages to first conversation
    conversation_manager.add_message(test_username, conv1_id, "user", "Message in conv 1")
    conversation_manager.add_message(test_username, conv1_id, "assistant", "Response in conv 1", "resp_conv1_001")
    
    # Add messages to second conversation
    conversation_manager.add_message(test_username, conv2_id, "user", "Message in conv 2")
    conversation_manager.add_message(test_username, conv2_id, "assistant", "Response in conv 2", "resp_conv2_001")
    
    # Verify conversation isolation
    conv1_response_id = conversation_manager.get_last_response_id(test_username, conv1_id)
    conv2_response_id = conversation_manager.get_last_response_id(test_username, conv2_id)
    
    assert conv1_response_id == "resp_conv1_001", f"Conv1 response ID incorrect: {conv1_response_id}"
    assert conv2_response_id == "resp_conv2_001", f"Conv2 response ID incorrect: {conv2_response_id}"
    print("✓ Conversation state properly isolated between conversations")
    
    # Verify message lists are separate
    conv1_messages = conversation_manager.get_message_list(test_username, conv1_id)
    conv2_messages = conversation_manager.get_message_list(test_username, conv2_id)
    
    assert len(conv1_messages) == 2, f"Conv1 should have 2 messages, got {len(conv1_messages)}"
    assert len(conv2_messages) == 2, f"Conv2 should have 2 messages, got {len(conv2_messages)}"
    assert conv1_messages[1]["text"] == "Response in conv 1", "Conv1 message content incorrect"
    assert conv2_messages[1]["text"] == "Response in conv 2", "Conv2 message content incorrect"
    print("✓ Message lists properly isolated between conversations")
    
    print("✅ Conversation state management test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing conversation continuity with response IDs...\n")
    
    try:
        test_conversation_continuity_flow()
        test_stream_processor_response_id_extraction()
        test_responses_client_previous_response_id()
        test_conversation_state_management()
        
        print("\n🎉 All conversation continuity tests passed!")
        print("✅ Conversation continuity with response IDs is working correctly!")
        print("✅ Context preservation across multiple message exchanges verified!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise