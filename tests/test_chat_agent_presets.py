"""Tests for chat endpoint agent preset and reasoning level functionality."""

import json
import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from app import AgentPreset, AgentPresetManager, ChatMessage, Conversation, ConversationData


class TestChatAgentPresets:
    """Test chat endpoint with agent preset functionality."""

    @pytest.fixture
    def temp_agent_manager(self):
        """Create a temporary agent preset manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield AgentPresetManager(temp_dir)

    @pytest.fixture
    def test_agent_preset(self):
        """Create a test agent preset."""
        current_time = int(time.time())
        return AgentPreset(
            id="test-preset",
            name="Test Assistant",
            instructions="You are a helpful test assistant.",
            model="gpt-5-mini",
            default_reasoning_level="high",
            created_at=current_time,
            updated_at=current_time,
        )

    def test_chat_message_with_agent_preset_metadata(self):
        """Test that ChatMessage can store agent preset metadata."""
        current_time = int(time.time())
        
        message = ChatMessage(
            role="assistant",
            text="Test response",
            timestamp=current_time,
            response_id="resp_123",
            agent_preset_id="test-preset",
            model="gpt-5-mini",
            reasoning_level="high",
        )
        
        assert message.agent_preset_id == "test-preset"
        assert message.model == "gpt-5-mini"
        assert message.reasoning_level == "high"

    def test_conversation_add_message_with_agent_preset(self):
        """Test that Conversation.add_message accepts agent preset parameters."""
        current_time = int(time.time())
        
        conversation_data = ConversationData(
            id="test-conv",
            created_at=current_time,
            metadata={},
            object="conversation",
        )
        
        conversation = Conversation(
            data=conversation_data,
            chat_name="Test Chat",
            last_update=current_time,
            messages=[],
        )
        
        # Add message with agent preset metadata
        conversation.add_message(
            role="assistant",
            content="Test response",
            response_id="resp_123",
            reasoning_data=None,
            agent_preset_id="test-preset",
            model="gpt-5-mini",
            reasoning_level="high",
        )
        
        assert len(conversation.messages) == 1
        message = conversation.messages[0]
        assert message.agent_preset_id == "test-preset"
        assert message.model == "gpt-5-mini"
        assert message.reasoning_level == "high"

    def test_chat_endpoint_accepts_agent_preset_parameters(self, client):
        """Test chat endpoint accepts agent preset parameters in request."""
        # Set up session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test POST request with agent preset parameters
        response = client.post('/chat', json={
            'user_input': 'Hello, test message',
            'agent_preset_id': 'test-preset',
            'reasoning_level': 'low'
        })
        
        # Verify the request was processed (should return streaming response)
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'

    def test_chat_endpoint_accepts_nonexistent_agent_preset(self, client):
        """Test chat endpoint handles non-existent agent preset gracefully."""
        # Set up session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test POST request with non-existent agent preset
        response = client.post('/chat', json={
            'user_input': 'Hello, test message',
            'agent_preset_id': 'non-existent-preset'
        })
        
        # Verify the request was processed (should fall back gracefully)
        assert response.status_code == 200

    def test_chat_endpoint_without_agent_preset(self, client):
        """Test chat endpoint works when no agent_preset_id provided."""
        # Set up session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test POST request without agent preset
        response = client.post('/chat', json={
            'user_input': 'Hello, test message'
        })
        
        # Verify the request was processed
        assert response.status_code == 200

    def test_chat_message_validation_with_agent_preset_fields(self):
        """Test ChatMessage validation with agent preset fields."""
        current_time = int(time.time())
        
        # Test valid agent preset fields
        message = ChatMessage(
            role="assistant",
            text="Test response",
            timestamp=current_time,
            model="gpt-5-pro",
            reasoning_level="low",
        )
        
        assert message.model == "gpt-5-pro"
        assert message.reasoning_level == "low"
        
        # Test invalid model
        with pytest.raises(ValueError, match="Model must be one of"):
            ChatMessage(
                role="assistant",
                text="Test response",
                timestamp=current_time,
                model="invalid-model",
            )
        
        # Test invalid reasoning level
        with pytest.raises(ValueError, match="Reasoning level must be one of"):
            ChatMessage(
                role="assistant",
                text="Test response",
                timestamp=current_time,
                reasoning_level="invalid-level",
            )