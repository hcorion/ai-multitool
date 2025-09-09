"""Integration tests for reasoning inspection UI with backend."""

import pytest
import json
from unittest.mock import Mock, patch
from app import app, ConversationManager


class TestReasoningUIIntegration:
    """Test complete reasoning inspection UI integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            with app.app_context():
                yield client

    @pytest.fixture
    def mock_conversation_with_reasoning(self):
        """Create a mock conversation with reasoning data."""
        from app import Conversation, ConversationData, ChatMessage
        
        # Create mock conversation data
        conv_data = ConversationData(
            id="test-conversation",
            created_at=1234567890,
            metadata={},
            object="thread"
        )
        
        # Create messages
        user_message = ChatMessage(
            role="user",
            text="What is 2+2?",
            timestamp=1234567890
        )
        
        assistant_message = ChatMessage(
            role="assistant",
            text="2+2 equals 4.",
            timestamp=1234567891,
            response_id="resp_123",
            reasoning_data={
                "summary_parts": ["I need to calculate 2+2", "This is basic arithmetic"],
                "complete_summary": "I need to calculate 2+2. This is basic arithmetic. The answer is 4.",
                "timestamp": 1234567891,
                "response_id": "resp_123"
            }
        )
        
        # Create conversation
        conversation = Conversation(
            data=conv_data,
            chat_name="Test Chat",
            last_update=1234567891,
            messages=[user_message, assistant_message]
        )
        
        return conversation

    def test_reasoning_endpoint_returns_correct_data(self, client, mock_conversation_with_reasoning):
        """Test that the reasoning endpoint returns correct data."""
        with patch.object(ConversationManager, 'get_conversation') as mock_get_conv:
            with patch.object(ConversationManager, 'get_message_reasoning_data') as mock_get_reasoning:
                with patch.object(ConversationManager, 'get_message_by_index') as mock_get_message:
                    # Mock session
                    with client.session_transaction() as sess:
                        sess['username'] = 'testuser'
                    
                    # Mock conversation exists
                    mock_get_conv.return_value = mock_conversation_with_reasoning
                    
                    # Mock message exists and is assistant message
                    mock_get_message.return_value = mock_conversation_with_reasoning.messages[1]  # Assistant message
                    
                    # Mock reasoning data
                    mock_get_reasoning.return_value = {
                        "summary_parts": ["I need to calculate 2+2", "This is basic arithmetic"],
                        "complete_summary": "I need to calculate 2+2. This is basic arithmetic. The answer is 4.",
                        "timestamp": 1234567891,
                        "response_id": "resp_123"
                    }
                    
                    # Make request to reasoning endpoint
                    response = client.get('/chat/reasoning/test-conversation/1')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    
                    assert 'reasoning' in data
                    assert data['reasoning']['complete_summary'] == "I need to calculate 2+2. This is basic arithmetic. The answer is 4."
                    assert len(data['reasoning']['summary_parts']) == 2
                    assert data['success'] is True

    def test_reasoning_endpoint_handles_missing_data(self, client):
        """Test that the reasoning endpoint handles missing reasoning data gracefully."""
        with patch.object(ConversationManager, 'get_conversation') as mock_get_conv:
            with patch.object(ConversationManager, 'get_message_reasoning_data') as mock_get_reasoning:
                with patch.object(ConversationManager, 'get_message_by_index') as mock_get_message:
                    # Mock session
                    with client.session_transaction() as sess:
                        sess['username'] = 'testuser'
                    
                    # Mock conversation exists but no reasoning data
                    from app import Conversation, ConversationData, ChatMessage
                    
                    conv_data = ConversationData(
                        id="test-conversation",
                        created_at=1234567890,
                        metadata={},
                        object="thread"
                    )
                    
                    user_message = ChatMessage(role="user", text="Hello", timestamp=1234567890)
                    assistant_message = ChatMessage(role="assistant", text="Hi there!", timestamp=1234567891)
                    
                    conversation = Conversation(
                        data=conv_data,
                        chat_name="Test Chat",
                        last_update=1234567891,
                        messages=[user_message, assistant_message]
                    )
                    
                    mock_get_conv.return_value = conversation
                    mock_get_message.return_value = assistant_message  # Assistant message
                    mock_get_reasoning.return_value = None
                    
                    # Make request to reasoning endpoint
                    response = client.get('/chat/reasoning/test-conversation/1')
                    
                    assert response.status_code == 404
                    data = json.loads(response.data)
                    
                    assert 'error' in data
                    assert 'reasoning data' in data['error'].lower()

    def test_reasoning_endpoint_authentication_required(self, client):
        """Test that the reasoning endpoint requires authentication."""
        # Make request without session
        response = client.get('/chat/reasoning/test-conversation/1')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'authentication' in data['error'].lower()

    def test_reasoning_endpoint_validates_message_index(self, client, mock_conversation_with_reasoning):
        """Test that the reasoning endpoint validates message index."""
        with patch.object(ConversationManager, 'get_conversation') as mock_get_conv:
            # Mock session
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
            
            # Mock conversation with only 2 messages (indices 0 and 1)
            mock_get_conv.return_value = mock_conversation_with_reasoning
            
            # Request invalid message index
            response = client.get('/chat/reasoning/test-conversation/5')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'message index' in data['error'].lower()

    def test_reasoning_endpoint_user_message_returns_error(self, client, mock_conversation_with_reasoning):
        """Test that requesting reasoning for user message returns error."""
        with patch.object(ConversationManager, 'get_conversation') as mock_get_conv:
            with patch.object(ConversationManager, 'get_message_by_index') as mock_get_message:
                # Mock session
                with client.session_transaction() as sess:
                    sess['username'] = 'testuser'
                
                mock_get_conv.return_value = mock_conversation_with_reasoning
                mock_get_message.return_value = mock_conversation_with_reasoning.messages[0]  # User message
                
                # Request reasoning for user message (index 0)
                response = client.get('/chat/reasoning/test-conversation/0')
                
                assert response.status_code == 400  # Should return error for user messages
                data = json.loads(response.data)
                
                assert 'error' in data
                assert 'reasoning' in data['error'].lower()

    def test_html_template_includes_reasoning_modal(self, client):
        """Test that the main template includes the reasoning modal."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/')
        assert response.status_code == 200
        
        html_content = response.data.decode('utf-8')
        
        # Check that reasoning modal elements are present
        assert 'id="reasoning-modal"' in html_content
        assert 'id="reasoning-content"' in html_content
        assert 'id="reasoning-loading"' in html_content
        assert 'id="reasoning-error"' in html_content
        assert 'reasoning-modal-close' in html_content

    def test_css_includes_reasoning_styles(self, client):
        """Test that the compiled CSS includes reasoning styles."""
        response = client.get('/static/css/style.css')
        assert response.status_code == 200
        
        css_content = response.data.decode('utf-8')
        
        # Check that reasoning CSS classes are present
        assert '.reasoning-button' in css_content
        assert '.reasoning-modal' in css_content
        assert '.reasoning-modal-content' in css_content
        assert 'position: absolute' in css_content  # reasoning button positioning

    def test_javascript_includes_reasoning_functions(self, client):
        """Test that the compiled JavaScript includes reasoning functions."""
        # Test chat.js
        response = client.get('/static/js/chat.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        assert 'addReasoningButton' in js_content
        assert 'showReasoningModal' in js_content
        assert 'reasoning-button' in js_content
        
        # Test script.js
        response = client.get('/static/js/script.js')
        assert response.status_code == 200
        
        js_content = response.data.decode('utf-8')
        assert 'addReasoningButtonToMessage' in js_content
        assert 'showReasoningModalFromScript' in js_content
        assert '/chat/reasoning/' in js_content