"""
Tests for agent preset functionality including data models and storage.

This module tests the AgentPreset and ChatMessage models, as well as the
AgentPresetManager class for CRUD operations with file-based storage.
"""

import pytest
import time
import json
import os
from unittest.mock import patch, Mock
from typing import Dict, Any

# Mock OpenAI client before importing app components
with patch('openai.OpenAI'):
    from app import AgentPreset, ChatMessage, AgentPresetManager


class TestAgentPresetModel:
    """Test cases for the AgentPreset Pydantic model."""

    def test_valid_agent_preset_creation(self):
        """Test creating a valid agent preset with all required fields."""
        current_time = int(time.time())
        preset = AgentPreset(
            id='test-preset',
            name='Test Assistant',
            instructions='You are a helpful test assistant.',
            model='gpt-5',
            default_reasoning_level='high',
            created_at=current_time,
            updated_at=current_time
        )
        
        assert preset.id == 'test-preset'
        assert preset.name == 'Test Assistant'
        assert preset.instructions == 'You are a helpful test assistant.'
        assert preset.model == 'gpt-5'
        assert preset.default_reasoning_level == 'high'
        assert preset.created_at == current_time
        assert preset.updated_at == current_time

    def test_agent_preset_with_defaults(self):
        """Test creating agent preset with default values."""
        current_time = int(time.time())
        preset = AgentPreset(
            id='default-test',
            name='Default Test',
            instructions='Test instructions',
            created_at=current_time,
            updated_at=current_time
        )
        
        assert preset.model == 'gpt-5'  # Default value
        assert preset.default_reasoning_level == 'medium'  # Default value

    def test_invalid_model_validation(self):
        """Test that invalid model types are rejected."""
        current_time = int(time.time())
        
        with pytest.raises(ValueError, match="Model must be one of"):
            AgentPreset(
                id='invalid-model',
                name='Invalid Model Test',
                instructions='Test',
                model='invalid-model',
                created_at=current_time,
                updated_at=current_time
            )

    def test_invalid_reasoning_level_validation(self):
        """Test that invalid reasoning levels are rejected."""
        current_time = int(time.time())
        
        with pytest.raises(ValueError, match="Reasoning level must be one of"):
            AgentPreset(
                id='invalid-reasoning',
                name='Invalid Reasoning Test',
                instructions='Test',
                default_reasoning_level='invalid-level',
                created_at=current_time,
                updated_at=current_time
            )

    def test_valid_model_types(self):
        """Test all valid model types are accepted."""
        current_time = int(time.time())
        valid_models = ['gpt-5', 'gpt-5-mini', 'gpt-5-pro']
        
        for model in valid_models:
            preset = AgentPreset(
                id=f'test-{model}',
                name=f'Test {model}',
                instructions='Test',
                model=model,
                created_at=current_time,
                updated_at=current_time
            )
            assert preset.model == model

    def test_valid_reasoning_levels(self):
        """Test all valid reasoning levels are accepted."""
        current_time = int(time.time())
        valid_levels = ['high', 'medium', 'low']
        
        for level in valid_levels:
            preset = AgentPreset(
                id=f'test-{level}',
                name=f'Test {level}',
                instructions='Test',
                default_reasoning_level=level,
                created_at=current_time,
                updated_at=current_time
            )
            assert preset.default_reasoning_level == level

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        current_time = int(time.time())
        original_preset = AgentPreset(
            id='json-test',
            name='JSON Test',
            instructions='Test JSON serialization',
            model='gpt-5-pro',
            default_reasoning_level='low',
            created_at=current_time,
            updated_at=current_time
        )
        
        # Serialize to JSON
        json_data = original_preset.model_dump()
        assert isinstance(json_data, dict)
        assert len(json_data) == 7  # All fields present
        
        # Deserialize from JSON
        restored_preset = AgentPreset.model_validate(json_data)
        
        # Verify all fields match
        assert restored_preset.id == original_preset.id
        assert restored_preset.name == original_preset.name
        assert restored_preset.instructions == original_preset.instructions
        assert restored_preset.model == original_preset.model
        assert restored_preset.default_reasoning_level == original_preset.default_reasoning_level
        assert restored_preset.created_at == original_preset.created_at
        assert restored_preset.updated_at == original_preset.updated_at


