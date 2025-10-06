"""Test reasoning modal with actual web search data."""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, conversation_manager


class TestReasoningModalWithWebSearch:
    """Test reasoning modal functionality with web search data."""

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

    def test_reasoning_endpoint_with_actual_web_search_data(self, client, mock_session):
        """Test reasoning endpoint with realistic web search data."""
        # Mock conversation data with realistic web search information
        mock_reasoning_data = {
            "summary_parts": [
                "User is asking about current weather conditions",
                "I need to search for current weather information",
                "Found current weather data from reliable sources"
            ],
            "complete_summary": "The user asked about current weather. I searched for up-to-date weather information from reliable meteorological sources and found that it's currently sunny with mild temperatures.",
            "timestamp": 1704067200,
            "response_id": "resp_weather_search_123",
            "web_searches": [
                {
                    "item_id": "ws_68ce5102e5d481949543f9c6f24b9ad30917ec2dabc2f9ff",
                    "query": "current weather conditions today",
                    "status": "completed",
                    "timestamp": 1704067201,
                    "action_type": "search",
                    "sources": ["weather.com", "noaa.gov", "accuweather.com"],
                    "output_index": 0,
                    "sequence_number": 1
                },
                {
                    "item_id": "ws_68ce5102e5d481949543f9c6f24b9ad30917ec2dabc2f9ff2",
                    "query": "temperature forecast next 24 hours",
                    "status": "completed",
                    "timestamp": 1704067205,
                    "action_type": "search",
                    "sources": ["weather.gov", "weatherchannel.com"],
                    "output_index": 1,
                    "sequence_number": 2
                },
                {
                    "item_id": "ws_68ce5102e5d481949543f9c6f24b9ad30917ec2dabc2f9ff3",
                    "query": "precipitation radar current conditions",
                    "status": "in_progress",
                    "timestamp": 1704067210,
                    "action_type": "search",
                    "output_index": 2,
                    "sequence_number": 3
                }
            ],
            "message_data": {
                "item_id": "msg_68ce51063f488194a13dec765454c0660917ec2dabc2f9ff",
                "role": "assistant",
                "status": "completed",
                "content_items": [
                    {
                        "type": "output_text",
                        "text": "Based on current weather data, it's sunny with a temperature of 72°F and no precipitation expected.",
                        "annotations": [
                            {
                                "type": "citation",
                                "text": "Weather data from NOAA and Weather.com"
                            }
                        ]
                    }
                ]
            }
        }

        mock_conversation = [
            {"role": "user", "text": "What's the weather like today?"},
            {
                "role": "assistant", 
                "text": "Based on current weather data, it's sunny with a temperature of 72°F and no precipitation expected.",
                "reasoning_data": mock_reasoning_data
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Based on current weather data, it\'s sunny with a temperature of 72°F and no precipitation expected.', response_id='resp_weather_search_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            # Test API endpoint
            response = client.get('/chat/reasoning/weather_search_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify complete API response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'weather_search_conv'
            assert data['message_index'] == 1
            assert data['message_role'] == 'assistant'
            
            # Verify reasoning data
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == mock_reasoning_data['complete_summary']
            assert len(reasoning['summary_parts']) == 3
            assert reasoning['response_id'] == 'resp_weather_search_123'
            
            # Verify web search data is included
            assert 'web_searches' in data
            web_searches = data['web_searches']
            assert len(web_searches) == 3
            
            # Verify first search (completed)
            first_search = web_searches[0]
            assert first_search['query'] == "current weather conditions today"
            assert first_search['status'] == "completed"
            assert first_search['action_type'] == "search"
            assert len(first_search['sources']) == 3
            assert "weather.com" in first_search['sources']
            
            # Verify second search (completed)
            second_search = web_searches[1]
            assert second_search['query'] == "temperature forecast next 24 hours"
            assert second_search['status'] == "completed"
            assert len(second_search['sources']) == 2
            
            # Verify third search (in progress)
            third_search = web_searches[2]
            assert third_search['query'] == "precipitation radar current conditions"
            assert third_search['status'] == "in_progress"
            
            # Verify message data is included
            assert 'message_data' in data
            message_data = data['message_data']
            assert message_data['role'] == 'assistant'
            assert message_data['status'] == 'completed'
            assert len(message_data['content_items']) == 1
            
            content_item = message_data['content_items'][0]
            assert content_item['type'] == 'output_text'
            assert 'sunny' in content_item['text']
            assert len(content_item['annotations']) == 1

    def test_reasoning_endpoint_mixed_search_statuses(self, client, mock_session):
        """Test reasoning endpoint with various web search statuses."""
        mock_reasoning_data = {
            "summary_parts": ["Processing complex query with multiple searches"],
            "complete_summary": "I performed several searches to gather comprehensive information.",
            "timestamp": 1704067300,
            "response_id": "resp_mixed_search_123",
            "web_searches": [
                {
                    "item_id": "ws_completed",
                    "query": "completed search query",
                    "status": "completed",
                    "timestamp": 1704067301,
                    "action_type": "search",
                    "sources": ["example.com"]
                },
                {
                    "item_id": "ws_failed",
                    "query": "failed search query",
                    "status": "failed",
                    "timestamp": 1704067302,
                    "action_type": "search"
                },
                {
                    "item_id": "ws_searching",
                    "query": "ongoing search query",
                    "status": "searching",
                    "timestamp": 1704067303,
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
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Here\'s the information I found through multiple searches.', response_id='resp_mixed_search_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            response = client.get('/chat/reasoning/mixed_search_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify web search data with different statuses
            web_searches = data['web_searches']
            assert len(web_searches) == 3
            
            # Find searches by status
            completed_search = next(s for s in web_searches if s['status'] == 'completed')
            failed_search = next(s for s in web_searches if s['status'] == 'failed')
            searching_search = next(s for s in web_searches if s['status'] == 'searching')
            
            assert completed_search['query'] == "completed search query"
            assert 'sources' in completed_search
            
            assert failed_search['query'] == "failed search query"
            assert 'sources' not in failed_search  # Failed searches might not have sources
            
            assert searching_search['query'] == "ongoing search query"

    def test_reasoning_endpoint_empty_web_searches_array(self, client, mock_session):
        """Test reasoning endpoint with empty web searches array."""
        mock_reasoning_data = {
            "summary_parts": ["Simple query without web searches"],
            "complete_summary": "This was a straightforward question that didn't require web searches.",
            "timestamp": 1704067400,
            "response_id": "resp_no_search_123",
            "web_searches": []  # Empty array
        }

        mock_conversation = [
            {"role": "user", "text": "Simple question"},
            {
                "role": "assistant", 
                "text": "Simple answer without web search.",
                "reasoning_data": mock_reasoning_data
            }
        ]
        
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Simple answer without web search.', response_id='resp_no_search_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            response = client.get('/chat/reasoning/no_search_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            
            # Verify reasoning data is present
            assert 'reasoning' in data
            
            # Verify empty web search data is not included in response
            assert 'web_searches' not in data