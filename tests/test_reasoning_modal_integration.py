"""Integration test for reasoning modal with tabbed interface."""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import app, conversation_manager


class TestReasoningModalIntegration:
    """Integration test for the complete reasoning modal functionality."""

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

    def test_complete_reasoning_modal_flow(self, client, mock_session):
        """Test the complete flow from API to frontend display."""
        # Mock conversation data with both reasoning and web search data
        mock_reasoning_data = {
            "summary_parts": [
                "User asked about weather in New York",
                "Searching for current weather information",
                "Found current conditions and temperature"
            ],
            "complete_summary": "I searched for current weather information in New York and found that it's currently sunny with a temperature of 72°F.",
            "timestamp": 1704067200,
            "response_id": "resp_weather_123",
            "web_searches": [
                {
                    "item_id": "ws_68ce5102e5d481949543f9c6f24b9ad30917ec2dabc2f9ff",
                    "query": "weather New York current conditions",
                    "status": "completed",
                    "timestamp": 1704067201,
                    "action_type": "search",
                    "sources": ["weather.com", "noaa.gov"]
                },
                {
                    "item_id": "ws_68ce5102e5d481949543f9c6f24b9ad30917ec2dabc2f9ff2",
                    "query": "New York temperature today",
                    "status": "completed", 
                    "timestamp": 1704067205,
                    "action_type": "search"
                }
            ],
            "message_data": {
                "item_id": "msg_68ce51063f488194a13dec765454c0660917ec2dabc2f9ff",
                "role": "assistant",
                "status": "completed",
                "content_items": [
                    {
                        "type": "output_text",
                        "text": "The current weather in New York is sunny with a temperature of 72°F.",
                        "annotations": [
                            {
                                "type": "citation",
                                "text": "Weather data from weather.com"
                            }
                        ]
                    }
                ]
            }
        }

        mock_conversation = [
            {"role": "user", "text": "What's the weather like in New York?"},
            {
                "role": "assistant", 
                "text": "The current weather in New York is sunny with a temperature of 72°F.",
                "reasoning_data": mock_reasoning_data
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='The current weather in New York is sunny with a temperature of 72°F.', response_id='resp_weather_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_reasoning_data):
            
            # Test API endpoint
            response = client.get('/chat/reasoning/weather_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify complete API response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'weather_conv'
            assert data['message_index'] == 1
            assert data['message_role'] == 'assistant'
            
            # Verify reasoning data
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == mock_reasoning_data['complete_summary']
            assert len(reasoning['summary_parts']) == 3
            assert reasoning['response_id'] == 'resp_weather_123'
            
            # Verify web search data
            web_searches = data['web_searches']
            assert len(web_searches) == 2
            
            # Verify first search
            first_search = web_searches[0]
            assert first_search['query'] == "weather New York current conditions"
            assert first_search['status'] == "completed"
            assert first_search['action_type'] == "search"
            assert len(first_search['sources']) == 2
            
            # Verify second search
            second_search = web_searches[1]
            assert second_search['query'] == "New York temperature today"
            assert second_search['status'] == "completed"
            
            # Verify message data
            message_data = data['message_data']
            assert message_data['role'] == 'assistant'
            assert message_data['status'] == 'completed'
            assert len(message_data['content_items']) == 1
            
            content_item = message_data['content_items'][0]
            assert content_item['type'] == 'output_text'
            assert 'sunny' in content_item['text']
            assert len(content_item['annotations']) == 1

    def test_backward_compatibility_with_old_data(self, client, mock_session):
        """Test that the enhanced modal works with old reasoning data format."""
        # Mock old-style reasoning data (no web searches)
        mock_old_reasoning_data = {
            "summary_parts": ["Processing user question", "Generating response"],
            "complete_summary": "User asked a simple question and I provided a direct answer.",
            "timestamp": 1704067100,
            "response_id": "resp_old_123"
        }

        mock_conversation = [
            {"role": "user", "text": "Hello"},
            {
                "role": "assistant", 
                "text": "Hello! How can I help you today?",
                "reasoning_data": mock_old_reasoning_data
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Hello! How can I help you today?', response_id='resp_old_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_old_reasoning_data):
            
            # Test API endpoint with old data
            response = client.get('/chat/reasoning/old_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'old_conv'
            assert data['message_index'] == 1
            
            # Verify reasoning data is present
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == mock_old_reasoning_data['complete_summary']
            assert len(reasoning['summary_parts']) == 2
            
            # Verify web search data is not included (backward compatibility)
            assert 'web_searches' not in data
            assert 'message_data' not in data

    def test_error_handling_with_malformed_data(self, client, mock_session):
        """Test error handling with malformed reasoning data."""
        # Mock malformed reasoning data
        mock_malformed_data = {
            "summary_parts": ["Valid part"],
            # Missing complete_summary
            "timestamp": "invalid_timestamp",  # Invalid type
            "response_id": "resp_malformed_123",
            "web_searches": "not_an_array"  # Invalid type
        }

        mock_conversation = [
            {"role": "user", "text": "Test question"},
            {
                "role": "assistant", 
                "text": "Test answer",
                "reasoning_data": mock_malformed_data
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Test answer', response_id='resp_malformed_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_malformed_data):
            
            # Test API endpoint with malformed data
            response = client.get('/chat/reasoning/malformed_conv/1')
            
            # Should still return 200 but handle malformed data gracefully
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            
            # Verify reasoning data is present (even if incomplete)
            reasoning = data['reasoning']
            assert len(reasoning['summary_parts']) == 1
            
            # Verify malformed web_searches is not included
            assert 'web_searches' not in data