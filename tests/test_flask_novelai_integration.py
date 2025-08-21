"""
Tests for Flask route integration with the refactored generate_novelai_image function.

Tests verify that the Flask routes correctly call the refactored function
and handle responses appropriately.
"""

import pytest
from unittest.mock import Mock, patch

from app import app, GeneratedImageData


class TestFlaskNovelAIIntegration:
    """Test cases for Flask route integration with NovelAI generation."""

    @pytest.fixture
    def client(self):
        """Flask test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def logged_in_session(self, client):
        """Create a logged-in session for testing."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'

    @patch("app.generate_novelai_image")
    def test_index_post_novelai_basic(self, mock_generate_novelai, client, logged_in_session):
        """Test basic NovelAI image generation through Flask route."""
        # Setup mock
        mock_generate_novelai.return_value = GeneratedImageData(
            local_image_path="/static/images/testuser/001-test.png",
            revised_prompt="revised test prompt",
            prompt="test prompt",
            image_name="001-test.png"
        )

        # Make request
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
            'size': '512x768',
            'seed': '42',
            'negative_prompt': 'avoid this',
        })

        # Verify response
        assert response.status_code == 200
        assert b"001-test.png" in response.data
        assert b"revised test prompt" in response.data

        # Verify generate_novelai_image was called correctly
        mock_generate_novelai.assert_called_once_with(
            prompt="test prompt",
            negative_prompt="avoid this",
            username="testuser",
            size=(512, 768),
            seed=42,
            upscale=False,
            grid_dynamic_prompt=None,
            character_prompts=[]
        )

    @patch("app.generate_novelai_image")
    def test_index_post_novelai_with_upscale(self, mock_generate_novelai, client, logged_in_session):
        """Test NovelAI image generation with upscaling through Flask route."""
        # Setup mock
        mock_generate_novelai.return_value = GeneratedImageData(
            local_image_path="/static/images/testuser/002-upscaled.png",
            revised_prompt="upscaled prompt",
            prompt="upscale test",
            image_name="002-upscaled.png"
        )

        # Make request with upscale enabled
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'upscale test',
            'size': '1024x1024',
            'upscale': 'on',  # HTML checkbox sends 'on' when checked
        })

        # Verify response
        assert response.status_code == 200

        # Verify generate_novelai_image was called with upscale=True
        mock_generate_novelai.assert_called_once()
        call_args = mock_generate_novelai.call_args
        assert call_args.kwargs['upscale'] is True

    @patch("app._extract_character_prompts_from_form")
    @patch("app.generate_novelai_image")
    def test_index_post_novelai_with_character_prompts(
        self, mock_generate_novelai, mock_extract_char_prompts, client, logged_in_session
    ):
        """Test NovelAI image generation with character prompts through Flask route."""
        # Setup mocks
        mock_extract_char_prompts.return_value = [
            {"positive": "character 1", "negative": "avoid 1"},
            {"positive": "character 2", "negative": ""}
        ]
        
        mock_generate_novelai.return_value = GeneratedImageData(
            local_image_path="/static/images/testuser/003-chars.png",
            revised_prompt="character prompt test",
            prompt="test with characters",
            image_name="003-chars.png"
        )

        # Make request
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test with characters',
            'size': '512x512',
            # Character prompts would be extracted from form by _extract_character_prompts_from_form
        })

        # Verify response
        assert response.status_code == 200

        # Verify character prompts were extracted and passed
        mock_extract_char_prompts.assert_called_once()
        mock_generate_novelai.assert_called_once()
        call_args = mock_generate_novelai.call_args
        assert call_args.kwargs['character_prompts'] == [
            {"positive": "character 1", "negative": "avoid 1"},
            {"positive": "character 2", "negative": ""}
        ]

    @patch("app.generate_novelai_image")
    def test_index_post_novelai_error_handling(self, mock_generate_novelai, client, logged_in_session):
        """Test error handling in Flask route when NovelAI generation fails."""
        # Setup mock to raise an exception
        mock_generate_novelai.side_effect = Exception("NovelAI Generate Image 400: Bad request")

        # Make request
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
            'size': '512x512',
        })

        # Verify error response
        assert response.status_code == 200  # Flask still returns 200 but with error message
        assert b"NovelAI Generate Image 400: Bad request" in response.data

    def test_index_post_novelai_no_session(self, client):
        """Test that requests without session are redirected to login."""
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
            'size': '512x512',
        })

        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location

    @patch("app.generate_novelai_image")
    def test_index_post_novelai_missing_prompt(self, mock_generate_novelai, client, logged_in_session):
        """Test error handling when prompt is missing."""
        # Make request without prompt
        response = client.post('/', data={
            'provider': 'novelai',
            'size': '512x512',
        })

        # Verify error response
        assert response.status_code == 200
        assert b"Please provide a prompt!" in response.data

        # Verify generate_novelai_image was not called
        mock_generate_novelai.assert_not_called()

    @patch("app.generate_novelai_image")
    def test_index_post_novelai_missing_size(self, mock_generate_novelai, client, logged_in_session):
        """Test error handling when size is missing for NovelAI."""
        # Make request without size
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
        })

        # Verify error response
        assert response.status_code == 200
        assert b"Unable to get &#39;size&#39; field." in response.data

        # Verify generate_novelai_image was not called
        mock_generate_novelai.assert_not_called()

    @patch("app.generate_seed_for_provider")
    @patch("app.generate_novelai_image")
    def test_index_post_novelai_auto_seed(
        self, mock_generate_novelai, mock_generate_seed, client, logged_in_session
    ):
        """Test automatic seed generation when no seed provided."""
        # Setup mocks
        mock_generate_seed.return_value = 12345
        mock_generate_novelai.return_value = GeneratedImageData(
            local_image_path="/static/images/testuser/004-auto-seed.png",
            revised_prompt="auto seed test",
            prompt="test prompt",
            image_name="004-auto-seed.png"
        )

        # Make request without seed
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
            'size': '512x512',
        })

        # Verify response
        assert response.status_code == 200

        # Verify seed was generated and used
        mock_generate_seed.assert_called_once_with('novelai')
        mock_generate_novelai.assert_called_once()
        call_args = mock_generate_novelai.call_args
        assert call_args.kwargs['seed'] == 12345

    @patch("app.generate_image_grid")
    def test_index_post_novelai_grid_generation(self, mock_generate_grid, client, logged_in_session):
        """Test grid generation routing for NovelAI."""
        # Setup mock
        mock_generate_grid.return_value = GeneratedImageData(
            local_image_path="/static/images/testuser/grid-001.png",
            revised_prompt="grid test",
            prompt="test prompt",
            image_name="grid-001.png"
        )

        # Make request with grid generation enabled
        response = client.post('/', data={
            'provider': 'novelai',
            'prompt': 'test prompt',
            'size': '512x512',
            'advanced-generate-grid': 'on',
            'grid-prompt-file': 'test-prompts.txt',
        })

        # Verify response
        assert response.status_code == 200

        # Verify grid generation was called instead of regular generation
        mock_generate_grid.assert_called_once()
        call_args = mock_generate_grid.call_args
        assert call_args[0][:5] == ('novelai', 'test prompt', '512x512', None, 'test-prompts.txt')
        # The last argument should be the request object
        assert hasattr(call_args[0][5], 'form')  # Verify it's a request object


