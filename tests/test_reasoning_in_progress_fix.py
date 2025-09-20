"""
Test that reasoning in-progress events are properly generated.
"""

import json
from queue import Queue
from unittest.mock import Mock

import pytest

from app import StreamEventProcessor


class TestReasoningInProgressFix:
    """Test that reasoning in-progress events work correctly."""

    def test_reasoning_events_full_flow(self):
        """Test the complete flow of reasoning events."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Simulate a complete reasoning flow
        
        # 1. First reasoning part starts
        part1_added = Mock()
        part1_added.type = "response.reasoning_summary_part.added"
        part1_added.part = Mock()
        part1_added.part.text = "Let me think about this problem"
        part1_added.part_id = "part_1"
        
        processor._handle_reasoning_summary_part_added(part1_added)
        
        # 2. Text generation starts (multiple deltas)
        delta1 = Mock()
        delta1.type = "response.reasoning_summary_text.delta"
        delta1.delta = "I need to consider"
        
        delta2 = Mock()
        delta2.type = "response.reasoning_summary_text.delta"
        delta2.delta = " the various factors"
        
        delta3 = Mock()
        delta3.type = "response.reasoning_summary_text.delta"
        delta3.delta = " involved in this decision"
        
        processor._handle_reasoning_summary_text_delta(delta1)
        processor._handle_reasoning_summary_text_delta(delta2)
        processor._handle_reasoning_summary_text_delta(delta3)
        
        # 3. Second reasoning part starts
        part2_added = Mock()
        part2_added.type = "response.reasoning_summary_part.added"
        part2_added.part = Mock()
        part2_added.part.text = "Now let me analyze the options"
        part2_added.part_id = "part_2"
        
        processor._handle_reasoning_summary_part_added(part2_added)
        
        # 4. More text generation
        delta4 = Mock()
        delta4.type = "response.reasoning_summary_text.delta"
        delta4.delta = " Option A has benefits"
        
        processor._handle_reasoning_summary_text_delta(delta4)
        
        # 5. Parts complete
        part1_done = Mock()
        part1_done.type = "response.reasoning_summary_part.done"
        part1_done.part_id = "part_1"
        
        part2_done = Mock()
        part2_done.type = "response.reasoning_summary_part.done"
        part2_done.part_id = "part_2"
        
        processor._handle_reasoning_summary_part_done(part1_done)
        processor._handle_reasoning_summary_part_done(part2_done)
        
        # Collect all events
        events = []
        while not event_queue.empty():
            events.append(json.loads(event_queue.get()))
        
        # Analyze the event flow
        event_types = [e["type"] for e in events]
        
        # Should have:
        # 1. reasoning_started (from first part)
        # 2. reasoning_in_progress (from text deltas - 4 times)
        # 3. reasoning_in_progress (from second part)
        # 4. reasoning_completed (from part1 done)
        # 5. reasoning_completed (from part2 done)
        
        started_count = event_types.count("reasoning_started")
        in_progress_count = event_types.count("reasoning_in_progress")
        completed_count = event_types.count("reasoning_completed")
        
        assert started_count == 1, f"Expected 1 reasoning_started, got {started_count}"
        assert in_progress_count >= 4, f"Expected at least 4 reasoning_in_progress (4 deltas + 1 part), got {in_progress_count}"
        assert completed_count == 2, f"Expected 2 reasoning_completed (2 parts), got {completed_count}"
        
        # Verify the first event is reasoning_started
        assert events[0]["type"] == "reasoning_started"
        assert events[0]["part_id"] == "part_1"
        
        # Verify we have in-progress events from text deltas
        delta_in_progress_events = [e for e in events if e["type"] == "reasoning_in_progress" and e.get("status") == "thinking"]
        assert len(delta_in_progress_events) >= 4, f"Expected at least 4 delta-triggered in-progress events, got {len(delta_in_progress_events)}"

    def test_reasoning_in_progress_provides_continuous_feedback(self):
        """Test that reasoning in-progress events provide continuous feedback during text generation."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Simulate continuous text generation (like what happens during real reasoning)
        for i in range(10):
            delta_event = Mock()
            delta_event.type = "response.reasoning_summary_text.delta"
            delta_event.delta = f"reasoning step {i}"
            
            processor._handle_reasoning_summary_text_delta(delta_event)
        
        # Collect events
        events = []
        while not event_queue.empty():
            events.append(json.loads(event_queue.get()))
        
        # Should have 10 in-progress events
        assert len(events) == 10, f"Expected 10 reasoning_in_progress events, got {len(events)}"
        
        # All should be in-progress with thinking status
        for event in events:
            assert event["type"] == "reasoning_in_progress"
            assert event["status"] == "thinking"
        
        # Verify reasoning data was accumulated
        assert len(processor.reasoning_data["complete_summary"]) > 0
        assert "reasoning step" in processor.reasoning_data["complete_summary"]