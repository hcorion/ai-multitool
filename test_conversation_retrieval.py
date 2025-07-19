#!/usr/bin/env python3
"""
Test script for conversation retrieval and listing functionality.
This tests the updated routes and functions that now use local storage instead of OpenAI threads.
"""

import json
import time
from unittest.mock import patch
from flask import Flask

# Import the necessary components from app.py
from app import app, conversation_manager


def test_chat_get_route():
    """Test the /chat GET route with local conversation storage."""
    print("🧪 Testing /chat GET route with local storage...")

    test_username = "get_route_test_user"

    # Create a conversation with some messages
    conversation_id = conversation_manager.create_conversation(
        test_username, "GET Route Test"
    )
    conversation_manager.add_message(
        test_username, conversation_id, "user", "Hello from GET test"
    )
    conversation_manager.add_message(
        test_username,
        conversation_id,
        "assistant",
        "Hi there! This is a test response.",
        "resp_get_001",
    )
    conversation_manager.add_message(
        test_username, conversation_id, "user", "How are you?"
    )
    conversation_manager.add_message(
        test_username,
        conversation_id,
        "assistant",
        "I'm doing well, thank you!",
        "resp_get_002",
    )

    print(f"✓ Created test conversation: {conversation_id}")

    # Test the GET route
    with app.test_client() as client:
        # Set up session
        with client.session_transaction() as sess:
            sess["username"] = test_username

        # Make GET request to /chat
        response = client.get(f"/chat?thread_id={conversation_id}")

        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # Parse response data
        response_data = json.loads(response.data.decode())

        # Verify response structure
        assert "threadId" in response_data, "Response missing threadId"
        assert "messages" in response_data, "Response missing messages"
        assert response_data["threadId"] == conversation_id, (
            f"Expected {conversation_id}, got {response_data['threadId']}"
        )

        # Verify messages
        messages = response_data["messages"]
        assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"

        # Verify message structure and content
        expected_messages = [
            {"role": "user", "text": "Hello from GET test"},
            {"role": "assistant", "text": "Hi there! This is a test response."},
            {"role": "user", "text": "How are you?"},
            {"role": "assistant", "text": "I'm doing well, thank you!"},
        ]

        for i, expected in enumerate(expected_messages):
            actual = messages[i]
            assert actual["role"] == expected["role"], (
                f"Message {i}: expected role {expected['role']}, got {actual['role']}"
            )
            assert actual["text"] == expected["text"], (
                f"Message {i}: expected text {expected['text']}, got {actual['text']}"
            )

        print("✓ /chat GET route returns correct conversation data")
        print("✓ Message structure matches frontend expectations")
        print("✓ ThreadId field maintained for frontend compatibility")

    print("✅ /chat GET route test passed!")
    return True


def test_get_all_conversations_route():
    """Test the /get-all-conversations route with new conversation structure."""
    print("\n🧪 Testing /get-all-conversations route...")

    test_username = "list_route_test_user"

    # Create multiple conversations
    conversations_data = [
        {
            "name": "First Conversation",
            "messages": [("user", "Hello 1"), ("assistant", "Hi 1", "resp_list_001")],
        },
        {
            "name": "Second Conversation",
            "messages": [("user", "Hello 2"), ("assistant", "Hi 2", "resp_list_002")],
        },
        {
            "name": "Third Conversation",
            "messages": [("user", "Hello 3")],
        },  # No assistant response yet
    ]

    created_conversations = []

    for conv_data in conversations_data:
        conv_id = conversation_manager.create_conversation(
            test_username, conv_data["name"]
        )
        created_conversations.append(conv_id)

        for message in conv_data["messages"]:
            role, text = message[:2]
            response_id = message[2] if len(message) > 2 else None
            conversation_manager.add_message(
                test_username, conv_id, role, text, response_id
            )

        # Add a small delay to ensure different timestamps
        time.sleep(0.01)

    print(f"✓ Created {len(created_conversations)} test conversations")

    # Test the GET route
    with app.test_client() as client:
        # Set up session
        with client.session_transaction() as sess:
            sess["username"] = test_username

        # Make GET request to /get-all-conversations
        response = client.get("/get-all-conversations")

        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # Parse response data
        conversations = json.loads(response.data.decode())

        # Verify we got all conversations
        assert len(conversations) == 3, (
            f"Expected 3 conversations, got {len(conversations)}"
        )

        # Verify each conversation has the required structure
        for conv_id, conv_data in conversations.items():
            assert conv_id in created_conversations, (
                f"Unexpected conversation ID: {conv_id}"
            )

            # Check required fields
            required_fields = ["data", "chat_name", "last_update"]
            for field in required_fields:
                assert field in conv_data, (
                    f"Conversation {conv_id} missing field: {field}"
                )

            # Check data structure
            data = conv_data["data"]
            assert "id" in data, f"Conversation {conv_id} data missing id"
            assert "created_at" in data, (
                f"Conversation {conv_id} data missing created_at"
            )
            assert "object" in data, f"Conversation {conv_id} data missing object"
            assert data["object"] == "conversation", (
                f"Expected object=conversation, got {data['object']}"
            )

            # Verify chat name matches what we created
            expected_names = [cd["name"] for cd in conversations_data]
            assert conv_data["chat_name"] in expected_names, (
                f"Unexpected chat name: {conv_data['chat_name']}"
            )

        print("✓ All conversations returned with correct structure")
        print("✓ Required fields present in each conversation")
        print("✓ Data format compatible with frontend expectations")

    print("✅ /get-all-conversations route test passed!")
    return True


