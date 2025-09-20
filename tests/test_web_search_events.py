"""Tests for web search event processing in StreamEventProcessor."""

import json
import time
from queue import Queue
from unittest.mock import Mock

import pytest

from app import StreamEventProcessor


class TestWebSearchEventProcessing:
    """Test web search event processing functionality."""

    def test_web_search_in_progress_event(self):
        """Test handling of response.web_search_call.in_progress event."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock event
        mock_event = Mock()
        mock_event.type = "response.web_search_call.in_progress"
        mock_event.item_id = "ws_test123"
        mock_event.output_index = 1
        mock_event.sequence_number = 100
        
        # Process the event
        processor._handle_web_search_call_in_progress(mock_event)
        
        # Verify event data was stored
        assert "ws_test123" in processor.web_search_events
        event_data = processor.web_search_events["ws_test123"]
        assert event_data["item_id"] == "ws_test123"
        assert event_data["status"] == "in_progress"
        assert event_data["output_index"] == 1
        assert event_data["sequence_number"] == 100
        assert "timestamp" in event_data
        
        # Verify frontend status event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "search_started"
        assert status_event["item_id"] == "ws_test123"
        assert status_event["output_index"] == 1
        assert status_event["sequence_number"] == 100

    def test_web_search_searching_event(self):
        """Test handling of response.web_search_call.searching event."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock event
        mock_event = Mock()
        mock_event.type = "response.web_search_call.searching"
        mock_event.item_id = "ws_test123"
        mock_event.output_index = 1
        mock_event.sequence_number = 101
        
        # Process the event
        processor._handle_web_search_call_searching(mock_event)
        
        # Verify event data was stored
        assert "ws_test123" in processor.web_search_events
        event_data = processor.web_search_events["ws_test123"]
        assert event_data["status"] == "searching"
        assert event_data["sequence_number"] == 101
        
        # Verify frontend status event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "search_in_progress"
        assert status_event["status"] == "searching"

    def test_web_search_completed_event(self):
        """Test handling of response.web_search_call.completed event."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock event
        mock_event = Mock()
        mock_event.type = "response.web_search_call.completed"
        mock_event.item_id = "ws_test123"
        mock_event.output_index = 1
        mock_event.sequence_number = 102
        
        # Process the event
        processor._handle_web_search_call_completed(mock_event)
        
        # Verify event data was stored
        assert "ws_test123" in processor.web_search_events
        event_data = processor.web_search_events["ws_test123"]
        assert event_data["status"] == "completed"
        assert event_data["sequence_number"] == 102
        
        # Verify frontend status event was sent
        assert not event_queue.empty()
        status_event = json.loads(event_queue.get())
        assert status_event["type"] == "search_completed"

    def test_web_search_output_item_processing(self):
        """Test processing of web search output items."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock web search output item
        mock_action = Mock()
        mock_action.type = "search"
        mock_action.query = "test query"
        mock_action.sources = None
        
        mock_output_item = Mock()
        mock_output_item.id = "ws_test123"
        mock_output_item.type = "web_search_call"
        mock_output_item.status = "completed"
        mock_output_item.action = mock_action
        
        # Process the output item
        processor._process_web_search_output_item(mock_output_item, is_done=True)
        
        # Verify output item data was stored
        assert "ws_test123" in processor.web_search_output_items
        item_data = processor.web_search_output_items["ws_test123"]
        assert item_data["item_id"] == "ws_test123"
        assert item_data["status"] == "completed"
        assert item_data["action_type"] == "search"
        assert item_data["query"] == "test query"
        assert item_data["is_done"] is True

    def test_message_output_item_processing(self):
        """Test processing of message output items."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock content item
        mock_content_item = Mock()
        mock_content_item.type = "output_text"
        mock_content_item.text = "Test response text"
        mock_content_item.annotations = []
        
        # Create mock message output item
        mock_output_item = Mock()
        mock_output_item.id = "msg_test123"
        mock_output_item.type = "message"
        mock_output_item.role = "assistant"
        mock_output_item.status = "completed"
        mock_output_item.content = [mock_content_item]
        
        # Process the output item
        processor._process_message_output_item(mock_output_item, is_done=True)
        
        # Verify message data was stored
        assert "msg_test123" in processor.message_output_items
        message_data = processor.message_output_items["msg_test123"]
        assert message_data["item_id"] == "msg_test123"
        assert message_data["role"] == "assistant"
        assert message_data["status"] == "completed"
        assert len(message_data["content_items"]) == 1
        assert message_data["content_items"][0]["text"] == "Test response text"
        
        # Verify message data was stored in reasoning data
        assert processor.reasoning_data["message_data"] == message_data

    def test_web_search_correlation(self):
        """Test correlation of web search events with output items."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Add web search event data
        processor.web_search_events["ws_test123"] = {
            "item_id": "ws_test123",
            "status": "in_progress",
            "output_index": 1,
            "sequence_number": 100,
            "timestamp": int(time.time()),
        }
        
        # Add web search output item data
        processor.web_search_output_items["ws_test123"] = {
            "item_id": "ws_test123",
            "status": "completed",
            "query": "test query",
            "action_type": "search",
            "timestamp": int(time.time()),
        }
        
        # Correlate the data
        processor._correlate_web_search_data()
        
        # Verify correlated data was stored in reasoning data
        web_searches = processor.reasoning_data["web_searches"]
        assert len(web_searches) == 1
        
        search_data = web_searches[0]
        assert search_data["item_id"] == "ws_test123"
        assert search_data["status"] == "completed"  # Should use output item status
        assert search_data["output_index"] == 1
        assert search_data["sequence_number"] == 100
        assert search_data["query"] == "test query"
        assert search_data["action_type"] == "search"

    def test_output_item_added_event_handling(self):
        """Test handling of response.output_item.added events."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock web search output item
        mock_output_item = Mock()
        mock_output_item.type = "web_search_call"
        mock_output_item.id = "ws_test123"
        mock_output_item.status = "in_progress"
        mock_output_item.action = None
        
        # Create mock event
        mock_event = Mock()
        mock_event.type = "response.output_item.added"
        mock_event.output_item = mock_output_item
        
        # Process the event
        processor._handle_output_item_added(mock_event)
        
        # Verify output item was processed
        assert "ws_test123" in processor.web_search_output_items

    def test_output_item_done_event_handling(self):
        """Test handling of response.output_item.done events."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create mock message output item
        mock_content_item = Mock()
        mock_content_item.type = "output_text"
        mock_content_item.text = "Test message"
        mock_content_item.annotations = []
        
        mock_output_item = Mock()
        mock_output_item.type = "message"
        mock_output_item.id = "msg_test123"
        mock_output_item.role = "assistant"
        mock_output_item.status = "completed"
        mock_output_item.content = [mock_content_item]
        
        # Create mock event
        mock_event = Mock()
        mock_event.type = "response.output_item.done"
        mock_event.output_item = mock_output_item
        
        # Process the event
        processor._handle_output_item_done(mock_event)
        
        # Verify output item was processed
        assert "msg_test123" in processor.message_output_items
        assert processor.reasoning_data["message_data"] is not None

    def test_enhanced_reasoning_data_retrieval(self):
        """Test that reasoning data includes web search and message data."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Set up reasoning data with web searches
        processor.reasoning_data = {
            "summary_parts": ["Test reasoning"],
            "complete_summary": "Complete test reasoning",
            "timestamp": int(time.time()),
            "response_id": "resp_test123",
            "web_searches": [{
                "item_id": "ws_test123",
                "status": "completed",
                "query": "test query",
                "action_type": "search",
            }],
            "message_data": {
                "item_id": "msg_test123",
                "role": "assistant",
                "status": "completed",
                "content_items": [{"type": "output_text", "text": "Test response"}],
            }
        }
        
        # Get reasoning data
        reasoning_data = processor.get_reasoning_data()
        
        # Verify all data is included
        assert reasoning_data is not None
        assert len(reasoning_data["web_searches"]) == 1
        assert reasoning_data["web_searches"][0]["query"] == "test query"
        assert reasoning_data["message_data"]["role"] == "assistant"

    def test_error_handling_in_web_search_processing(self):
        """Test error handling in web search event processing."""
        event_queue = Queue()
        processor = StreamEventProcessor(event_queue)
        
        # Create malformed event (missing attributes)
        mock_event = Mock()
        mock_event.type = "response.web_search_call.in_progress"
        # Simulate missing attributes by setting them to None
        mock_event.item_id = None
        mock_event.output_index = None
        mock_event.sequence_number = None
        
        # Process should not raise exception
        processor._handle_web_search_call_in_progress(mock_event)
        
        # Should continue processing without storing invalid data
        assert len(processor.web_search_events) == 0

    def test_web_search_event_stream_integration(self):
        """Test web search events are handled in the main stream event handler."""
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
        
        # Process events through main handler
        processor._handle_stream_event(in_progress_event)
        processor._handle_stream_event(searching_event)
        processor._handle_stream_event(completed_event)
        
        # Verify events were processed
        assert "ws_test123" in processor.web_search_events
        assert processor.web_search_events["ws_test123"]["status"] == "completed"
        
        # Verify status events were sent to frontend
        status_events = []
        while not event_queue.empty():
            status_events.append(json.loads(event_queue.get()))
        
        assert len(status_events) == 3
        assert status_events[0]["type"] == "search_started"
        assert status_events[1]["type"] == "search_in_progress"
        assert status_events[2]["type"] == "search_completed"