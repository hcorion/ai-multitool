"""Test web search data extraction from OpenAI response structures."""

import pytest
from unittest.mock import MagicMock
from queue import Queue
from app import StreamEventProcessor


class TestWebSearchDataExtraction:
    """Test web search data extraction functionality."""

    @pytest.fixture
    def event_processor(self):
        """Create a StreamEventProcessor for testing."""
        event_queue = Queue()
        return StreamEventProcessor(event_queue)

    def test_web_search_output_item_with_search_action(self, event_processor):
        """Test processing web search output item with search action."""
        # Create mock web search output item matching OpenAI structure
        output_item = MagicMock()
        output_item.id = "ws_search_test_123"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock search action
        action = MagicMock()
        action.type = "search"
        action.query = "current weather in New York"
        
        # Create mock sources (ActionSearchSource objects)
        source1 = MagicMock()
        source1.type = "url"
        source1.url = "https://weather.com/weather/today/l/New+York+NY"
        
        source2 = MagicMock()
        source2.type = "url"
        source2.url = "https://www.noaa.gov/weather"
        
        action.sources = [source1, source2]
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored with correct data
        assert "ws_search_test_123" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_search_test_123"]
        
        assert output_data["query"] == "current weather in New York"
        assert output_data["action_type"] == "search"
        assert output_data["status"] == "completed"
        assert len(output_data["sources"]) == 2
        assert "weather.com" in output_data["sources"][0]
        assert "noaa.gov" in output_data["sources"][1]

    def test_web_search_output_item_with_open_page_action(self, event_processor):
        """Test processing web search output item with open_page action."""
        # Create mock web search output item
        output_item = MagicMock()
        output_item.id = "ws_open_test_456"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock open_page action
        action = MagicMock()
        action.type = "open_page"
        action.url = "https://example.com/specific-page"
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored with correct data
        assert "ws_open_test_456" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_open_test_456"]
        
        assert output_data["action_type"] == "open_page"
        assert output_data["url"] == "https://example.com/specific-page"
        assert output_data["status"] == "completed"

    def test_web_search_output_item_with_find_action(self, event_processor):
        """Test processing web search output item with find action."""
        # Create mock web search output item
        output_item = MagicMock()
        output_item.id = "ws_find_test_789"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock find action
        action = MagicMock()
        action.type = "find"
        action.pattern = "temperature"
        action.url = "https://weather.com/current-conditions"
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored with correct data
        assert "ws_find_test_789" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_find_test_789"]
        
        assert output_data["action_type"] == "find"
        assert output_data["pattern"] == "temperature"
        assert output_data["url"] == "https://weather.com/current-conditions"
        assert output_data["status"] == "completed"

    def test_web_search_output_item_with_dict_sources(self, event_processor):
        """Test processing web search output item with dictionary sources."""
        # Create mock web search output item
        output_item = MagicMock()
        output_item.id = "ws_dict_test_101"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock search action with dict sources
        action = MagicMock()
        action.type = "search"
        action.query = "Python programming tutorial"
        action.sources = [
            {"type": "url", "url": "https://python.org/tutorial"},
            {"type": "url", "url": "https://docs.python.org/3/"}
        ]
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored with correct data
        assert "ws_dict_test_101" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_dict_test_101"]
        
        assert output_data["query"] == "Python programming tutorial"
        assert output_data["action_type"] == "search"
        assert len(output_data["sources"]) == 2
        assert "python.org" in output_data["sources"][0]
        assert "docs.python.org" in output_data["sources"][1]

    def test_web_search_output_item_with_string_sources(self, event_processor):
        """Test processing web search output item with string sources."""
        # Create mock web search output item
        output_item = MagicMock()
        output_item.id = "ws_string_test_202"
        output_item.status = "completed"
        output_item.type = "web_search_call"

        # Create mock search action with string sources
        action = MagicMock()
        action.type = "search"
        action.query = "machine learning basics"
        action.sources = [
            "https://scikit-learn.org/stable/",
            "https://tensorflow.org/tutorials"
        ]
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Check that output item was stored with correct data
        assert "ws_string_test_202" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_string_test_202"]
        
        assert output_data["query"] == "machine learning basics"
        assert output_data["action_type"] == "search"
        assert len(output_data["sources"]) == 2
        assert "scikit-learn.org" in output_data["sources"][0]
        assert "tensorflow.org" in output_data["sources"][1]

    def test_web_search_output_item_without_action(self, event_processor):
        """Test processing web search output item without action data."""
        # Create mock web search output item without action
        output_item = MagicMock()
        output_item.id = "ws_no_action_303"
        output_item.status = "in_progress"
        output_item.type = "web_search_call"
        output_item.action = None

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=False)

        # Check that output item was stored with basic data
        assert "ws_no_action_303" in event_processor.web_search_output_items
        output_data = event_processor.web_search_output_items["ws_no_action_303"]
        
        assert output_data["status"] == "in_progress"
        assert output_data["is_done"] == False
        assert "query" not in output_data
        assert "action_type" not in output_data

    def test_complete_web_search_flow_with_correlation(self, event_processor):
        """Test complete web search flow with event correlation."""
        item_id = "ws_complete_test_404"
        
        # Add web search event
        event_processor.web_search_events[item_id] = {
            "item_id": item_id,
            "status": "completed",
            "output_index": 0,
            "sequence_number": 1,
            "timestamp": 1704067200,
        }

        # Create and process web search output item
        output_item = MagicMock()
        output_item.id = item_id
        output_item.status = "completed"
        output_item.type = "web_search_call"

        action = MagicMock()
        action.type = "search"
        action.query = "complete flow test query"
        
        source = MagicMock()
        source.type = "url"
        source.url = "https://example.com/complete-test"
        action.sources = [source]
        
        output_item.action = action

        # Process the output item
        event_processor._process_web_search_output_item(output_item, is_done=True)

        # Get reasoning data to trigger correlation
        reasoning_data = event_processor.get_reasoning_data()

        # Check that web search data was correlated correctly
        assert reasoning_data is not None
        assert "web_searches" in reasoning_data
        assert len(reasoning_data["web_searches"]) == 1
        
        search_data = reasoning_data["web_searches"][0]
        assert search_data["item_id"] == item_id
        assert search_data["query"] == "complete flow test query"
        assert search_data["status"] == "completed"
        assert search_data["action_type"] == "search"
        assert len(search_data["sources"]) == 1
        assert "example.com" in search_data["sources"][0]
        assert search_data["output_index"] == 0
        assert search_data["sequence_number"] == 1