class TestGenerateImageFunction:
    """Test the generate_image function that routes to generate_novelai_image."""

    @patch("app.generate_novelai_image")
    @patch("app.generate_seed_for_provider")
    def test_generate_image_novelai_routing(self, mock_generate_seed, mock_generate_novelai):
        """Test that generate_image correctly routes NovelAI requests."""
        from app import generate_image
        from flask import Flask
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request

        # Setup mocks
        mock_generate_seed.return_value = 54321
        mock_generate_novelai.return_value = GeneratedImageData(
            local_image_path="/test/path.png",
            revised_prompt="revised",
            prompt="original",
            image_name="test.png"
        )

        # Create a mock request
        with Flask(__name__).test_request_context():
            builder = EnvironBuilder(method='POST', data={
                'negative_prompt': 'avoid this',
                'upscale': 'on',
            })
            request = Request(builder.get_environ())

            # Mock session
            with patch('app.session', {'username': 'testuser'}):
                result = generate_image(
                    provider='novelai',
                    prompt='test prompt',
                    size='1024x768',
                    request=request,
                    seed=None,  # Should trigger auto-generation
                )

        # Verify seed generation
        mock_generate_seed.assert_called_once_with('novelai')

        # Verify generate_novelai_image was called correctly
        mock_generate_novelai.assert_called_once_with(
            prompt='test prompt',
            negative_prompt='avoid this',
            username='testuser',
            size=(1024, 768),
            seed=54321,
            upscale=True,
            grid_dynamic_prompt=None,
            character_prompts=[]  # Should be extracted from form
        )

        # Verify result
        assert result.local_image_path == "/test/path.png"
        assert result.revised_prompt == "revised"
        assert result.prompt == "original"
        assert result.image_name == "test.png"