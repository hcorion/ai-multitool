#!/usr/bin/env python3
"""
Test script for StreamEventProcessor with real Responses API event types.
"""

import json
from queue import Queue
from typing import Any

# Import the actual StreamEventProcessor from app.py
from app import StreamEventProcessor


class MockRealEvent:
    """Mock event class to simulate real ResponseStreamEvent objects."""

    def __init__(self, event_type, **kwargs):
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockResponse:
    """Mock response object."""
    def __init__(self, response_id):
        self.id = response_id


class MockContentPart:
    """Mock content part object."""
    def __init__(self, text):
        self.text = text


def test_real_event_types():
    """Test StreamEventProcessor with real Responses API event types."""
    print("Testing StreamEventProcessor with real event types...")

    # Create a test event queue
    test_queue = Queue()
    processor = StreamEventProcessor(test_queue)

    # Create mock response object
    mock_response = MockResponse("resp_real_test_123")

    # Test events that match the real Responses API stream
    events = [
        MockRealEvent("response.created", response=mock_response),
        MockRealEvent("response.in_progress"),
        MockRealEvent("response.output_item.added"),
        MockRealEvent("response.content_part.added"),
        MockRealEvent("response.output_text.delta", delta="Hello"),
        MockRealEvent("response.output_text.delta", delta=" from"),
        MockRealEvent("response.output_text.delta", delta=" real"),
        MockRealEvent("response.output_text.delta", delta=" API!"),
        MockRealEvent("response.output_text.done", content_part=MockContentPart("Hello from real API!")),
        MockRealEvent("response.content_part.done"),
        MockRealEvent("response.output_item.done"),
        MockRealEvent("response.completed", response=mock_response),
    ]

    # Process events
    for event in events:
        processor._handle_stream_event(event)

    # Collect results
    results = []
    while not test_queue.empty():
        results.append(json.loads(test_queue.get()))

    print("Real event processing results:")
    for i, result in enumerate(results):
        print(f"  {i + 1}. {result}")

    # Verify response ID was captured
    response_id = processor.get_response_id()
    assert response_id == "resp_real_test_123", f"Expected resp_real_test_123, got {response_id}"

    # Verify we got the expected frontend events (text_created, text_delta, text_done, response_done)
    frontend_events = [r for r in results if r["type"] in ["text_created", "text_delta", "text_done", "response_done"]]
    expected_frontend_types = ["text_created", "text_delta", "text_delta", "text_delta", "text_delta", "text_done", "response_done"]
    actual_frontend_types = [event["type"] for event in frontend_events]
    
    assert actual_frontend_types == expected_frontend_types, (
        f"Expected {expected_frontend_types}, got {actual_frontend_types}"
    )

    # Verify accumulated text in text_done event
    text_done_event = next(r for r in results if r["type"] == "text_done")
    assert "Hello from real API!" in text_done_event["text"], (
        f"Expected accumulated text, got {text_done_event['text']}"
    )

    print("✓ All real event type tests passed!")
    return True


def test_full_real_stream():
    """Test the full stream processing with real event types."""
    print("\nTesting full real stream processing...")

    test_queue = Queue()
    processor = StreamEventProcessor(test_queue)

    # Mock response
    mock_response = MockResponse("resp_full_test_456")

    # Mock stream of real events
    mock_stream = [
        MockRealEvent("response.created", response=mock_response),
        MockRealEvent("response.in_progress"),
        MockRealEvent("response.output_item.added"),
        MockRealEvent("response.content_part.added"),
        MockRealEvent("response.output_text.delta", delta="The"),
        MockRealEvent("response.output_text.delta", delta=" migration"),
        MockRealEvent("response.output_text.delta", delta=" is"),
        MockRealEvent("response.output_text.delta", delta=" working!"),
        MockRealEvent("response.output_text.done", content_part=MockContentPart("The migration is working!")),
        MockRealEvent("response.content_part.done"),
        MockRealEvent("response.output_item.done"),
        MockRealEvent("response.completed", response=mock_response),
    ]

    # Process the entire stream
    processor.process_stream(mock_stream)

    # Collect and verify results
    results = []
    while not test_queue.empty():
        results.append(json.loads(test_queue.get()))

    print("Full real stream processing results:")
    for i, result in enumerate(results):
        print(f"  {i + 1}. {result}")

    # Verify final response ID
    assert processor.get_response_id() == "resp_full_test_456", (
        f"Expected resp_full_test_456, got {processor.get_response_id()}"
    )

    # Verify we have the essential frontend events
    frontend_event_types = [r["type"] for r in results]
    assert "text_created" in frontend_event_types, "Missing text_created event"
    assert "text_delta" in frontend_event_types, "Missing text_delta events"
    assert "text_done" in frontend_event_types, "Missing text_done event"
    assert "response_done" in frontend_event_types, "Missing response_done event"

    print("✓ Full real stream processing test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing StreamEventProcessor with real Responses API event types...\n")
    
    try:
        test_real_event_types()
        test_full_real_stream()
        
        print("\n🎉 All real event type tests passed!")
        print("✅ StreamEventProcessor now handles real Responses API events correctly!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise