"""Test web search data consolidation in StreamEventProcessor."""

import pytest
import time
from unittest.mock import MagicMock
from queue import Queue
from app import StreamEventProcessor


class TestWebSearchDataConsolidation:
    """Test web search data consolidation functionality."""

    @pytest.fixture
    def event_processor(self):
        """Create a StreamEventProcessor for testing."""
        event_queue = Queue()
        return StreamEventProcessor(event_queue)

    def test_web_search_event_processing(self, event_processor):
        """Test that web search events are properly processed and stored."""
        # Create mock web search events
        in_progress_event = MagicMock()
        in_progress_event.type = "response.web_search_call.in_progress"
        in_progress_event.item_id = "ws_test_123"
        in_progress_event.output_index = 0
        in_progress_event.sequence_number = 1

        searching_event = MagicMock()
        searching_event.type = "response.web_search_call.searching"
        searching_event.item_id = "ws_test_123"
        searching_event.output_index = 0
        searching_event.sequence_number = 2

        completed_event = MagicMock()
        completed_event.type = "response.web_search_call.completed"
        completed_event.item_id = "ws_test_123"
        completed_event.output_index = 0
        completed_event.sequence_number = 3

        # Process the events
        event_processor._handle_web_search_call_in_progress(in_progress_event)
        event_processor._handle_web_search_call_searching(searching_event)
        event_processor._handle_web_search_call_completed(completed_event)

        # Check that events were stored
        assert "ws_test_123" in event_processor.web_search_events
        event_data = event_processor.web_search_events["ws_test_123"]
        assert event_data["status"] == "completed"
        assert event_data["item_id"] == "ws_test_123"

    def test_web_search_output_item_processing(self, event_processor):
        """Test that web search output items are properly processed."""
        # Create mock web search output item
        output_item = MagicMock()
        output_item.id = "ws_test_456"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock action
        action = MagicMock()
        action.type = "search"
        action.query = "test search query"
        action.sources = ["example.com", "test.org"]
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored
        assert "ws_test_456" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_test_456"]
        assert output_data["query"] == "test search query"
        assert output_data["action_type"] == "search"
        assert output_data["sources"] == ["example.com", "test.org"]

    def test_web_search_data_correlation(self, event_processor):
        """Test that web search events and output items are properly correlated."""
        # Add web search event
        event_processor.web_search_events["ws_test_789"] = {
            "item_id": "ws_test_789",
            "status": "completed",
            "output_index": 0,
            "sequence_number": 1,
            "timestamp": int(time.time()),
        }

        # Add web search output item
        event_processor.web_search_output_items["ws_test_789"] = {
            "item_id": "ws_test_789",
            "status": "completed",
            "query": "correlation test query",
            "action_type": "search",
            "sources": ["correlation.com"],
            "timestamp": int(time.time()),
            "is_done": True,
        }

        # Correlate the data
        event_processor._correlate_web_search_data()

        # Check that data was correlated and stored in reasoning data
        web_searches = event_processor.reasoning_data.get("web_searches", [])
        assert len(web_searches) == 1
        
        search_data = web_searches[0]
        assert search_data["item_id"] == "ws_test_789"
        assert search_data["query"] == "correlation test query"
        assert search_data["status"] == "completed"
        assert search_data["action_type"] == "search"
        assert search_data["sources"] == ["correlation.com"]

    def test_get_reasoning_data_includes_web_searches(self, event_processor):
        """Test that get_reasoning_data includes web search data."""
        # Add some reasoning data
        event_processor.reasoning_data["complete_summary"] = "Test reasoning summary"
        
        # Add web search data
        event_processor.web_search_output_items["ws_final_test"] = {
            "item_id": "ws_final_test",
            "status": "completed",
            "query": "final test query",
            "action_type": "search",
            "sources": ["final.com"],
            "timestamp": int(time.time()),
            "is_done": True,
        }

        # Get reasoning data
        reasoning_data = event_processor.get_reasoning_data()

        # Check that web search data is included
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 1
        
        search_data = reasoning_data["web_searches"][0]
        assert search_data["query"] == "final test query"
        assert search_data["status"] == "completed"

    def test_web_search_data_without_reasoning(self, event_processor):
        """Test that web search data alone is sufficient to return reasoning data."""
        # Add only web search data (no reasoning summary)
        event_processor.web_search_output_items["ws_only_test"] = {
            "item_id": "ws_only_test",
            "status": "completed",
            "query": "standalone search query",
            "action_type": "search",
            "sources": ["standalone.com"],
            "timestamp": int(time.time()),
            "is_done": True,
        }

        # Get reasoning data
        reasoning_data = event_processor.get_reasoning_data()

        # Check that reasoning data is returned even without summary
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 1
        
        search_data = reasoning_data["web_searches"][0]
        assert search_data["query"] == "standalone search query"