"""
Integration test to verify seed functionality works end-to-end.
"""

import pytest
from unittest.mock import Mock, patch
import json


class TestSeedIntegration:
    """Integration tests for seed functionality."""

    @patch('app.session', {'username': 'testuser'})
    @patch('app.generate_novelai_image')
    def test_seed_passed_through_image_endpoint(self, mock_generate, client):
        """Test that seed from form is passed through to generation function."""
        
        # Create a simple object instead of Mock to avoid JSON serialization issues
        class MockGeneratedData:
            def __init__(self):
                self.local_image_path = '/path/to/image.png'
                self.image_name = 'image.png'
                self.revised_prompt = 'revised test prompt'
        
        mock_generate.return_value = MockGeneratedData()
        
        # Test with specific seed
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'novelai',
            'operation': 'generate',
            'seed': '12345',
            'size': '1024x1024'
        })
        
        # Verify the request was successful
        assert response.status_code == 200
        
        # Verify the generation function was called with the correct seed
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args[1]['seed'] == 12345
        
        # Verify response contains expected data
        response_data = json.loads(response.data)
        assert response_data['success'] == True
        assert response_data['image_path'] == '/path/to/image.png'

    @patch('app.session', {'username': 'testuser'})
    @patch('app.generate_novelai_image')
    @patch('app.generate_seed_for_provider')
    def test_seed_generation_when_zero(self, mock_generate_seed, mock_generate, client):
        """Test that seed is generated when set to 0."""
        
        mock_generate_seed.return_value = 99999
        
        # Create a simple object instead of Mock to avoid JSON serialization issues
        class MockGeneratedData:
            def __init__(self):
                self.local_image_path = '/path/to/image.png'
                self.image_name = 'image.png'
                self.revised_prompt = 'revised test prompt'
        
        mock_generate.return_value = MockGeneratedData()
        
        # Test with seed = 0 (should generate random seed)
        response = client.post('/image', data={
            'prompt': 'test prompt',
            'provider': 'novelai',
            'operation': 'generate',
            'seed': '0',
            'size': '1024x1024'
        })
        
        # Verify the request was successful
        assert response.status_code == 200
        
        # Verify seed generation was called
        mock_generate_seed.assert_called_once_with('novelai')
        
        # Verify the generation function was called with the generated seed
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args[1]['seed'] == 99999

    @patch('app.session', {'username': 'testuser'})
    @patch('app.generate_novelai_inpaint_image')
    @patch('os.path.exists')
    def test_seed_in_inpainting_request(self, mock_exists, mock_inpaint, client):
        """Test that seed is passed through in inpainting requests."""
        
        # Mock file existence checks
        mock_exists.return_value = True
        
        # Mock the inpainting function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/inpainted.png'
        mock_generated_data.image_name = 'inpainted.png'
        mock_generated_data.revised_prompt = None
        mock_inpaint.return_value = mock_generated_data
        
        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'fake_image_data'
            
            response = client.post('/image', data={
                'prompt': 'inpaint this',
                'provider': 'novelai',
                'operation': 'inpaint',
                'seed': '54321',
                'base_image_path': '/path/to/base.png',
                'mask_path': '/path/to/mask.png'
            })
        
        # Verify the request was successful
        assert response.status_code == 200
        
        # Verify the inpainting function was called with the correct seed
        mock_inpaint.assert_called_once()
        call_args = mock_inpaint.call_args
        assert call_args[1]['seed'] == 54321

    @patch('app.session', {'username': 'testuser'})
    @patch('app.generate_novelai_img2img_image')
    def test_seed_in_img2img_request(self, mock_img2img, client):
        """Test that seed is passed through in img2img requests."""
        
        # Mock the img2img function
        mock_generated_data = Mock()
        mock_generated_data.local_image_path = '/path/to/img2img.png'
        mock_generated_data.image_name = 'img2img.png'
        mock_generated_data.revised_prompt = None
        mock_img2img.return_value = mock_generated_data
        
        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'fake_image_data'
            
            response = client.post('/image', data={
                'prompt': 'transform this',
                'provider': 'novelai',
                'operation': 'img2img',
                'seed': '77777',
                'base_image_path': '/path/to/base.png',
                'strength': '0.8'
            })
        
        # Verify the request was successful
        assert response.status_code == 200
        
        # Verify the img2img function was called with the correct seed
        mock_img2img.assert_called_once()
        call_args = mock_img2img.call_args
        assert call_args[1]['seed'] == 77777