#!/usr/bin/env python3
"""
Unit tests for TitleGenerator class.
Tests title generation with various message types and error scenarios.
"""

import json
import time
import os
from unittest.mock import Mock, patch
import openai

# Set a dummy API key for testing to avoid initialization errors
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-unit-tests")

# Import the ResponsesAPIClient class from app.py
from app import ResponsesAPIClient


class MockResponse:
    """Mock OpenAI response for testing."""

    def __init__(self, output: str):
        self.output = output


def test_responses_client_title_method():
    """Test ResponsesAPIClient has title generation method."""
    print("\n🧪 Testing ResponsesAPIClient title generation method...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    assert hasattr(responses_client, 'generate_conversation_title'), "Should have generate_conversation_title method"
    assert callable(responses_client.generate_conversation_title), "generate_conversation_title should be callable"

    print("✓ ResponsesAPIClient has title generation method")


def test_get_title_generation_instructions():
    """Test title generation instructions."""
    print("\n🧪 Testing title generation instructions...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    instructions = responses_client._get_title_generation_instructions()

    assert "You are a title generator" in instructions, "Instructions should define role"
    assert "maximum 30 characters" in instructions, "Instructions should specify length limit"
    assert "Python Binary Search" in instructions, "Instructions should contain examples"
    assert "Generate only the title" in instructions, "Instructions should specify output format"
    assert "Extract the main topic" in instructions, "Instructions should guide topic extraction"
    assert "Use specific technical terms" in instructions, "Instructions should encourage technical terms"

    print("✓ Title generation instructions work correctly")


def test_sanitize_title():
    """Test title sanitization."""
    print("\n🧪 Testing title sanitization...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    # Test normal title
    title = responses_client._sanitize_title("Binary Search Help")
    assert title == "Binary Search Help", f"Normal title should pass through: {title}"

    # Test title with quotes
    title = responses_client._sanitize_title('"Algorithm Question"')
    assert title == "Algorithm Question", f"Quotes should be removed: {title}"

    # Test title with newlines
    title = responses_client._sanitize_title("Python\nHelp")
    assert title == "Python Help", f"Newlines should be replaced: {title}"

    # Test long title truncation
    long_title = "This is a very long title that exceeds thirty characters"
    title = responses_client._sanitize_title(long_title)
    assert len(title) <= 30, f"Title should be truncated to 30 chars: {title}"
    assert title.endswith("..."), f"Long titles should end with ellipsis: {title}"

    # Test generic titles (should use fallback)
    generic_titles = ["chat", "help", "hi", "hello", "conversation"]
    for generic in generic_titles:
        title = responses_client._sanitize_title(generic)
        assert title.startswith("Chat - "), (
            f"Generic title '{generic}' should use fallback: {title}"
        )

    # Test empty title
    title = responses_client._sanitize_title("")
    assert title.startswith("Chat - "), f"Empty title should use fallback: {title}"

    # Test very short title
    title = responses_client._sanitize_title("Hi")
    assert title.startswith("Chat - "), f"Very short title should use fallback: {title}"

    print("✓ Title sanitization works correctly")


def test_generate_fallback_title():
    """Test fallback title generation."""
    print("\n🧪 Testing fallback title generation...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    fallback_title = responses_client._generate_fallback_title()

    assert fallback_title.startswith("Chat - "), (
        f"Fallback should start with 'Chat - ': {fallback_title}"
    )
    assert len(fallback_title) <= 30, (
        f"Fallback title should be <= 30 chars: {fallback_title}"
    )

    # Test that it contains a timestamp format
    import re

    timestamp_pattern = r"Chat - \d{2}/\d{2} \d{2}:\d{2}"
    assert re.match(timestamp_pattern, fallback_title), (
        f"Fallback should match timestamp pattern: {fallback_title}"
    )

    print("✓ Fallback title generation works correctly")


def test_successful_title_generation():
    """Test successful title generation."""
    print("\n🧪 Testing successful title generation...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    # Mock successful API response
    mock_response = MockResponse("Binary Search Algorithm")
    mock_client.responses.create.return_value = mock_response

    user_message = "How do I implement a binary search algorithm in Python?"
    title = responses_client.generate_conversation_title(user_message)

    assert title == "Binary Search Algorithm", f"Should return sanitized title: {title}"

    # Verify API was called with correct parameters
    mock_client.responses.create.assert_called_once()
    call_args = mock_client.responses.create.call_args

    assert call_args[1]["model"] == "o3-mini", "Should use o3-mini model"
    assert call_args[1]["stream"] == False, "Should not stream for title generation"
    assert call_args[1]["reasoning"]["effort"] == "low", (
        "Should use low reasoning effort"
    )
    assert call_args[1]["max_output_tokens"] == 50, "Should limit output tokens"
    assert user_message[:500] in call_args[1]["input"], (
        "Should include user message in input"
    )
    assert "instructions" in call_args[1], "Should include instructions parameter"
    assert "You are a title generator" in call_args[1]["instructions"], (
        "Instructions should contain role definition"
    )

    print("✓ Successful title generation works correctly")


def test_api_error_handling():
    """Test API error handling scenarios."""
    print("\n🧪 Testing API error handling...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    user_message = "Test message"

    # Test general exception (simulating API errors)
    mock_client.responses.create.side_effect = Exception("API connection failed")
    title = responses_client.generate_conversation_title(user_message)
    assert title.startswith("Chat - "), f"API error should return fallback: {title}"

    # Test another exception type
    mock_client.responses.create.side_effect = ConnectionError("Network error")
    title = responses_client.generate_conversation_title(user_message)
    assert title.startswith("Chat - "), (
        f"Connection error should return fallback: {title}"
    )

    # Test timeout error
    mock_client.responses.create.side_effect = TimeoutError("Request timeout")
    title = responses_client.generate_conversation_title(user_message)
    assert title.startswith("Chat - "), f"Timeout error should return fallback: {title}"

    print("✓ API error handling works correctly")


def test_empty_response_handling():
    """Test handling of empty API responses."""
    print("\n🧪 Testing empty response handling...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    # Test response without output attribute
    mock_response = Mock()
    del mock_response.output  # Remove output attribute
    mock_client.responses.create.return_value = mock_response

    title = responses_client.generate_conversation_title("Test message")
    assert title.startswith("Chat - "), (
        f"Missing output should return fallback: {title}"
    )

    # Test response with empty output
    mock_response = MockResponse("")
    mock_client.responses.create.return_value = mock_response

    title = responses_client.generate_conversation_title("Test message")
    assert title.startswith("Chat - "), f"Empty output should return fallback: {title}"

    print("✓ Empty response handling works correctly")


def test_various_message_types():
    """Test title generation with various message types."""
    print("\n🧪 Testing various message types...")

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    test_cases = [
        ("How do I implement a binary search algorithm?", "Binary Search Guide"),
        ("What's the weather like?", "Weather Question"),
        (
            "I need help with my Python project that involves machine learning",
            "Python ML Project",
        ),
        ("Hi there!", "Greeting Chat"),
        ("🤔 Can you explain machine learning?", "Machine Learning Explain"),
        ("", "Empty Message Chat"),
    ]

    for user_message, expected_response in test_cases:
        # Mock API response
        mock_response = MockResponse(expected_response)
        mock_client.responses.create.return_value = mock_response

        title = responses_client.generate_conversation_title(user_message)

        # For empty message, the API will still be called but we should handle it
        if not user_message:
            # Empty message might still generate a title, but it should be valid
            assert len(title) <= 30, f"Title should be <= 30 chars: {title}"
            assert title, f"Title should not be empty for empty message"
        else:
            # Should get the mocked response (possibly sanitized)
            assert len(title) <= 30, f"Title should be <= 30 chars: {title}"
            assert title, f"Title should not be empty for message: {user_message}"

    print("✓ Various message types handled correctly")


def test_concurrent_title_generation():
    """Test concurrent title generation (thread safety)."""
    print("\n🧪 Testing concurrent title generation...")

    import threading
    import time

    mock_client = Mock()
    responses_client = ResponsesAPIClient(mock_client)

    # Mock API response with delay to simulate real API
    def mock_create(*args, **kwargs):
        time.sleep(0.1)  # Small delay
        return MockResponse("Test Title")

    mock_client.responses.create.side_effect = mock_create

    results = []
    errors = []

    def generate_title_thread(message):
        try:
            title = responses_client.generate_conversation_title(f"Test message {message}")
            results.append(title)
        except Exception as e:
            errors.append(e)

    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=generate_title_thread, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    assert len(errors) == 0, f"No errors should occur in concurrent execution: {errors}"
    assert len(results) == 5, f"All threads should complete: {len(results)}"

    print("✓ Concurrent title generation works correctly")


def run_all_tests():
    """Run all TitleGenerator tests."""
    print("🚀 Starting TitleGenerator tests...")

    try:
        test_responses_client_title_method()
        test_get_title_generation_instructions()
        test_sanitize_title()
        test_generate_fallback_title()
        test_successful_title_generation()
        test_api_error_handling()
        test_empty_response_handling()
        test_various_message_types()
        test_concurrent_title_generation()

        print("\n✅ All TitleGenerator tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