class TestChatMessageModel:
    """Test cases for the extended ChatMessage Pydantic model."""

    def test_chat_message_with_agent_fields(self):
        """Test creating chat message with new agent-related fields."""
        current_time = int(time.time())
        message = ChatMessage(
            role='assistant',
            text='Hello from agent preset!',
            timestamp=current_time,
            agent_preset_id='test-preset',
            model='gpt-5-pro',
            reasoning_level='high'
        )
        
        assert message.role == 'assistant'
        assert message.text == 'Hello from agent preset!'
        assert message.timestamp == current_time
        assert message.agent_preset_id == 'test-preset'
        assert message.model == 'gpt-5-pro'
        assert message.reasoning_level == 'high'

    def test_chat_message_without_agent_fields(self):
        """Test creating chat message without agent fields (backward compatibility)."""
        current_time = int(time.time())
        message = ChatMessage(
            role='user',
            text='Hello!',
            timestamp=current_time
        )
        
        assert message.role == 'user'
        assert message.text == 'Hello!'
        assert message.timestamp == current_time
        assert message.agent_preset_id is None
        assert message.model is None
        assert message.reasoning_level is None

    def test_invalid_model_in_message(self):
        """Test that invalid model types are rejected in messages."""
        current_time = int(time.time())
        
        with pytest.raises(ValueError, match="Model must be one of"):
            ChatMessage(
                role='assistant',
                text='Test',
                timestamp=current_time,
                model='invalid-model'
            )

    def test_invalid_reasoning_level_in_message(self):
        """Test that invalid reasoning levels are rejected in messages."""
        current_time = int(time.time())
        
        with pytest.raises(ValueError, match="Reasoning level must be one of"):
            ChatMessage(
                role='assistant',
                text='Test',
                timestamp=current_time,
                reasoning_level='invalid-level'
            )

    def test_valid_model_types_in_message(self):
        """Test all valid model types are accepted in messages."""
        current_time = int(time.time())
        valid_models = ['gpt-5', 'gpt-5-mini', 'gpt-5-pro']
        
        for model in valid_models:
            message = ChatMessage(
                role='assistant',
                text='Test',
                timestamp=current_time,
                model=model
            )
            assert message.model == model

    def test_valid_reasoning_levels_in_message(self):
        """Test all valid reasoning levels are accepted in messages."""
        current_time = int(time.time())
        valid_levels = ['high', 'medium', 'low']
        
        for level in valid_levels:
            message = ChatMessage(
                role='assistant',
                text='Test',
                timestamp=current_time,
                reasoning_level=level
            )
            assert message.reasoning_level == level


