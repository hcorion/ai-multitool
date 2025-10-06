"""Test API endpoint with web search events only."""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, conversation_manager


class TestAPIWithEventsOnly:
    """Test API endpoint with web search events only (no output items)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_session(self):
        """Mock session with authenticated user."""
        with patch('app.session', {'username': 'testuser'}):
            yield

    def test_reasoning_endpoint_with_events_only_web_search(self, client, mock_session):
        """Test reasoning endpoint with web search events but no output items."""
        # Mock conversation data with web search events only (like current data)
        mock_reasoning_data = {
            "summary_parts": [
                "User asked about current events",
                "I need to search for recent information",
                "Found relevant information from web sources"
            ],
            "complete_summary": "The user asked about current events. I performed web searches to find the most recent information and provided an updated response.",
            "timestamp": 1758355000,
            "response_id": "resp_events_only_123",
            "web_searches": [
                {
                    "item_id": "ws_68ce5e30b3a481959356e2bfcca1b38f05c61180e42bbe72",
                    "status": "completed",
                    "output_index": 1,
                    "sequence_number": 318,
                    "timestamp": 1758355001,
                    "query": "Web search performed (sequence 318)",
                    "action_type": "search"
                }
            ]
        }

        mock_conversation = [
            {"role": "user", "text": "What are the latest developments in AI?"},
            {
                "role": "assistant", 
                "text": "Based on recent web searches, here are the latest AI developments...",
                "reasoning_data": mock_reasoning_data
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Based on recent web searches, here are the latest AI developments...', response_id='resp_events_only_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            # Test API endpoint
            response = client.get('/chat/reasoning/events_only_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify complete API response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'events_only_conv'
            assert data['message_index'] == 1
            assert data['message_role'] == 'assistant'
            
            # Verify reasoning data
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == mock_reasoning_data['complete_summary']
            assert len(reasoning['summary_parts']) == 3
            assert reasoning['response_id'] == 'resp_events_only_123'
            
            # Verify web search data is included
            assert 'web_searches' in data
            web_searches = data['web_searches']
            assert len(web_searches) == 1
            
            # Verify search data (events only)
            search = web_searches[0]
            assert search['item_id'] == "ws_68ce5e30b3a481959356e2bfcca1b38f05c61180e42bbe72"
            assert search['status'] == "completed"
            assert search['output_index'] == 1
            assert search['sequence_number'] == 318
            assert search['query'] == "Web search performed (sequence 318)"
            assert search['action_type'] == "search"
            # Should not have sources since we only have events
            assert 'sources' not in search

    def test_reasoning_endpoint_with_multiple_events_only(self, client, mock_session):
        """Test reasoning endpoint with multiple web search events."""
        mock_reasoning_data = {
            "summary_parts": ["Processing complex query with multiple searches"],
            "complete_summary": "I performed several web searches to gather comprehensive information.",
            "timestamp": 1758355000,
            "response_id": "resp_multiple_events_123",
            "web_searches": [
                {
                    "item_id": "ws_search_1",
                    "status": "completed",
                    "output_index": 0,
                    "sequence_number": 100,
                    "timestamp": 1758355001,
                    "query": "Web search performed (sequence 100)",
                    "action_type": "search"
                },
                {
                    "item_id": "ws_search_2",
                    "status": "completed",
                    "output_index": 1,
                    "sequence_number": 200,
                    "timestamp": 1758355002,
                    "query": "Web search performed (sequence 200)",
                    "action_type": "search"
                },
                {
                    "item_id": "ws_search_3",
                    "status": "in_progress",
                    "output_index": 2,
                    "sequence_number": 300,
                    "timestamp": 1758355003,
                    "query": "Web search performed (sequence 300)",
                    "action_type": "search"
                }
            ]
        }

        mock_conversation = [
            {"role": "user", "text": "Complex query requiring multiple searches"},
            {
                "role": "assistant", 
                "text": "Here's the information I found through multiple searches.",
                "reasoning_data": mock_reasoning_data
            }
        ]
        
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Here\'s the information I found through multiple searches.', response_id='resp_multiple_events_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            response = client.get('/chat/reasoning/multiple_events_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify web search data with different statuses
            web_searches = data['web_searches']
            assert len(web_searches) == 3
            
            # Check that all searches have placeholder queries with sequence numbers
            for i, search in enumerate(web_searches):
                expected_sequence = (i + 1) * 100
                assert search['query'] == f"Web search performed (sequence {expected_sequence})"
                assert search['action_type'] == "search"
                assert search['sequence_number'] == expected_sequence
                
            # Check different statuses
            assert web_searches[0]['status'] == 'completed'
            assert web_searches[1]['status'] == 'completed'
            assert web_searches[2]['status'] == 'in_progress'