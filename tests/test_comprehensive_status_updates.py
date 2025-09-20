"""
Test comprehensive real-time status updates for web search and reasoning.
"""

import json
import time
from queue import Queue
from unittest.mock import Mock

import pytest

from app import StreamEventProcessor


class TestComprehensiveStatusUpdates:
    """Test comprehensive real-time status updates functionality."""

    def test_reasoning_status_events(self):
        """Test reasoning status event generation."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock reasoning events
        part_added_event = Mock()
        part_added_event.type = "response.reasoning_summary_part.added"
        part_added_event.part = Mock()
        part_added_event.part.text = "First reasoning step"
        part_added_event.part_id = "part_1"
        
        part_done_event = Mock()
        part_done_event.type = "response.reasoning_summary_part.done"
        part_done_event.part_id = "part_1"
        
        text_delta_event = Mock()
        text_delta_event.type = "response.reasoning_summary_text.delta"
        text_delta_event.delta = "reasoning text"
        
        # Process first reasoning part (should trigger reasoning_started)
        processor._handle_reasoning_summary_part_added(part_added_event)
        
        # Check reasoning_started event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "reasoning_started"
        assert status_event["part_id"] == "part_1"
        
        # Create second reasoning part (should trigger reasoning_in_progress)
        part_added_event2 = Mock()
        part_added_event2.type = "response.reasoning_summary_part.added"
        part_added_event2.part = Mock()
        part_added_event2.part.text = "Second reasoning step"
        part_added_event2.part_id = "part_2"
        
        processor._handle_reasoning_summary_part_added(part_added_event2)
        
        # Check reasoning_in_progress event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "reasoning_in_progress"
        assert status_event["part_id"] == "part_2"
        assert status_event["status"] == "thinking"
        
        # Process reasoning text delta (should trigger more reasoning_in_progress)
        processor._handle_reasoning_summary_text_delta(text_delta_event)
        
        # Check reasoning_in_progress event was sent during text generation
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "reasoning_in_progress"
        assert status_event["status"] == "thinking"
        
        # Process reasoning part done (should trigger reasoning_completed)
        processor._handle_reasoning_summary_part_done(part_done_event)
        
        # Check reasoning_completed event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "reasoning_completed"
        assert status_event["part_id"] == "part_1"

    def test_web_search_status_events_with_metadata(self):
        """Test web search status events include proper metadata."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock web search events with metadata
        in_progress_event = Mock()
        in_progress_event.type = "response.web_search_call.in_progress"
        in_progress_event.item_id = "ws_test123"
        in_progress_event.output_index = 1
        in_progress_event.sequence_number = 100
        
        searching_event = Mock()
        searching_event.type = "response.web_search_call.searching"
        searching_event.item_id = "ws_test123"
        searching_event.output_index = 1
        searching_event.sequence_number = 101
        
        completed_event = Mock()
        completed_event.type = "response.web_search_call.completed"
        completed_event.item_id = "ws_test123"
        completed_event.output_index = 1
        completed_event.sequence_number = 102
        
        # Process events
        processor._handle_web_search_call_in_progress(in_progress_event)
        processor._handle_web_search_call_searching(searching_event)
        processor._handle_web_search_call_completed(completed_event)
        
        # Collect all status events
        status_events = []
        while not event_queue.empty():
            status_events.append(json.loads(event_queue.get()))
        
        # Verify all three status events were generated
        assert len(status_events) == 3
        
        # Check search_started event
        assert status_events[0]["type"] == "search_started"
        assert status_events[0]["item_id"] == "ws_test123"
        assert status_events[0]["output_index"] == 1
        assert status_events[0]["sequence_number"] == 100
        
        # Check search_in_progress event
        assert status_events[1]["type"] == "search_in_progress"
        assert status_events[1]["status"] == "searching"
        assert status_events[1]["item_id"] == "ws_test123"
        assert status_events[1]["output_index"] == 1
        assert status_events[1]["sequence_number"] == 101
        
        # Check search_completed event
        assert status_events[2]["type"] == "search_completed"
        assert status_events[2]["item_id"] == "ws_test123"
        assert status_events[2]["output_index"] == 1
        assert status_events[2]["sequence_number"] == 102

    def test_combined_web_search_and_reasoning_status(self):
        """Test that web search and reasoning status events work together."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock events for both web search and reasoning
        search_event = Mock()
        search_event.type = "response.web_search_call.in_progress"
        search_event.item_id = "ws_test123"
        search_event.output_index = 1
        search_event.sequence_number = 100
        
        reasoning_event = Mock()
        reasoning_event.type = "response.reasoning_summary_part.added"
        reasoning_event.part = Mock()
        reasoning_event.part.text = "Reasoning about search results"
        reasoning_event.part_id = "part_1"
        
        # Process both events
        processor._handle_web_search_call_in_progress(search_event)
        processor._handle_reasoning_summary_part_added(reasoning_event)
        
        # Collect status events
        status_events = []
        while not event_queue.empty():
            status_events.append(json.loads(event_queue.get()))
        
        # Verify both types of status events were generated
        assert len(status_events) == 2
        
        # Find search and reasoning events
        search_status = next(e for e in status_events if e["type"] == "search_started")
        reasoning_status = next(e for e in status_events if e["type"] == "reasoning_started")
        
        # Verify search status
        assert search_status["item_id"] == "ws_test123"
        assert search_status["output_index"] == 1
        
        # Verify reasoning status
        assert reasoning_status["part_id"] == "part_1"

    def test_status_events_dont_interfere_with_chat_flow(self):
        """Test that status events don't interfere with normal chat message flow."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock text events
        text_created_event = Mock()
        text_created_event.type = "response.created"
        text_created_event.response = Mock()
        text_created_event.response.id = "resp_123"
        
        text_delta_event = Mock()
        text_delta_event.type = "response.output_text.delta"
        text_delta_event.delta = "Hello world"
        
        # Create mock status events
        search_event = Mock()
        search_event.type = "response.web_search_call.in_progress"
        search_event.item_id = "ws_test123"
        search_event.output_index = 1
        search_event.sequence_number = 100
        
        reasoning_event = Mock()
        reasoning_event.type = "response.reasoning_summary_part.added"
        reasoning_event.part = Mock()
        reasoning_event.part.text = "Thinking about response"
        reasoning_event.part_id = "part_1"
        
        # Process all events
        processor._handle_response_created(text_created_event)
        processor._handle_output_text_delta(text_delta_event)
        processor._handle_web_search_call_in_progress(search_event)
        processor._handle_reasoning_summary_part_added(reasoning_event)
        
        # Collect all events
        all_events = []
        while not event_queue.empty():
            all_events.append(json.loads(event_queue.get()))
        
        # Verify we have both chat and status events
        chat_events = [e for e in all_events if e["type"] in ["text_created", "text_delta"]]
        status_events = [e for e in all_events if e["type"] in ["search_started", "reasoning_started"]]
        
        assert len(chat_events) == 2
        assert len(status_events) == 2
        
        # Verify chat functionality is preserved
        assert chat_events[0]["type"] == "text_created"
        assert chat_events[1]["type"] == "text_delta"
        assert chat_events[1]["delta"] == "Hello world"
        
        # Verify status events are properly formatted
        search_status = next(e for e in status_events if e["type"] == "search_started")
        reasoning_status = next(e for e in status_events if e["type"] == "reasoning_started")
        
        assert search_status["item_id"] == "ws_test123"
        assert reasoning_status["part_id"] == "part_1"

    def test_error_handling_in_status_events(self):
        """Test that errors in status event processing don't break chat functionality."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create malformed events
        malformed_search_event = Mock()
        malformed_search_event.type = "response.web_search_call.in_progress"
        # Missing required attributes
        
        malformed_reasoning_event = Mock()
        malformed_reasoning_event.type = "response.reasoning_summary_part.added"
        # Missing part attribute
        
        # Process malformed events (should not crash)
        processor._handle_web_search_call_in_progress(malformed_search_event)
        processor._handle_reasoning_summary_part_added(malformed_reasoning_event)
        
        # Clear any events that might have been generated from malformed events
        while not event_queue.empty():
            event_queue.get()
        
        # Create valid text event to ensure chat still works
        text_delta_event = Mock()
        text_delta_event.type = "response.output_text.delta"
        text_delta_event.delta = "Chat still works"
        
        processor._handle_output_text_delta(text_delta_event)
        
        # Verify chat functionality continues to work
        assert not event_queue.empty()
        text_event = json.loads(event_queue.get())
        assert text_event["type"] == "text_delta"
        assert text_event["delta"] == "Chat still works"

    def test_reasoning_data_includes_status_metadata(self):
        """Test that reasoning data includes proper metadata for status correlation."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Set up response ID
        processor.current_response_id = "resp_123"
        
        # Process reasoning events
        part_added_event = Mock()
        part_added_event.type = "response.reasoning_summary_part.added"
        part_added_event.part = Mock()
        part_added_event.part.text = "Reasoning step"
        part_added_event.part_id = "part_1"
        
        text_done_event = Mock()
        text_done_event.type = "response.reasoning_summary_text.done"
        text_done_event.text = "Complete reasoning summary"
        
        processor._handle_reasoning_summary_part_added(part_added_event)
        processor._handle_reasoning_summary_text_done(text_done_event)
        
        # Get reasoning data
        reasoning_data = processor.get_reasoning_data()
        
        # Verify reasoning data includes proper metadata
        assert reasoning_data is not None
        assert reasoning_data["response_id"] == "resp_123"
        assert reasoning_data["complete_summary"] == "Complete reasoning summary"
        assert len(reasoning_data["summary_parts"]) == 1
        assert reasoning_data["summary_parts"][0] == "Reasoning step"
        assert reasoning_data["timestamp"] > 0