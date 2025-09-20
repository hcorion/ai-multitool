"""Integration tests for web search event processing with conversation storage."""

import json
import time
from queue import Queue
from unittest.mock import Mock

import pytest

from app import StreamEventProcessor, ConversationManager


class TestWebSearchIntegration:
    """Test web search integration with conversation storage."""

    def test_web_search_data_storage_in_conversation(self, tmp_path):
        """Test that web search data is properly stored in conversation."""
        # Set up conversation manager with temp directory
        conv_manager = ConversationManager(str(tmp_path))
        
        # Create a conversation
        username = "testuser"
        conv_id = conv_manager.create_conversation(username, "Test Chat")
        
        # Set up stream processor
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Simulate web search events and output items
        processor.current_response_id = "resp_test123"
        
        # Add web search event
        processor.web_search_events["ws_test123"] = {
            "item_id": "ws_test123",
            "status": "completed",
            "output_index": 1,
            "sequence_number": 100,
            "timestamp": int(time.time()),
        }
        
        # Add web search output item
        processor.web_search_output_items["ws_test123"] = {
            "item_id": "ws_test123",
            "status": "completed",
            "query": "test search query",
            "action_type": "search",
            "timestamp": int(time.time()),
        }
        
        # Add message output item
        processor.message_output_items["msg_test123"] = {
            "item_id": "msg_test123",
            "role": "assistant",
            "status": "completed",
            "content_items": [{"type": "output_text", "text": "Test response"}],
            "annotations": [],
            "timestamp": int(time.time()),
        }
        
        # Correlate data
        processor._correlate_web_search_data()
        processor.reasoning_data["message_data"] = processor.message_output_items["msg_test123"]
        
        # Get reasoning data
        reasoning_data = processor.get_reasoning_data()
        
        # Add message to conversation with reasoning data
        conv_manager.add_message(
            username, 
            conv_id, 
            "assistant", 
            "Test response with web search",
            response_id="resp_test123",
            reasoning_data=reasoning_data
        )
        
        # Verify the data was stored correctly
        retrieved_reasoning = conv_manager.get_message_reasoning_data(username, conv_id, 0)
        
        assert retrieved_reasoning is not None
        assert "web_searches" in retrieved_reasoning
        assert len(retrieved_reasoning["web_searches"]) == 1
        
        web_search = retrieved_reasoning["web_searches"][0]
        assert web_search["item_id"] == "ws_test123"
        assert web_search["query"] == "test search query"
        assert web_search["status"] == "completed"
        assert web_search["action_type"] == "search"
        
        assert "message_data" in retrieved_reasoning
        message_data = retrieved_reasoning["message_data"]
        assert message_data["item_id"] == "msg_test123"
        assert message_data["role"] == "assistant"

    def test_web_search_backward_compatibility(self, tmp_path):
        """Test that conversations without web search data still work."""
        # Set up conversation manager with temp directory
        conv_manager = ConversationManager(str(tmp_path))
        
        # Create a conversation
        username = "testuser"
        conv_id = conv_manager.create_conversation(username, "Test Chat")
        
        # Add message with old-style reasoning data (no web searches)
        old_reasoning_data = {
            "summary_parts": ["Test reasoning"],
            "complete_summary": "Complete test reasoning",
            "timestamp": int(time.time()),
            "response_id": "resp_old123",
        }
        
        conv_manager.add_message(
            username, 
            conv_id, 
            "assistant", 
            "Test response without web search",
            response_id="resp_old123",
            reasoning_data=old_reasoning_data
        )
        
        # Verify the data can still be retrieved
        retrieved_reasoning = conv_manager.get_message_reasoning_data(username, conv_id, 0)
        
        assert retrieved_reasoning is not None
        assert retrieved_reasoning["complete_summary"] == "Complete test reasoning"
        assert len(retrieved_reasoning["summary_parts"]) == 1
        
        # Web search fields should not be present in old data
        assert "web_searches" not in retrieved_reasoning
        assert "message_data" not in retrieved_reasoning

    def test_web_search_validation_with_invalid_data(self, tmp_path):
        """Test validation handles invalid web search data gracefully."""
        # Set up conversation manager with temp directory
        conv_manager = ConversationManager(str(tmp_path))
        
        # Create a conversation
        username = "testuser"
        conv_id = conv_manager.create_conversation(username, "Test Chat")
        
        # Try to add message with invalid web search data
        invalid_reasoning_data = {
            "summary_parts": ["Test reasoning"],
            "complete_summary": "Complete test reasoning",
            "timestamp": int(time.time()),
            "response_id": "resp_invalid123",
            "web_searches": "invalid_not_a_list",  # Should be a list
            "message_data": "invalid_not_a_dict",  # Should be a dict or None
        }
        
        # This should raise a validation error
        with pytest.raises(ValueError, match="web_searches must be a list"):
            conv_manager.add_message(
                username, 
                conv_id, 
                "assistant", 
                "Test response with invalid data",
                response_id="resp_invalid123",
                reasoning_data=invalid_reasoning_data
            )

    def test_web_search_status_events_generation(self):
        """Test that web search events generate proper status events for frontend."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock web search events
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
        
        # Verify correct status events were generated
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
        assert status_events[1]["sequence_number"] == 101
        
        # Check search_completed event
        assert status_events[2]["type"] == "search_completed"
        assert status_events[2]["item_id"] == "ws_test123"
        assert status_events[2]["sequence_number"] == 102

    def test_multiple_web_searches_correlation(self):
        """Test correlation of multiple web searches in a single response."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Add multiple web search events
        processor.web_search_events["ws_search1"] = {
            "item_id": "ws_search1",
            "status": "completed",
            "output_index": 1,
            "sequence_number": 100,
            "timestamp": int(time.time()),
        }
        
        processor.web_search_events["ws_search2"] = {
            "item_id": "ws_search2",
            "status": "completed",
            "output_index": 2,
            "sequence_number": 200,
            "timestamp": int(time.time()),
        }
        
        # Add corresponding output items
        processor.web_search_output_items["ws_search1"] = {
            "item_id": "ws_search1",
            "status": "completed",
            "query": "first search query",
            "action_type": "search",
            "timestamp": int(time.time()),
        }
        
        processor.web_search_output_items["ws_search2"] = {
            "item_id": "ws_search2",
            "status": "completed",
            "query": "second search query",
            "action_type": "search",
            "timestamp": int(time.time()),
        }
        
        # Correlate data
        processor._correlate_web_search_data()
        
        # Verify both searches were correlated
        web_searches = processor.reasoning_data["web_searches"]
        assert len(web_searches) == 2
        
        # Find searches by query to verify both are present
        queries = [search["query"] for search in web_searches]
        assert "first search query" in queries
        assert "second search query" in queries
        
        # Verify each search has proper correlation data
        for search in web_searches:
            assert "item_id" in search
            assert "output_index" in search
            assert "sequence_number" in search
            assert search["status"] == "completed"
            assert search["action_type"] == "search"