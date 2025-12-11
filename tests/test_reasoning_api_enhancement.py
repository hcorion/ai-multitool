"""Tests for enhanced reasoning API endpoint with web search data."""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from app import app, conversation_manager


class TestReasoningAPIEnhancement:
    """Test enhanced reasoning API endpoint functionality."""

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

    def test_reasoning_endpoint_with_web_search_data(self, client, mock_session):
        """Test that reasoning endpoint returns web search data when available."""
        # Mock conversation data with web search information
        mock_conversation = [
            {"role": "user", "text": "What's the weather like?"},
            {
                "role": "assistant", 
                "text": "The weather is sunny today.",
                "reasoning_data": {
                    "summary_parts": ["Checking weather data", "Analyzing current conditions"],
                    "complete_summary": "I searched for current weather information and found it's sunny.",
                    "timestamp": 1704067200,
                    "response_id": "resp_123",
                    "web_searches": [
                        {
                            "item_id": "ws_123",
                            "query": "current weather",
                            "status": "completed",
                            "timestamp": 1704067201,
                            "action_type": "search",
                            "sources": ["weather.com"]
                        }
                    ],
                    "message_data": {
                        "item_id": "msg_123",
                        "role": "assistant",
                        "status": "completed",
                        "content_items": [
                            {
                                "type": "output_text",
                                "text": "The weather is sunny today.",
                                "annotations": []
                            }
                        ]
                    }
                }
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='The weather is sunny today.', response_id='resp_123')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_conversation[1]['reasoning_data']):
            
            response = client.get('/chat/reasoning/test_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'test_conv'
            assert data['message_index'] == 1
            assert data['message_role'] == 'assistant'
            
            # Verify reasoning data
            assert 'reasoning' in data
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == "I searched for current weather information and found it's sunny."
            assert len(reasoning['summary_parts']) == 2
            
            # Verify web search data is included
            assert 'web_searches' in data
            web_searches = data['web_searches']
            assert len(web_searches) == 1
            assert web_searches[0]['query'] == "current weather"
            assert web_searches[0]['status'] == "completed"
            assert web_searches[0]['action_type'] == "search"
            
            # Verify message data is included
            assert 'message_data' in data
            message_data = data['message_data']
            assert message_data['role'] == 'assistant'
            assert message_data['status'] == 'completed'

    def test_reasoning_endpoint_without_web_search_data(self, client, mock_session):
        """Test that reasoning endpoint works without web search data (backward compatibility)."""
        # Mock conversation data without web search information
        mock_conversation = [
            {"role": "user", "text": "Hello"},
            {
                "role": "assistant", 
                "text": "Hello there!",
                "reasoning_data": {
                    "summary_parts": ["Processing greeting"],
                    "complete_summary": "User said hello, responding with greeting.",
                    "timestamp": 1704067200,
                    "response_id": "resp_456"
                }
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Hello there!', response_id='resp_456')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_conversation[1]['reasoning_data']):
            
            response = client.get('/chat/reasoning/test_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            assert data['conversation_id'] == 'test_conv'
            assert data['message_index'] == 1
            
            # Verify reasoning data
            assert 'reasoning' in data
            reasoning = data['reasoning']
            assert reasoning['complete_summary'] == "User said hello, responding with greeting."
            
            # Verify web search data is not included when not available
            assert 'web_searches' not in data
            assert 'message_data' not in data

    def test_reasoning_endpoint_empty_web_search_data(self, client, mock_session):
        """Test that reasoning endpoint handles empty web search data correctly."""
        # Mock conversation data with empty web search array
        mock_conversation = [
            {"role": "user", "text": "Simple question"},
            {
                "role": "assistant", 
                "text": "Simple answer.",
                "reasoning_data": {
                    "summary_parts": ["Processing question"],
                    "complete_summary": "Answered the question directly.",
                    "timestamp": 1704067200,
                    "response_id": "resp_789",
                    "web_searches": []  # Empty array
                }
            }
        ]
        
        # Mock conversation manager methods
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=2), \
             patch.object(conversation_manager, 'get_message_by_index', return_value=MagicMock(role='assistant', text='Simple answer.', response_id='resp_789')), \
             patch.object(conversation_manager, 'get_message_reasoning_data', return_value=mock_conversation[1]['reasoning_data']):
            
            response = client.get('/chat/reasoning/test_conv/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Verify basic response structure
            assert data['success'] is True
            
            # Verify reasoning data
            assert 'reasoning' in data
            
            # Verify empty web search data is not included
            assert 'web_searches' not in data

    def test_reasoning_endpoint_error_handling(self, client, mock_session):
        """Test that reasoning endpoint handles errors gracefully."""
        # Test conversation not found
        with patch.object(conversation_manager, 'get_conversation', return_value=None):
            response = client.get('/chat/reasoning/nonexistent/0')
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Conversation not found'

        # Test invalid message index
        mock_conversation = [{"role": "user", "text": "Hello"}]
        with patch.object(conversation_manager, 'get_conversation', return_value=mock_conversation), \
             patch.object(conversation_manager, 'get_conversation_message_count', return_value=1):
            response = client.get('/chat/reasoning/test_conv/5')
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Invalid message index' in data['error']

    def test_reasoning_endpoint_authentication(self, client):
        """Test that reasoning endpoint requires authentication."""
        # Test without session
        response = client.get('/chat/reasoning/test_conv/0')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error_message' in data
        assert data['error_message'] == 'Authentication required'