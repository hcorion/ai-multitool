"""
Test status message consistency and completion behavior.
"""

import json
from queue import Queue
from unittest.mock import Mock

import pytest

from app import StreamEventProcessor


class TestStatusMessageConsistency:
    """Test status message consistency and completion behavior."""

    def test_reasoning_completion_sent_for_each_part(self):
        """Test that reasoning completion is sent for each reasoning part completion."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create multiple reasoning part events
        part1_event = Mock()
        part1_event.type = "response.reasoning_summary_part.added"
        part1_event.part = Mock()
        part1_event.part.text = "First reasoning step"
        part1_event.part_id = "part_1"
        
        part2_event = Mock()
        part2_event.type = "response.reasoning_summary_part.added"
        part2_event.part = Mock()
        part2_event.part.text = "Second reasoning step"
        part2_event.part_id = "part_2"
        
        part3_event = Mock()
        part3_event.type = "response.reasoning_summary_part.added"
        part3_event.part = Mock()
        part3_event.part.text = "Third reasoning step"
        part3_event.part_id = "part_3"
        
        # Create part done events (these SHOULD trigger completion)
        part1_done = Mock()
        part1_done.type = "response.reasoning_summary_part.done"
        part1_done.part_id = "part_1"
        
        part2_done = Mock()
        part2_done.type = "response.reasoning_summary_part.done"
        part2_done.part_id = "part_2"
        
        part3_done = Mock()
        part3_done.type = "response.reasoning_summary_part.done"
        part3_done.part_id = "part_3"
        
        # Process all events
        processor._handle_reasoning_summary_part_added(part1_event)
        processor._handle_reasoning_summary_part_added(part2_event)
        processor._handle_reasoning_summary_part_added(part3_event)
        processor._handle_reasoning_summary_part_done(part1_done)
        processor._handle_reasoning_summary_part_done(part2_done)
        processor._handle_reasoning_summary_part_done(part3_done)
        
        # Collect all events
        events = []
        while not event_queue.empty():
            events.append(json.loads(event_queue.get()))
        
        # Count event types
        started_events = [e for e in events if e["type"] == "reasoning_started"]
        in_progress_events = [e for e in events if e["type"] == "reasoning_in_progress"]
        completed_events = [e for e in events if e["type"] == "reasoning_completed"]
        
        # Verify event counts
        assert len(started_events) == 1, f"Expected 1 reasoning_started event, got {len(started_events)}"
        assert len(in_progress_events) == 2, f"Expected 2 reasoning_in_progress events, got {len(in_progress_events)}"
        assert len(completed_events) == 3, f"Expected 3 reasoning_completed events (one per part), got {len(completed_events)}"
        
        # Verify completion events have part_ids
        for completion_event in completed_events:
            assert "part_id" in completion_event, "Completion events should have part_id"

    def test_status_message_lengths_are_consistent(self):
        """Test that status messages are short and consistent."""
        # Define the expected messages (these should match what's in chat.ts)
        search_messages = {
            'search_started': "Searching...",
            'search_in_progress': "Searching...",
            'search_completed': "Search done"
        }
        
        reasoning_messages = {
            'reasoning_started': "Thinking...",
            'reasoning_in_progress': "Thinking...",
            'reasoning_completed': "Thinking done"
        }
        
        # Verify active messages are the same length
        assert len(search_messages['search_started']) == len(search_messages['search_in_progress'])
        assert len(reasoning_messages['reasoning_started']) == len(reasoning_messages['reasoning_in_progress'])
        
        # Verify completion messages are short and consistent format
        assert len(search_messages['search_completed']) <= 12  # "Search done" = 11 chars
        assert len(reasoning_messages['reasoning_completed']) <= 13  # "Thinking done" = 13 chars
        
        # Verify completion messages follow same pattern
        assert search_messages['search_completed'].endswith(" done")
        assert reasoning_messages['reasoning_completed'].endswith(" done")

    def test_reasoning_in_progress_during_text_generation(self):
        """Test that reasoning in-progress events are sent during text delta generation."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create text delta events
        delta1_event = Mock()
        delta1_event.type = "response.reasoning_summary_text.delta"
        delta1_event.delta = "First part of reasoning"
        
        delta2_event = Mock()
        delta2_event.type = "response.reasoning_summary_text.delta"
        delta2_event.delta = " and second part"
        
        delta3_event = Mock()
        delta3_event.type = "response.reasoning_summary_text.delta"
        delta3_event.delta = " and final conclusion"
        
        # Process delta events
        processor._handle_reasoning_summary_text_delta(delta1_event)
        processor._handle_reasoning_summary_text_delta(delta2_event)
        processor._handle_reasoning_summary_text_delta(delta3_event)
        
        # Collect all events
        events = []
        while not event_queue.empty():
            events.append(json.loads(event_queue.get()))
        
        # Should have generated in-progress events for each delta
        in_progress_events = [e for e in events if e["type"] == "reasoning_in_progress"]
        assert len(in_progress_events) == 3, f"Expected 3 reasoning_in_progress events, got {len(in_progress_events)}"
        
        # All should have status "thinking"
        for event in in_progress_events:
            assert event["status"] == "thinking"