class TestAgentPresetManager:
    """Test cases for the AgentPresetManager class."""

    @pytest.fixture
    def manager(self, temp_dir):
        """Create an AgentPresetManager instance for testing."""
        return AgentPresetManager(temp_dir)

    @pytest.fixture
    def sample_preset(self):
        """Create a sample agent preset for testing."""
        current_time = int(time.time())
        return AgentPreset(
            id='sample-preset',
            name='Sample Assistant',
            instructions='You are a sample assistant for testing.',
            model='gpt-5',
            default_reasoning_level='medium',
            created_at=current_time,
            updated_at=current_time
        )

    def test_create_preset(self, manager, sample_preset):
        """Test creating a new agent preset."""
        username = 'testuser'
        preset_id = manager.create_preset(username, sample_preset)
        
        assert preset_id == sample_preset.id
        
        # Verify the preset was saved
        retrieved = manager.get_preset(username, preset_id)
        assert retrieved is not None
        assert retrieved.id == sample_preset.id
        assert retrieved.name == sample_preset.name

    def test_get_preset_existing(self, manager, sample_preset):
        """Test retrieving an existing preset."""
        username = 'testuser'
        manager.create_preset(username, sample_preset)
        
        retrieved = manager.get_preset(username, sample_preset.id)
        assert retrieved is not None
        assert retrieved.id == sample_preset.id
        assert retrieved.name == sample_preset.name
        assert retrieved.instructions == sample_preset.instructions

    def test_get_preset_nonexistent(self, manager):
        """Test retrieving a non-existent preset returns None."""
        username = 'testuser'
        retrieved = manager.get_preset(username, 'nonexistent-preset')
        assert retrieved is None

    def test_list_presets_empty(self, manager):
        """Test listing presets when none exist."""
        username = 'testuser'
        presets = manager.list_presets(username)
        assert presets == []

    def test_list_presets_with_data(self, manager, sample_preset):
        """Test listing presets when some exist."""
        username = 'testuser'
        manager.create_preset(username, sample_preset)
        
        presets = manager.list_presets(username)
        assert len(presets) == 1
        assert presets[0].id == sample_preset.id

    def test_update_preset_existing(self, manager, sample_preset):
        """Test updating an existing preset."""
        username = 'testuser'
        manager.create_preset(username, sample_preset)
        
        # Modify the preset
        sample_preset.name = 'Updated Assistant'
        sample_preset.instructions = 'Updated instructions'
        
        success = manager.update_preset(username, sample_preset)
        assert success is True
        
        # Verify the update
        retrieved = manager.get_preset(username, sample_preset.id)
        assert retrieved.name == 'Updated Assistant'
        assert retrieved.instructions == 'Updated instructions'

    def test_update_preset_nonexistent(self, manager, sample_preset):
        """Test updating a non-existent preset returns False."""
        username = 'testuser'
        success = manager.update_preset(username, sample_preset)
        assert success is False

    def test_delete_preset_existing(self, manager, sample_preset):
        """Test deleting an existing preset."""
        username = 'testuser'
        manager.create_preset(username, sample_preset)
        
        success = manager.delete_preset(username, sample_preset.id)
        assert success is True
        
        # Verify deletion
        retrieved = manager.get_preset(username, sample_preset.id)
        assert retrieved is None

    def test_delete_preset_nonexistent(self, manager):
        """Test deleting a non-existent preset returns False."""
        username = 'testuser'
        success = manager.delete_preset(username, 'nonexistent-preset')
        assert success is False

    def test_delete_default_preset_protection(self, manager):
        """Test that default preset cannot be deleted."""
        username = 'testuser'
        manager.ensure_default_preset(username)
        
        success = manager.delete_preset(username, 'default')
        assert success is False
        
        # Verify default preset still exists
        default_preset = manager.get_preset(username, 'default')
        assert default_preset is not None

    def test_get_default_preset(self, manager):
        """Test getting the built-in default preset."""
        default_preset = manager.get_default_preset()
        
        assert default_preset.id == 'default'
        assert default_preset.name == 'Default Assistant'
        assert default_preset.model == 'gpt-5'
        assert default_preset.default_reasoning_level == 'medium'
        assert len(default_preset.instructions) > 0

    def test_ensure_default_preset(self, manager):
        """Test ensuring default preset exists for a user."""
        username = 'testuser'
        
        # Initially no presets
        presets = manager.list_presets(username)
        assert len(presets) == 0
        
        # Ensure default preset
        manager.ensure_default_preset(username)
        
        # Verify default preset was created
        presets = manager.list_presets(username)
        assert len(presets) == 1
        assert presets[0].id == 'default'

    def test_file_storage_persistence(self, manager, sample_preset, temp_dir):
        """Test that presets are properly persisted to file storage."""
        username = 'testuser'
        manager.create_preset(username, sample_preset)
        
        # Verify file was created
        user_file = os.path.join(temp_dir, 'agents', f'{username}.json')
        assert os.path.exists(user_file)
        
        # Verify file contents
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'presets' in data
        assert sample_preset.id in data['presets']
        assert data['presets'][sample_preset.id]['name'] == sample_preset.name

    def test_concurrent_access_protection(self, manager, sample_preset):
        """Test that concurrent access is properly handled with locks."""
        username = 'testuser'
        
        # This test verifies that the locking mechanism exists
        # In a real concurrent scenario, this would prevent race conditions
        lock = manager._get_user_lock(username)
        assert lock is not None
        
        # Test that multiple calls return the same lock
        lock2 = manager._get_user_lock(username)
        assert lock is lock2

    def test_error_handling_corrupted_file(self, manager, temp_dir):
        """Test error handling when preset file is corrupted."""
        username = 'testuser'
        
        # Create corrupted JSON file
        user_file = os.path.join(temp_dir, 'agents', f'{username}.json')
        os.makedirs(os.path.dirname(user_file), exist_ok=True)
        with open(user_file, 'w') as f:
            f.write('invalid json content')
        
        # Should handle corruption gracefully
        presets = manager.list_presets(username)
        assert presets == []
        
        # Should be able to create new presets after corruption
        current_time = int(time.time())
        new_preset = AgentPreset(
            id='recovery-test',
            name='Recovery Test',
            instructions='Test recovery',
            created_at=current_time,
            updated_at=current_time
        )
        
        preset_id = manager.create_preset(username, new_preset)
        assert preset_id == new_preset.id

    def test_duplicate_preset_id_rejection(self, manager, sample_preset):
        """Test that duplicate preset IDs are rejected."""
        username = 'testuser'
        
        # Create first preset
        manager.create_preset(username, sample_preset)
        
        # Try to create another preset with same ID
        with pytest.raises(ValueError, match="already exists"):
            manager.create_preset(username, sample_preset)