"""UI integration tests for reasoning inspection functionality."""

import pytest
import json
from unittest.mock import Mock, patch
from app import app, ConversationManager


class TestReasoningUIIntegration:
    """Test reasoning UI integration with backend."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            with app.app_context():
                yield client

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