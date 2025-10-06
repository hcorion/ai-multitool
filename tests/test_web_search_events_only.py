"""Test web search processing with events only (no output items)."""

import pytest
import time
from unittest.mock import MagicMock
from queue import Queue
from app import StreamEventProcessor


class TestWebSearchEventsOnly:
    """Test web search processing when only events are available."""

    @pytest.fixture
    def event_processor(self):
        """Create a StreamEventProcessor for testing."""
        event_queue = Queue()
        return StreamEventProcessor(event_queue)

    def test_web_search_events_only_correlation(self, event_processor):
        """Test that web search events without output items still produce search data."""
        # Simulate the current situation: web search events but no output items
        item_id = "ws_68ce5e30b3a481959356e2bfcca1b38f05c61180e42bbe72"
        
        # Add web search event (like what we see in the actual data)
        event_processor.web_search_events[item_id] = {
            "item_id": item_id,
            "status": "completed",
            "output_index": 1,
            "sequence_number": 318,
            "timestamp": 1758355001,
        }

        # No output items are added (simulating the current issue)
        assert len(event_processor.web_search_output_items) == 0

        # Get reasoning data to trigger correlation
        reasoning_data = event_processor.get_reasoning_data()

        # Check that web search data was created from events only
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 1
        
        search_data = reasoning_data["web_searches"][0]
        assert search_data["item_id"] == item_id
        assert search_data["status"] == "completed"
        assert search_data["output_index"] == 1
        assert search_data["sequence_number"] == 318
        assert search_data["timestamp"] == 1758355001
        
        # Check that placeholder query information was added
        assert "query" in search_data
        assert "Web search" in search_data["query"]
        assert search_data["action_type"] == "search"

    def test_multiple_web_search_events_only(self, event_processor):
        """Test multiple web search events without output items."""
        # Add multiple web search events
        events_data = [
            {
                "item_id": "ws_test_001",
                "status": "completed",
                "output_index": 0,
                "sequence_number": 100,
                "timestamp": 1758355000,
            },
            {
                "item_id": "ws_test_002",
                "status": "in_progress",
                "output_index": 1,
                "sequence_number": 200,
                "timestamp": 1758355001,
            },
            {
                "item_id": "ws_test_003",
                "status": "searching",
                "output_index": 2,
                "sequence_number": 300,
                "timestamp": 1758355002,
            },
        ]

        for event_data in events_data:
            event_processor.web_search_events[event_data["item_id"]] = event_data

        # Get reasoning data
        reasoning_data = event_processor.get_reasoning_data()

        # Check that all events were converted to search data
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 3
        
        # Check each search entry
        for i, search_data in enumerate(reasoning_data["web_searches"]):
            expected = events_data[i]
            assert search_data["item_id"] == expected["item_id"]
            assert search_data["status"] == expected["status"]
            assert search_data["output_index"] == expected["output_index"]
            assert search_data["sequence_number"] == expected["sequence_number"]
            assert search_data["timestamp"] == expected["timestamp"]
            assert "query" in search_data
            assert search_data["action_type"] == "search"

    def test_mixed_events_and_output_items(self, event_processor):
        """Test correlation when some items have output items and others don't."""
        # Add web search event with output item
        item_id_with_output = "ws_with_output"
        event_processor.web_search_events[item_id_with_output] = {
            "item_id": item_id_with_output,
            "status": "completed",
            "output_index": 0,
            "sequence_number": 100,
            "timestamp": 1758355000,
        }
        
        event_processor.web_search_output_items[item_id_with_output] = {
            "item_id": item_id_with_output,
            "status": "completed",
            "query": "actual search query",
            "action_type": "search",
            "sources": ["example.com"],
            "timestamp": 1758355000,
            "is_done": True,
        }

        # Add web search event without output item
        item_id_without_output = "ws_without_output"
        event_processor.web_search_events[item_id_without_output] = {
            "item_id": item_id_without_output,
            "status": "completed",
            "output_index": 1,
            "sequence_number": 200,
            "timestamp": 1758355001,
        }

        # Get reasoning data
        reasoning_data = event_processor.get_reasoning_data()

        # Check that both items are included
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 2
        
        # Find the items by ID
        with_output = next(s for s in reasoning_data["web_searches"] if s["item_id"] == item_id_with_output)
        without_output = next(s for s in reasoning_data["web_searches"] if s["item_id"] == item_id_without_output)
        
        # Check item with output data
        assert with_output["query"] == "actual search query"
        assert with_output["sources"] == ["example.com"]
        assert with_output["action_type"] == "search"
        
        # Check item without output data (should have placeholder)
        assert "Web search" in without_output["query"]
        assert without_output["action_type"] == "search"
        assert "sources" not in without_output

    def test_reasoning_data_with_events_only_and_summary(self, event_processor):
        """Test that reasoning data includes both summary and web search events."""
        # Add reasoning summary
        event_processor.reasoning_data["complete_summary"] = "I performed a web search to find information."
        
        # Add web search event
        item_id = "ws_with_summary"
        event_processor.web_search_events[item_id] = {
            "item_id": item_id,
            "status": "completed",
            "output_index": 0,
            "sequence_number": 100,
            "timestamp": 1758355000,
        }

        # Get reasoning data
        reasoning_data = event_processor.get_reasoning_data()

        # Check that both summary and web search data are included
        assert reasoning_data is not None
        assert reasoning_data["complete_summary"] == "I performed a web search to find information."
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 1
        
        search_data = reasoning_data["web_searches"][0]
        assert search_data["item_id"] == item_id
        assert search_data["status"] == "completed"