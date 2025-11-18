"""
Tests for agent preset API endpoints.

This module tests the Flask API endpoints for agent preset management,
including authentication, validation, and CRUD operations.
"""

import pytest
import json
import tempfile
import shutil
from unittest.mock import patch

# Mock OpenAI client before importing app
with patch('openai.OpenAI'):
    from app import app


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(temp_dir):
    """Create a test client for the Flask app with isolated storage."""
    app.config['TESTING'] = True
    # Override the static folder to use our temp directory
    original_static_folder = app.static_folder
    app.static_folder = temp_dir
    
    # Reinitialize the agent preset manager with the temp directory
    from app import AgentPresetManager
    import app as app_module
    original_manager = app_module.agent_preset_manager
    app_module.agent_preset_manager = AgentPresetManager(temp_dir)
    
    with app.test_client() as client:
        yield client
    
    # Restore original static folder and manager
    app.static_folder = original_static_folder
    app_module.agent_preset_manager = original_manager


@pytest.fixture
def authenticated_session(client):
    """Create an authenticated session for testing."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
    return client


class TestAgentPresetAPIAuthentication:
    """Test authentication requirements for agent preset API endpoints."""

    def test_get_agents_requires_authentication(self, client):
        """Test that GET /agents requires authentication."""
        response = client.get('/agents')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'AuthenticationError'

    def test_post_agents_requires_authentication(self, client):
        """Test that POST /agents requires authentication."""
        response = client.post('/agents', json={'name': 'Test', 'instructions': 'Test'})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'AuthenticationError'

    def test_get_agent_by_id_requires_authentication(self, client):
        """Test that GET /agents/<id> requires authentication."""
        response = client.get('/agents/test-id')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'

    def test_put_agent_requires_authentication(self, client):
        """Test that PUT /agents/<id> requires authentication."""
        response = client.put('/agents/test-id', json={'name': 'Test', 'instructions': 'Test'})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'

    def test_delete_agent_requires_authentication(self, client):
        """Test that DELETE /agents/<id> requires authentication."""
        response = client.delete('/agents/test-id')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Not authenticated'


class TestAgentPresetAPIList:
    """Test the GET /agents endpoint for listing agent presets."""

    def test_list_agents_empty(self, authenticated_session):
        """Test listing agents when none exist (should include default)."""
        response = authenticated_session.get('/agents')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'presets' in data
        assert len(data['presets']) == 1  # Default preset should be created
        assert data['presets'][0]['id'] == 'default'
        assert data['presets'][0]['name'] == 'Default Assistant'

    def test_list_agents_with_custom_presets(self, authenticated_session):
        """Test listing agents when custom presets exist."""
        # Create a custom preset first
        preset_data = {
            'name': 'Custom Assistant',
            'instructions': 'You are a custom assistant.',
            'model': 'gpt-5-pro',
            'default_reasoning_level': 'high'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        
        # List all presets
        response = authenticated_session.get('/agents')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'presets' in data
        assert len(data['presets']) == 2  # Default + custom preset
        
        # Find the custom preset
        custom_preset = next((p for p in data['presets'] if p['name'] == 'Custom Assistant'), None)
        assert custom_preset is not None
        assert custom_preset['model'] == 'gpt-5-pro'
        assert custom_preset['default_reasoning_level'] == 'high'


class TestAgentPresetAPICreate:
    """Test the POST /agents endpoint for creating agent presets."""

    def test_create_agent_valid_data(self, authenticated_session):
        """Test creating an agent preset with valid data."""
        preset_data = {
            'name': 'Test Assistant',
            'instructions': 'You are a helpful test assistant.',
            'model': 'gpt-5',
            'default_reasoning_level': 'medium'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'preset_id' in data
        assert 'preset' in data
        
        preset = data['preset']
        assert preset['name'] == 'Test Assistant'
        assert preset['instructions'] == 'You are a helpful test assistant.'
        assert preset['model'] == 'gpt-5'
        assert preset['default_reasoning_level'] == 'medium'
        assert 'created_at' in preset
        assert 'updated_at' in preset

    def test_create_agent_with_defaults(self, authenticated_session):
        """Test creating an agent preset with default model and reasoning level."""
        preset_data = {
            'name': 'Default Test',
            'instructions': 'Test with defaults.'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 201
        
        data = json.loads(response.data)
        preset = data['preset']
        assert preset['model'] == 'gpt-5.1'  # Default value
        assert preset['default_reasoning_level'] == 'medium'  # Default value

    def test_create_agent_missing_name(self, authenticated_session):
        """Test creating an agent preset without required name field."""
        preset_data = {
            'instructions': 'Test instructions.'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing required field: name' in data['error']

    def test_create_agent_missing_instructions(self, authenticated_session):
        """Test creating an agent preset without required instructions field."""
        preset_data = {
            'name': 'Test Assistant'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing required field: instructions' in data['error']

    def test_create_agent_empty_name(self, authenticated_session):
        """Test creating an agent preset with empty name."""
        preset_data = {
            'name': '   ',  # Whitespace only
            'instructions': 'Test instructions.'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing required field: name' in data['error']

    def test_create_agent_invalid_model(self, authenticated_session):
        """Test creating an agent preset with invalid model."""
        preset_data = {
            'name': 'Test Assistant',
            'instructions': 'Test instructions.',
            'model': 'invalid-model'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation error' in data['error']

    def test_create_agent_invalid_reasoning_level(self, authenticated_session):
        """Test creating an agent preset with invalid reasoning level."""
        preset_data = {
            'name': 'Test Assistant',
            'instructions': 'Test instructions.',
            'default_reasoning_level': 'invalid-level'
        }
        
        response = authenticated_session.post('/agents', json=preset_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation error' in data['error']

    def test_create_agent_non_json_request(self, authenticated_session):
        """Test creating an agent preset with non-JSON request."""
        response = authenticated_session.post('/agents', data='not json')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'ValidationError'
        assert 'Request must be JSON' in data['error_message']

    def test_create_agent_empty_json(self, authenticated_session):
        """Test creating an agent preset with empty JSON."""
        response = authenticated_session.post('/agents', json={})
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'ValidationError'
        assert 'Missing required field' in data['error_message']


class TestAgentPresetAPIGet:
    """Test the GET /agents/<id> endpoint for retrieving specific agent presets."""

    def test_get_existing_agent(self, authenticated_session):
        """Test retrieving an existing agent preset."""
        # Create a preset first
        preset_data = {
            'name': 'Retrieval Test',
            'instructions': 'Test retrieval functionality.',
            'model': 'gpt-5-mini'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # Retrieve the preset
        response = authenticated_session.get(f'/agents/{preset_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'preset' in data
        
        preset = data['preset']
        assert preset['id'] == preset_id
        assert preset['name'] == 'Retrieval Test'
        assert preset['instructions'] == 'Test retrieval functionality.'
        assert preset['model'] == 'gpt-5-mini'

    def test_get_nonexistent_agent(self, authenticated_session):
        """Test retrieving a non-existent agent preset."""
        response = authenticated_session.get('/agents/nonexistent-id')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['error'] == 'Agent preset not found'

    def test_get_default_agent(self, authenticated_session):
        """Test retrieving the default agent preset."""
        # Ensure default preset exists
        authenticated_session.get('/agents')
        
        # Retrieve default preset
        response = authenticated_session.get('/agents/default')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        preset = data['preset']
        assert preset['id'] == 'default'
        assert preset['name'] == 'Default Assistant'


class TestAgentPresetAPIUpdate:
    """Test the PUT /agents/<id> endpoint for updating agent presets."""

    def test_update_existing_agent(self, authenticated_session):
        """Test updating an existing agent preset."""
        # Create a preset first
        preset_data = {
            'name': 'Original Name',
            'instructions': 'Original instructions.',
            'model': 'gpt-5'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # Update the preset
        update_data = {
            'name': 'Updated Name',
            'instructions': 'Updated instructions.',
            'model': 'gpt-5-pro',
            'default_reasoning_level': 'high'
        }
        
        response = authenticated_session.put(f'/agents/{preset_id}', json=update_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        preset = data['preset']
        assert preset['name'] == 'Updated Name'
        assert preset['instructions'] == 'Updated instructions.'
        assert preset['model'] == 'gpt-5-pro'
        assert preset['default_reasoning_level'] == 'high'

    def test_update_nonexistent_agent(self, authenticated_session):
        """Test updating a non-existent agent preset."""
        update_data = {
            'name': 'Updated Name',
            'instructions': 'Updated instructions.'
        }
        
        response = authenticated_session.put('/agents/nonexistent-id', json=update_data)
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['error'] == 'Agent preset not found'

    def test_update_agent_missing_fields(self, authenticated_session):
        """Test updating an agent preset with missing required fields."""
        # Create a preset first
        preset_data = {
            'name': 'Test Update',
            'instructions': 'Test instructions.'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # Try to update without required fields
        update_data = {
            'name': 'Updated Name'
            # Missing instructions
        }
        
        response = authenticated_session.put(f'/agents/{preset_id}', json=update_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Missing required field: instructions' in data['error']

    def test_update_agent_invalid_data(self, authenticated_session):
        """Test updating an agent preset with invalid data."""
        # Create a preset first
        preset_data = {
            'name': 'Test Update',
            'instructions': 'Test instructions.'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # Try to update with invalid model
        update_data = {
            'name': 'Updated Name',
            'instructions': 'Updated instructions.',
            'model': 'invalid-model'
        }
        
        response = authenticated_session.put(f'/agents/{preset_id}', json=update_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Validation error' in data['error']


class TestAgentPresetAPIDelete:
    """Test the DELETE /agents/<id> endpoint for deleting agent presets."""

    def test_delete_existing_agent(self, authenticated_session):
        """Test deleting an existing agent preset."""
        # Create a preset first
        preset_data = {
            'name': 'Delete Test',
            'instructions': 'This preset will be deleted.'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # Delete the preset
        response = authenticated_session.delete(f'/agents/{preset_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Preset deleted successfully'
        
        # Verify the preset is gone
        get_response = authenticated_session.get(f'/agents/{preset_id}')
        assert get_response.status_code == 404

    def test_delete_nonexistent_agent(self, authenticated_session):
        """Test deleting a non-existent agent preset."""
        response = authenticated_session.delete('/agents/nonexistent-id')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['error'] == 'Agent preset not found'

    def test_delete_default_agent_protection(self, authenticated_session):
        """Test that default agent preset cannot be deleted."""
        # Ensure default preset exists
        authenticated_session.get('/agents')
        
        response = authenticated_session.delete('/agents/default')
        assert response.status_code == 403
        
        data = json.loads(response.data)
        assert data['error'] == 'Cannot delete default preset'
        
        # Verify default preset still exists
        get_response = authenticated_session.get('/agents/default')
        assert get_response.status_code == 200


class TestAgentPresetAPIIntegration:
    """Integration tests for the complete agent preset API workflow."""

    def test_complete_crud_workflow(self, authenticated_session):
        """Test complete CRUD workflow for agent presets."""
        # 1. List presets (should have default only)
        list_response = authenticated_session.get('/agents')
        assert list_response.status_code == 200
        initial_data = json.loads(list_response.data)
        assert len(initial_data['presets']) == 1  # Default preset
        
        # 2. Create a new preset
        preset_data = {
            'name': 'CRUD Test Assistant',
            'instructions': 'You are a test assistant for CRUD operations.',
            'model': 'gpt-5-pro',
            'default_reasoning_level': 'high'
        }
        
        create_response = authenticated_session.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        create_data = json.loads(create_response.data)
        preset_id = create_data['preset_id']
        
        # 3. List presets (should have default + new preset)
        list_response = authenticated_session.get('/agents')
        list_data = json.loads(list_response.data)
        assert len(list_data['presets']) == 2
        
        # 4. Get the specific preset
        get_response = authenticated_session.get(f'/agents/{preset_id}')
        assert get_response.status_code == 200
        get_data = json.loads(get_response.data)
        assert get_data['preset']['name'] == 'CRUD Test Assistant'
        
        # 5. Update the preset
        update_data = {
            'name': 'Updated CRUD Assistant',
            'instructions': 'Updated instructions for CRUD test.',
            'model': 'gpt-5-mini',
            'default_reasoning_level': 'low'
        }
        
        update_response = authenticated_session.put(f'/agents/{preset_id}', json=update_data)
        assert update_response.status_code == 200
        update_response_data = json.loads(update_response.data)
        assert update_response_data['preset']['name'] == 'Updated CRUD Assistant'
        
        # 6. Verify the update
        get_response = authenticated_session.get(f'/agents/{preset_id}')
        get_data = json.loads(get_response.data)
        assert get_data['preset']['name'] == 'Updated CRUD Assistant'
        assert get_data['preset']['model'] == 'gpt-5-mini'
        
        # 7. Delete the preset
        delete_response = authenticated_session.delete(f'/agents/{preset_id}')
        assert delete_response.status_code == 200
        
        # 8. Verify deletion
        get_response = authenticated_session.get(f'/agents/{preset_id}')
        assert get_response.status_code == 404
        
        # 9. List presets (should have default only again)
        list_response = authenticated_session.get('/agents')
        final_data = json.loads(list_response.data)
        assert len(final_data['presets']) == 1  # Back to default only

    def test_multiple_users_isolation(self, client):
        """Test that agent presets are isolated between different users."""
        # User 1 creates a preset
        with client.session_transaction() as sess:
            sess['username'] = 'user1'
        
        preset_data = {
            'name': 'User 1 Assistant',
            'instructions': 'Assistant for user 1.'
        }
        
        create_response = client.post('/agents', json=preset_data)
        assert create_response.status_code == 201
        
        # User 2 should not see user 1's preset
        with client.session_transaction() as sess:
            sess['username'] = 'user2'
        
        list_response = client.get('/agents')
        assert list_response.status_code == 200
        data = json.loads(list_response.data)
        assert len(data['presets']) == 1  # Only default preset
        assert data['presets'][0]['id'] == 'default'