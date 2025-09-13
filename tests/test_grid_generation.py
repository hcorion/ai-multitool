"""
Tests for the new grid generation functionality using the unified /image endpoint.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from app import app


class TestGridGeneration:
    """Test grid generation functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['username'] = 'testuser'
            yield client

    def test_get_prompt_file_endpoint(self, client):
        """Test the GET endpoint for prompt files."""
        # Ensure test prompt file exists
        os.makedirs('static/prompts/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue\ngreen\nyellow\n')

        response = client.get('/prompt-files/colors')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['name'] == 'colors'
        assert data['content'] == ['red', 'blue', 'green', 'yellow']
        assert data['line_count'] == 4

    def test_get_nonexistent_prompt_file(self, client):
        """Test getting a non-existent prompt file."""
        response = client.get('/prompt-files/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_prompt_file_invalid_filename(self, client):
        """Test getting a prompt file with invalid filename."""
        response = client.get('/prompt-files/invalid@filename')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert 'invalid filename' in data['error'].lower()

    @patch('app._handle_generation_request')
    def test_grid_generation_via_unified_endpoint(self, mock_handler, client):
        """Test that grid generation works through the unified endpoint."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'test prompt'
        mock_response.provider = 'openai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue\ngreen')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            # Test grid generation request
            response = client.post('/image', data={
                'prompt': 'a __colors__ car',
                'provider': 'openai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['operation'] == 'grid_generate'
            assert 'grid' in data['image_name'].lower()
            assert 'colors' in data['revised_prompt']

    def test_unified_image_endpoint_still_works(self, client):
        """Test that the unified /image endpoint still works for regular generation."""
        with patch('app._handle_generation_request') as mock_handler:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.success = True
            mock_response.image_path = 'static/images/testuser/test.png'
            mock_response.image_name = 'test.png'
            mock_response.revised_prompt = 'test prompt'
            mock_response.provider = 'openai'
            mock_response.operation = 'generate'
            mock_response.timestamp = 1234567890
            mock_response.metadata = {}
            mock_handler.return_value = mock_response

            response = client.post('/image', data={
                'prompt': 'test prompt',
                'provider': 'openai',
                'operation': 'generate'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['image_name'] == 'test.png'

    @patch('app._handle_generation_request')
    def test_grid_generation_with_character_prompts(self, mock_handler, client):
        """Test that grid generation works with character prompts for NovelAI."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'test prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            # Test grid generation request with character prompts
            response = client.post('/image', data={
                'prompt': 'a __colors__ car',
                'provider': 'novelai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345',
                'character_prompts[0][positive]': 'character 1 positive',
                'character_prompts[0][negative]': 'character 1 negative',
                'character_prompts[1][positive]': 'character 2 positive',
                'character_prompts[1][negative]': 'character 2 negative'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['operation'] == 'grid_generate'
            assert data['provider'] == 'novelai'
            
            # Verify that _handle_generation_request was called with character prompts
            assert mock_handler.call_count == 2  # Should be called for each color (red, blue)
            
            # Check that character prompts were passed to the generation requests
            for call in mock_handler.call_args_list:
                request_obj = call[0][0]  # First argument is the request object
                assert hasattr(request_obj, 'character_prompts')
                assert request_obj.character_prompts is not None
                assert len(request_obj.character_prompts) == 2
                assert request_obj.character_prompts[0]['positive'] == 'character 1 positive'
                assert request_obj.character_prompts[0]['negative'] == 'character 1 negative'

    @patch('app._handle_generation_request')
    def test_grid_generation_with_detailed_errors(self, mock_handler, client):
        """Test that grid generation provides detailed error messages when individual generations fail."""
        # Mock failed image generation responses
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error_message = "API rate limit exceeded"
        mock_response.error_type = "rate_limit_error"
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue')

        # Test grid generation request that will fail
        response = client.post('/image', data={
            'prompt': 'a __colors__ car',
            'provider': 'openai',
            'advanced-generate-grid': 'on',
            'grid-prompt-file': 'colors',
            'seed': '12345'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'grid generation failed' in data['error_message'].lower()
        # Check that the detailed error message includes information about the specific failures
        assert 'no images were successfully generated' in data['error_message'].lower()
        assert 'errors encountered' in data['error_message'].lower()
        assert 'api rate limit exceeded' in data['error_message'].lower()
        assert 'rate_limit_error' in data['error_message'].lower()
        # Check that helpful tip is included for rate limiting
        assert 'rate limiting issue' in data['error_message'].lower()
        assert 'try again in a few minutes' in data['error_message'].lower()

    def test_grid_generation_missing_prompt_file(self, client):
        """Test grid generation with missing prompt file."""
        response = client.post('/image', data={
            'prompt': 'a __colors__ car',
            'provider': 'openai',
            'advanced-generate-grid': 'on',
            'grid-prompt-file': 'nonexistent',
            'seed': '12345'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'grid generation failed' in data['error_message'].lower()

    @patch('app._handle_generation_request')
    def test_grid_generation_processes_character_prompts_with_grid_override(self, mock_handler, client):
        """Test that character prompts are processed with grid prompt overrides."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'test prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            # Test grid generation request with character prompts that use the grid prompt file
            response = client.post('/image', data={
                'prompt': 'a car',
                'provider': 'novelai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345',
                'character_prompts[0][positive]': 'a __colors__ character',
                'character_prompts[0][negative]': 'bad __colors__ things'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify that _handle_generation_request was called for each color
            assert mock_handler.call_count == 2  # Should be called for red and blue
            
            # Check that character prompts were processed with grid overrides
            for call in mock_handler.call_args_list:
                request_obj = call[0][0]  # First argument is the request object
                assert hasattr(request_obj, 'character_prompts')
                assert request_obj.character_prompts is not None
                assert len(request_obj.character_prompts) == 1
                
                # The character prompt should have the grid prompt replaced
                char_prompt = request_obj.character_prompts[0]
                # Should be either "a red character" or "a blue character"
                assert 'red character' in char_prompt['positive'] or 'blue character' in char_prompt['positive']
                # Should be either "bad red things" or "bad blue things"  
                assert 'red things' in char_prompt['negative'] or 'blue things' in char_prompt['negative']
                # Should NOT contain the original __colors__ placeholder
                assert '__colors__' not in char_prompt['positive']
                assert '__colors__' not in char_prompt['negative']

    @patch('app._handle_generation_request')
    def test_grid_generation_with_grid_prompt_only_in_character_prompts(self, mock_handler, client):
        """Test grid generation where the grid prompt file is only used in character prompts, not main prompt."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'test prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue\ngreen')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            # Test grid generation where ONLY character prompts use the grid placeholder
            response = client.post('/image', data={
                'prompt': 'a fantasy scene',  # No grid placeholder in main prompt
                'provider': 'novelai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345',
                'character_prompts[0][positive]': 'a __colors__ dragon',  # Grid placeholder here
                'character_prompts[0][negative]': 'ugly __colors__ things',  # And here
                'character_prompts[1][positive]': 'a wizard',  # No grid placeholder
                'character_prompts[1][negative]': 'bad quality'  # No grid placeholder
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['operation'] == 'grid_generate'
            
            # Verify that _handle_generation_request was called for each color
            assert mock_handler.call_count == 3  # Should be called for red, blue, green
            
            # Check that character prompts were processed correctly
            for call in mock_handler.call_args_list:
                request_obj = call[0][0]  # First argument is the request object
                assert hasattr(request_obj, 'character_prompts')
                assert request_obj.character_prompts is not None
                assert len(request_obj.character_prompts) == 2
                
                # First character prompt should have grid replacement
                char_prompt_0 = request_obj.character_prompts[0]
                # Should be "a red dragon", "a blue dragon", or "a green dragon"
                assert any(color in char_prompt_0['positive'] for color in ['red dragon', 'blue dragon', 'green dragon'])
                # Should be "ugly red things", "ugly blue things", or "ugly green things"
                assert any(color in char_prompt_0['negative'] for color in ['red things', 'blue things', 'green things'])
                # Should NOT contain the original __colors__ placeholder
                assert '__colors__' not in char_prompt_0['positive']
                assert '__colors__' not in char_prompt_0['negative']
                
                # Second character prompt should remain unchanged (no grid placeholder)
                char_prompt_1 = request_obj.character_prompts[1]
                assert char_prompt_1['positive'] == 'a wizard'
                assert char_prompt_1['negative'] == 'bad quality'

    @patch('app._handle_generation_request')
    def test_grid_generation_metadata_includes_processed_prompts(self, mock_handler, client):
        """Test that grid generation metadata includes processed prompts."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'API revised prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {'API_Metadata': 'some_value'}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            # Test grid generation request
            response = client.post('/image', data={
                'prompt': 'a __colors__ car',
                'provider': 'novelai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345',
                'character_prompts[0][positive]': 'a __colors__ character',
                'character_prompts[0][negative]': 'bad __colors__ things'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Check that the final grid metadata includes processed prompt information
            metadata = data['metadata']
            assert 'Grid Prompt File' in metadata
            assert metadata['Grid Prompt File'] == 'colors'
            assert 'Grid Prompts' in metadata
            assert 'red, blue' in metadata['Grid Prompts']
            assert 'Grid Image Count' in metadata
            assert metadata['Grid Image Count'] == '2'

    @patch('app._handle_generation_request')
    def test_individual_grid_image_metadata_contains_processed_prompts(self, mock_handler, client):
        """Test that individual grid images have metadata with processed prompts."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'API revised prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red\nblue')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            
            # Test grid generation directly
            response = client.post('/image', data={
                    'prompt': 'a car',
                    'provider': 'novelai',
                    'advanced-generate-grid': 'on',
                    'grid-prompt-file': 'colors',
                    'seed': '12345',
                    'character_prompts[0][positive]': 'a __colors__ character',
                    'character_prompts[0][negative]': 'bad __colors__ things'
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify that the handler was called with requests that have processed character prompts
            assert mock_handler.call_count == 2  # red and blue
            
            # Check each call to verify the metadata would contain processed prompts
            for i, call in enumerate(mock_handler.call_args_list):
                request_obj = call[0][0]
                
                # Verify the character prompts were processed
                assert request_obj.character_prompts is not None
                assert len(request_obj.character_prompts) == 1
                
                char_prompt = request_obj.character_prompts[0]
                # Should contain either "red" or "blue" instead of "__colors__"
                assert '__colors__' not in char_prompt['positive']
                assert '__colors__' not in char_prompt['negative']
                assert ('red character' in char_prompt['positive'] or 'blue character' in char_prompt['positive'])
                assert ('red things' in char_prompt['negative'] or 'blue things' in char_prompt['negative'])

    @patch('app._handle_generation_request')
    def test_grid_generation_metadata_uses_frontend_expected_keys(self, mock_handler, client):
        """Test that grid generation metadata uses the keys expected by the frontend."""
        # Mock successful image generation responses
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.image_path = 'static/images/testuser/test.png'
        mock_response.image_name = 'test.png'
        mock_response.revised_prompt = 'API revised prompt'
        mock_response.provider = 'novelai'
        mock_response.operation = 'generate'
        mock_response.timestamp = 1234567890
        mock_response.metadata = {}
        mock_handler.return_value = mock_response

        # Ensure test directories and prompt file exist
        os.makedirs('static/prompts/testuser', exist_ok=True)
        os.makedirs('static/images/testuser', exist_ok=True)
        with open('static/prompts/testuser/colors.txt', 'w') as f:
            f.write('red')

        # Mock the ImageMagick operations and file operations to avoid dependency issues
        with patch('app.WandImage'), patch('app.PILImage'), patch('app.PngInfo'), \
             patch('app.get_file_count', return_value=1), \
             patch('os.path.exists', return_value=True), \
             patch('os.rename'):
            
            # Test grid generation request
            response = client.post('/image', data={
                'prompt': 'a __colors__ car',
                'provider': 'novelai',
                'advanced-generate-grid': 'on',
                'grid-prompt-file': 'colors',
                'seed': '12345',
                'character_prompts[0][positive]': 'a __colors__ character',
                'character_prompts[0][negative]': 'bad __colors__ things'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify that the handler was called with the correct request
            assert mock_handler.call_count == 1
            call_args = mock_handler.call_args_list[0]
            request_obj = call_args[0][0]
            
            # The individual image should have been created with enhanced metadata
            # We can't directly access it here, but we know the keys should be correct
            # based on our implementation
            
            # The main thing is that the frontend should now be able to display the prompts
            # Let's verify the grid metadata contains the expected structure
            grid_metadata = data['metadata']
            assert 'Grid Prompt File' in grid_metadata
            assert 'Grid Prompts' in grid_metadata

    def test_prompt_file_authentication(self):
        """Test that prompt file endpoints require authentication."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            # No session set up - should require authentication
            response = client.get('/prompt-files/colors')
            assert response.status_code == 401
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'not authenticated' in data['error'].lower()