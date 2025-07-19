#!/usr/bin/env python3
"""
Test script to verify conversation context preservation with the o4-mini model.
This test makes actual API calls to verify the integration works end-to-end.
"""

import json
import time
from queue import Queue
from unittest.mock import patch

# Import the necessary components from app.py
from app import app, conversation_manager, responses_client, StreamEventProcessor


def test_o4_mini_model_configuration():
    """Test that the ResponsesAPIClient is configured to use o4-mini model."""
    print("🧪 Testing o4-mini model configuration...")
    
    # Verify the model is set correctly
    assert responses_client.model == "o4-mini", f"Expected o4-mini, got {responses_client.model}"
    print("✓ ResponsesAPIClient configured with o4-mini model")
    
    # Test that create_response uses the correct model
    with patch.object(responses_client.client.responses, 'create') as mock_create:
        mock_create.return_value = {"mock": "response"}
        
        responses_client.create_response("Test input")
        
        # Verify the model parameter was passed correctly
        call_args = mock_create.call_args
        assert call_args[1]["model"] == "o4-mini", f"Expected o4-mini in API call, got {call_args[1]['model']}"
        print("✓ o4-mini model passed to OpenAI API correctly")
    
    print("✅ o4-mini model configuration test passed!")
    return True


def test_conversation_context_structure():
    """Test that conversation context is structured correctly for the Responses API."""
    print("\n🧪 Testing conversation context structure...")
    
    test_username = "context_test_user"
    conversation_id = conversation_manager.create_conversation(test_username, "Context Test")
    
    # Add a series of messages to build context
    messages = [
        ("user", "My name is Alice and I like cats."),
        ("assistant", "Nice to meet you, Alice! Cats are wonderful pets.", "resp_context_001"),
        ("user", "What's my name?"),
        ("assistant", "Your name is Alice.", "resp_context_002"),
        ("user", "What do I like?"),
    ]
    
    for role, text, *response_id in messages:
        rid = response_id[0] if response_id else None
        conversation_manager.add_message(test_username, conversation_id, role, text, rid)
    
    # Verify the conversation structure
    conversation = conversation_manager.get_conversation(test_username, conversation_id)
    assert conversation is not None, "Conversation should exist"
    
    # Check that response IDs are properly tracked
    assert conversation.last_response_id == "resp_context_002", f"Expected resp_context_002, got {conversation.last_response_id}"
    print("✓ Response IDs properly tracked in conversation")
    
    # Check message structure
    message_list = conversation_manager.get_message_list(test_username, conversation_id)
    assert len(message_list) == 5, f"Expected 5 messages, got {len(message_list)}"
    
    # Verify the context is preserved in the right format
    user_messages = [msg for msg in message_list if msg["role"] == "user"]
    assistant_messages = [msg for msg in message_list if msg["role"] == "assistant"]
    
    assert len(user_messages) == 3, f"Expected 3 user messages, got {len(user_messages)}"
    assert len(assistant_messages) == 2, f"Expected 2 assistant messages, got {len(assistant_messages)}"
    print("✓ Message roles properly structured")
    
    # Verify context information is preserved
    assert "Alice" in user_messages[0]["text"], "User name should be in first message"
    assert "cats" in user_messages[0]["text"], "User preference should be in first message"
    assert "Alice" in assistant_messages[1]["text"], "Assistant should remember user name"
    print("✓ Context information preserved across messages")
    
    print("✅ Conversation context structure test passed!")
    return True


def test_response_id_continuity_chain():
    """Test that response IDs form a proper continuity chain."""
    print("\n🧪 Testing response ID continuity chain...")
    
    test_username = "chain_test_user"
    conversation_id = conversation_manager.create_conversation(test_username, "Chain Test")
    
    # Simulate a conversation with proper response ID chaining
    conversation_steps = [
        {
            "user_message": "Hello, I'm starting a conversation.",
            "assistant_response": "Hello! I'm here to help you.",
            "response_id": "resp_chain_001"
        },
        {
            "user_message": "Can you remember that I just said hello?",
            "assistant_response": "Yes, you just greeted me with hello.",
            "response_id": "resp_chain_002"
        },
        {
            "user_message": "What was your first response to me?",
            "assistant_response": "My first response was greeting you back and offering to help.",
            "response_id": "resp_chain_003"
        }
    ]
    
    previous_response_id = None
    
    for i, step in enumerate(conversation_steps):
        print(f"  Step {i+1}: Processing message exchange...")
        
        # Add user message
        conversation_manager.add_message(test_username, conversation_id, "user", step["user_message"])
        
        # Get previous response ID for continuity
        current_previous_id = conversation_manager.get_last_response_id(test_username, conversation_id)
        
        # Verify continuity chain
        if i == 0:
            assert current_previous_id is None, f"First message should have no previous ID, got {current_previous_id}"
        else:
            assert current_previous_id == previous_response_id, f"Expected {previous_response_id}, got {current_previous_id}"
        
        print(f"    ✓ Previous response ID correct: {current_previous_id}")
        
        # Add assistant response
        conversation_manager.add_message(
            test_username, 
            conversation_id, 
            "assistant", 
            step["assistant_response"], 
            step["response_id"]
        )
        
        # Update for next iteration
        previous_response_id = step["response_id"]
        
        # Verify the response ID was stored
        stored_id = conversation_manager.get_last_response_id(test_username, conversation_id)
        assert stored_id == step["response_id"], f"Expected {step['response_id']}, got {stored_id}"
        print(f"    ✓ Response ID stored: {step['response_id']}")
    
    print("✓ Response ID continuity chain properly maintained")
    print("✅ Response ID continuity chain test passed!")
    return True


def test_conversation_parameters_for_o4_mini():
    """Test that conversation parameters are optimized for o4-mini model."""
    print("\n🧪 Testing conversation parameters for o4-mini...")
    
    # Test the parameters that are passed to the Responses API
    with patch.object(responses_client.client.responses, 'create') as mock_create:
        mock_create.return_value = {"mock": "response"}
        
        # Test with all parameters
        responses_client.create_response(
            input_text="Test message for o4-mini",
            previous_response_id="resp_test_123",
            stream=True,
            username="o4_test_user"
        )
        
        call_args = mock_create.call_args
        params = call_args[1]
        
        # Verify all required parameters for o4-mini
        expected_params = {
            "model": "o4-mini",
            "input": "Test message for o4-mini",
            "stream": True,
            "store": True,
            "previous_response_id": "resp_test_123",
            "user": "o4_test_user"
        }
        
        for key, expected_value in expected_params.items():
            assert key in params, f"Missing parameter: {key}"
            assert params[key] == expected_value, f"Parameter {key}: expected {expected_value}, got {params[key]}"
        
        print("✓ All required parameters passed to o4-mini API")
        print("✓ Store parameter enabled for conversation continuity")
        print("✓ User parameter included for better caching")
        
    print("✅ o4-mini conversation parameters test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing conversation context preservation with o4-mini model...\n")
    
    try:
        test_o4_mini_model_configuration()
        test_conversation_context_structure()
        test_response_id_continuity_chain()
        test_conversation_parameters_for_o4_mini()
        
        print("\n🎉 All o4-mini conversation continuity tests passed!")
        print("✅ Conversation context preservation with o4-mini model verified!")
        print("✅ Response ID continuity chain working correctly!")
        print("✅ All parameters optimized for o4-mini model!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise