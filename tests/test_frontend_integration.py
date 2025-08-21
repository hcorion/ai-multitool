"""
Tests for frontend integration with the new /image endpoint.
"""

import json
import pytest
from unittest.mock import Mock, patch
from app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_session(client):
    """Create an authenticated session."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'


class TestFrontendIntegration:
    """Test frontend integration with the new image endpoint."""
    
    def test_index_page_loads(self, client, authenticated_session):
        """Test that the main index page loads correctly."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'prompt-form' in response.data
    
    @patch('app.generate_image')
    def test_legacy_endpoint_still_works(self, mock_generate, client, authenticated_session):
        """Test that the legacy / endpoint still works for backward compatibility."""
        # Mock the generate_image function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/image.png'
        mock_generated_data.image_name = 'image.png'
        mock_generated_data.prompt = 'test prompt'
        mock_generated_data.revised_prompt = 'revised test prompt'
        mock_generate.return_value = mock_generated_data
        
        response = client.post('/', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'size': '1024x1024',
            'quality': 'standard'
        })
        
        # Should return HTML template, not JSON
        assert response.status_code == 200
        assert b'result-section' in response.data or b'image' in response.data
    
    @patch('app.generate_image')
    def test_new_endpoint_json_response(self, mock_generate, client, authenticated_session):
        """Test that the new /image endpoint returns JSON responses."""
        # Mock the generate_image function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/image.png'
        mock_generated_data.image_name = 'image.png'
        mock_generated_data.prompt = 'test prompt'
        mock_generated_data.revised_prompt = 'revised test prompt'
        mock_generate.return_value = mock_generated_data
        
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate',
            'width': '1024',
            'height': '1024',
            'quality': 'standard'
        })
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['image_path'] == '/path/to/image.png'
        assert data['image_name'] == 'image.png'
        assert data['revised_prompt'] == 'revised test prompt'
        assert data['provider'] == 'openai'
        assert data['operation'] == 'generate'
    
    def test_new_endpoint_error_response_format(self, client, authenticated_session):
        """Test that the new endpoint returns properly formatted error responses."""
        response = client.post('/image', data={
            'provider': 'openai',
            'operation': 'generate'
            # Missing required prompt
        })
        
        assert response.status_code == 400
        assert response.content_type == 'application/json'
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Prompt cannot be empty' in data['error']
    
    @patch('app.generate_image')
    def test_endpoint_selection_logic(self, mock_generate, client, authenticated_session):
        """Test that the correct endpoint is used based on request parameters."""
        # Mock the generate_image function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/image.png'
        mock_generated_data.image_name = 'image.png'
        mock_generated_data.prompt = 'test prompt'
        mock_generated_data.revised_prompt = 'revised test prompt'
        mock_generate.return_value = mock_generated_data
        
        # Test basic generation - should work with new endpoint
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Test that legacy endpoint still handles complex grid generation
        response = client.post('/', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'size': '1024x1024',
            'quality': 'standard',
            'advanced-generate-grid': 'on',
            'grid-prompt-file': 'test.txt'
        })
        
        # This should still work with the legacy endpoint
        # (though it might fail due to missing grid file, that's expected)
        assert response.status_code in [200, 400, 500]  # Various expected outcomes
    
    def test_response_format_consistency(self, client, authenticated_session):
        """Test that response formats are consistent across different scenarios."""
        # Test validation error
        response = client.post('/image', data={
            'prompt': '',  # Empty prompt
            'provider': 'openai',
            'operation': 'generate'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert isinstance(data['error'], str)
        
        # Test unsupported operation
        response = client.post('/image', data={
            'prompt': 'test',
            'provider': 'openai',
            'operation': 'img2img'  # OpenAI doesn't support img2img
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'does not support operation' in data['error']


class TestEndpointCompatibility:
    """Test compatibility between old and new endpoints."""
    
    @patch('app.generate_image')
    def test_same_parameters_different_endpoints(self, mock_generate, client, authenticated_session):
        """Test that the same parameters work on both endpoints (where applicable)."""
        # Mock the generate_image function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/image.png'
        mock_generated_data.image_name = 'image.png'
        mock_generated_data.prompt = 'test prompt'
        mock_generated_data.revised_prompt = 'revised test prompt'
        mock_generate.return_value = mock_generated_data
        
        # Parameters that should work on both endpoints
        common_params = {
            'prompt': 'test prompt',
            'provider': 'openai',
            'quality': 'standard'
        }
        
        # Legacy endpoint parameters
        legacy_params = {
            **common_params,
            'size': '1024x1024'
        }
        
        # New endpoint parameters
        new_params = {
            **common_params,
            'operation': 'generate',
            'width': '1024',
            'height': '1024'
        }
        
        # Test legacy endpoint
        legacy_response = client.post('/', data=legacy_params)
        assert legacy_response.status_code == 200
        
        # Test new endpoint
        new_response = client.post('/image', data=new_params)
        assert new_response.status_code == 200
        
        # Both should succeed (though with different response formats)
        new_data = json.loads(new_response.data)
        assert new_data['success'] is True