def test_conversation_manager_message_list():
    """Test ConversationManager.get_message_list method directly."""
    print("\n🧪 Testing ConversationManager.get_message_list method...")

    test_username = "message_list_test_user"
    conversation_id = conversation_manager.create_conversation(
        test_username, "Message List Test"
    )

    # Add various types of messages
    test_messages = [
        ("user", "First user message"),
        ("assistant", "First assistant response", "resp_ml_001"),
        ("user", "Second user message with special chars: !@#$%^&*()"),
        ("assistant", "Second assistant response with emoji 😊", "resp_ml_002"),
        ("user", "Third user message\nwith newlines\nand multiple lines"),
        ("assistant", "Final response", "resp_ml_003"),
    ]

    for message in test_messages:
        role, text = message[:2]
        response_id = message[2] if len(message) > 2 else None
        conversation_manager.add_message(
            test_username, conversation_id, role, text, response_id
        )

    print(f"✓ Added {len(test_messages)} test messages")

    # Get message list
    message_list = conversation_manager.get_message_list(test_username, conversation_id)

    # Verify message count
    assert len(message_list) == len(test_messages), (
        f"Expected {len(test_messages)} messages, got {len(message_list)}"
    )

    # Verify message structure and content
    for i, (expected_role, expected_text, *_) in enumerate(test_messages):
        actual_message = message_list[i]

        # Check required fields
        assert "role" in actual_message, f"Message {i} missing role field"
        assert "text" in actual_message, f"Message {i} missing text field"

        # Check content
        assert actual_message["role"] == expected_role, (
            f"Message {i}: expected role {expected_role}, got {actual_message['role']}"
        )
        assert actual_message["text"] == expected_text, (
            f"Message {i}: expected text {expected_text}, got {actual_message['text']}"
        )

    print("✓ Message list structure correct")
    print("✓ All message content preserved accurately")
    print("✓ Special characters and formatting preserved")

    print("✅ ConversationManager.get_message_list test passed!")
    return True


