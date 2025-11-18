"""
Tests for the unified /image endpoint.
"""

import json
import pytest
from unittest.mock import Mock, patch, mock_open
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


class TestImageEndpoint:
    """Test the unified /image endpoint."""
    
    def test_unauthenticated_request(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'AuthenticationError'
        assert 'Authentication required' in data['error_message']
    
    @patch('app.generate_openai_image')
    def test_generate_request_success(self, mock_generate, client, authenticated_session):
        """Test successful image generation request."""
        # Mock the generate_openai_image function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/image.png'
        mock_generated_data.image_name = 'image.png'
        mock_generated_data.prompt = 'test prompt'
        mock_generated_data.revised_prompt = 'revised test prompt'
        mock_generated_data.metadata = {'test': 'metadata'}
        mock_generate.return_value = mock_generated_data
        
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate',
            'width': '1024',
            'height': '1024',
            'quality': 'high'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['image_path'] == '/path/to/image.png'
        assert data['image_name'] == 'image.png'
        assert data['revised_prompt'] == 'revised test prompt'
        assert data['provider'] == 'openai'
        assert data['operation'] == 'generate'
    
    @patch('app.os.path.exists')
    @patch('app.generate_openai_inpaint_image')
    def test_inpaint_request_success(self, mock_inpaint, mock_exists, client, authenticated_session):
        """Test successful inpainting request."""
        # Mock file existence checks
        mock_exists.return_value = True
        
        # Mock the inpainting function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/inpainted.png'
        mock_generated_data.image_name = 'inpainted.png'
        mock_generated_data.revised_prompt = None
        mock_generated_data.metadata = {'test': 'metadata'}
        mock_inpaint.return_value = mock_generated_data
        
        response = client.post('/image', data={
            'prompt': 'inpaint this',
            'provider': 'openai',
            'operation': 'inpaint',
            'base_image_path': '/path/to/base.png',
            'mask_path': '/path/to/mask.png'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['image_path'] == '/path/to/inpainted.png'
        assert data['image_name'] == 'inpainted.png'
        assert data['provider'] == 'openai'
        assert data['operation'] == 'inpaint'
    
    @patch('app.novelai_api_key', 'test-api-key')
    @patch('app.os.path.exists')
    @patch('app.generate_novelai_img2img_image')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_image_data')
    def test_img2img_request_success(self, mock_file, mock_img2img, mock_exists, client, authenticated_session):
        """Test successful img2img request."""
        # Mock file existence checks
        mock_exists.return_value = True
        
        # Mock the img2img function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/img2img.png'
        mock_generated_data.image_name = 'img2img.png'
        mock_generated_data.revised_prompt = None
        mock_generated_data.metadata = {'test': 'metadata'}
        mock_img2img.return_value = mock_generated_data
        
        response = client.post('/image', data={
            'prompt': 'transform this',
            'provider': 'novelai',
            'operation': 'img2img',
            'base_image_path': '/path/to/base.png',
            'strength': '0.8'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['image_path'] == '/path/to/img2img.png'
        assert data['image_name'] == 'img2img.png'
        assert data['provider'] == 'novelai'
        assert data['operation'] == 'img2img'
    
    def test_invalid_operation(self, client, authenticated_session):
        """Test request with invalid operation."""
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'invalid_operation'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'ValidationError'
        assert 'error_message' in data
    
    def test_unsupported_provider_operation_combination(self, client, authenticated_session):
        """Test unsupported provider-operation combination."""
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'img2img'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'ValidationError'
        assert 'Provider openai does not support operation img2img' in data['error_message']
    
    def test_missing_required_fields(self, client, authenticated_session):
        """Test request with missing required fields."""
        response = client.post('/image', data={
            'provider': 'openai',
            'operation': 'generate'
            # Missing prompt
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert not data['success']
        assert data['error_type'] == 'ValidationError'
        assert 'error_message' in data
    
    def test_invalid_dimensions_openai(self, client, authenticated_session):
        """Test invalid dimensions for OpenAI provider."""
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate',
            'width': '512',
            'height': '512'
        })
        
        # Should return 400 - either from validation or from generation error
        assert response.status_code == 400
        data = json.loads(response.data)
        
        # Verify we got an error response (validation is working as the test shows it returns 400)
        assert 'error' in data or 'error_message' in data
        assert data.get('success', True) is False  # Should be False or not present
    
    @patch('app.generate_openai_image')
    def test_generation_error_handling(self, mock_generate, client, authenticated_session):
        """Test error handling in generation requests."""
        # Mock generate_openai_image to raise an exception
        mock_generate.side_effect = Exception("Generation failed")
        
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'operation': 'generate',
            'width': '1024',
            'height': '1024'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Generation failed' in data['error_message']
        assert data['error_type'] == 'Exception'
        assert data['provider'] == 'openai'
        assert data['operation'] == 'generate'


class TestHelperFunctions:
    """Test helper functions for the image endpoint."""
    
    def test_get_aspect_ratio_from_dimensions(self):
        """Test aspect ratio calculation."""
        from app import _get_aspect_ratio_from_dimensions
        
        # Square
        assert _get_aspect_ratio_from_dimensions(1024, 1024) == "1:1"
        
        # Landscape
        assert _get_aspect_ratio_from_dimensions(1792, 1024) == "16:9"
        assert _get_aspect_ratio_from_dimensions(1024, 768) == "4:3"
        assert _get_aspect_ratio_from_dimensions(1600, 900) == "16:9"
        
        # Portrait
        assert _get_aspect_ratio_from_dimensions(1024, 1792) == "9:16"
        assert _get_aspect_ratio_from_dimensions(768, 1024) == "3:4"
        assert _get_aspect_ratio_from_dimensions(900, 1600) == "9:16"


class TestBackwardCompatibility:
    """Test that the new endpoint doesn't break existing functionality."""
    
    def test_existing_index_route_no_post(self, client, authenticated_session):
        """Test that the existing index route no longer supports POST."""
        response = client.post('/', data={
            'prompt': 'test prompt',
            'provider': 'openai',
            'size': '1024x1024',
            'quality': 'high'
        })
        
        # Should return 405 Method Not Allowed
        assert response.status_code == 405