def test_frontend_compatibility():
    """Test that the JSON response format maintains frontend compatibility."""
    print("\n🧪 Testing frontend compatibility...")

    test_username = "frontend_test_user"

    # Create a conversation that mimics real usage
    conversation_id = conversation_manager.create_conversation(
        test_username, "Frontend Compatibility Test"
    )

    # Add realistic conversation
    realistic_messages = [
        ("user", "Hello, I need help with Python programming."),
        (
            "assistant",
            "I'd be happy to help you with Python! What specific topic or problem are you working on?",
            "resp_fe_001",
        ),
        ("user", "I'm trying to understand list comprehensions."),
        (
            "assistant",
            "List comprehensions are a concise way to create lists in Python. Here's a basic example:\n\n```python\n# Traditional way\nresult = []\nfor i in range(10):\n    if i % 2 == 0:\n        result.append(i * 2)\n\n# List comprehension\nresult = [i * 2 for i in range(10) if i % 2 == 0]\n```\n\nBoth create the same list: [0, 4, 8, 12, 16]",
            "resp_fe_002",
        ),
        ("user", "That's helpful! Can you show me a more complex example?"),
    ]

    for role, text, *response_id in realistic_messages:
        rid = response_id[0] if response_id else None
        conversation_manager.add_message(
            test_username, conversation_id, role, text, rid
        )

    print("✓ Created realistic conversation")

    # Test /chat GET response format
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = test_username

        response = client.get(f"/chat?thread_id={conversation_id}")
        chat_data = json.loads(response.data.decode())

        # Verify frontend-expected structure
        assert isinstance(chat_data, dict), "Chat response should be a dictionary"
        assert "threadId" in chat_data, "Missing threadId field for frontend"
        assert "messages" in chat_data, "Missing messages field for frontend"
        assert isinstance(chat_data["messages"], list), "Messages should be a list"

        # Verify message format
        for message in chat_data["messages"]:
            assert isinstance(message, dict), "Each message should be a dictionary"
            assert "role" in message, "Message missing role field"
            assert "text" in message, "Message missing text field"
            assert message["role"] in ["user", "assistant"], (
                f"Invalid role: {message['role']}"
            )
            assert isinstance(message["text"], str), "Message text should be a string"

        print("✓ /chat GET response format compatible with frontend")

    # Test /get-all-conversations response format
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = test_username

        response = client.get("/get-all-conversations")
        conversations_data = json.loads(response.data.decode())

        # Verify frontend-expected structure
        assert isinstance(conversations_data, dict), (
            "Conversations response should be a dictionary"
        )

        for conv_id, conv_data in conversations_data.items():
            assert isinstance(conv_id, str), "Conversation ID should be a string"
            assert isinstance(conv_data, dict), (
                "Conversation data should be a dictionary"
            )

            # Check required fields for frontend
            frontend_fields = ["data", "chat_name", "last_update"]
            for field in frontend_fields:
                assert field in conv_data, f"Missing frontend field: {field}"

            # Check data structure
            assert isinstance(conv_data["data"], dict), (
                "Conversation data.data should be a dictionary"
            )
            assert isinstance(conv_data["chat_name"], str), (
                "chat_name should be a string"
            )
            assert isinstance(conv_data["last_update"], (int, float)), (
                "last_update should be a number"
            )

        print("✓ /get-all-conversations response format compatible with frontend")

    print("✅ Frontend compatibility test passed!")
    return True


def test_error_handling():
    """Test error handling for conversation retrieval."""
    print("\n🧪 Testing error handling...")

    test_username = "error_test_user"

    # Test /chat GET with non-existent conversation
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = test_username

        # Try to get a non-existent conversation
        fake_conversation_id = "non-existent-conversation-id"
        response = client.get(f"/chat?thread_id={fake_conversation_id}")

        # Should return empty message list for non-existent conversation
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        response_data = json.loads(response.data.decode())
        assert response_data["messages"] == [], (
            "Non-existent conversation should return empty messages"
        )
        print("✓ Non-existent conversation handled gracefully")

    # Test /get-all-conversations with user who has no conversations
    new_username = "no_conversations_user"
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = new_username

        response = client.get("/get-all-conversations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        conversations_data = json.loads(response.data.decode())
        assert conversations_data == {}, (
            "User with no conversations should return empty dict"
        )
        print("✓ User with no conversations handled gracefully")

    print("✅ Error handling test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing conversation retrieval and listing functionality...\n")

    try:
        test_chat_get_route()
        test_get_all_conversations_route()
        test_conversation_manager_message_list()
        test_frontend_compatibility()
        test_error_handling()

        print("\n🎉 All conversation retrieval and listing tests passed!")
        print("✅ /chat GET route using local storage correctly!")
        print("✅ /get-all-conversations route working with new structure!")
        print("✅ ConversationManager.get_message_list functioning properly!")
        print("✅ Frontend compatibility maintained!")
        print("✅ Error handling working correctly!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
