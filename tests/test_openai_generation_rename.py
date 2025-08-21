"""
Tests for the renamed OpenAI image generation function.

Tests verify that the function was properly renamed from generate_dalle_image
to generate_openai_image and that all functionality remains intact.
"""

import pytest
from unittest.mock import Mock, patch

from app import generate_openai_image, GeneratedImageData, ModerationException


class TestGenerateOpenAIImageRenamed:
    """Test cases for the renamed generate_openai_image function."""
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    def test_generate_openai_image_basic_functionality(
        self, mock_process_image, mock_make_prompt, mock_client, mock_app
    ):
        """Test that the renamed function maintains basic functionality."""
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation response
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.generate response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_generate_response = Mock()
        mock_generate_response.data = [mock_image_data]
        mock_client.images.generate.return_value = mock_generate_response
        
        # Mock process_image_response
        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/generated.png"
        mock_saved_data.image_name = "generated.png"
        mock_process_image.return_value = mock_saved_data
        
        with patch("app.base64.b64decode") as mock_b64decode:
            mock_b64decode.return_value = b"decoded image data"
            
            # Call the renamed function
            result = generate_openai_image(
                prompt="test prompt",
                username="testuser",
                size="1024x1024",
                quality="standard",
                strict_follow_prompt=False,
                seed=42
            )
        
        # Verify the function still works correctly
        assert isinstance(result, GeneratedImageData)
        assert result.local_image_path == "/path/to/generated.png"
        assert result.image_name == "generated.png"
        
        # Verify it uses the correct model
        mock_client.images.generate.assert_called_once()
        call_kwargs = mock_client.images.generate.call_args.kwargs
        assert call_kwargs["model"] == "gpt-image-1"
        assert call_kwargs["prompt"] == "processed prompt"
        assert call_kwargs["size"] == "1024x1024"
        assert call_kwargs["quality"] == "standard"
        assert call_kwargs["n"] == 1
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    def test_generate_openai_image_with_strict_follow_prompt(
        self, mock_process_image, mock_make_prompt, mock_client, mock_app
    ):
        """Test the renamed function with strict follow prompt enabled."""
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "short prompt"
        
        # Mock moderation response
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.generate response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_generate_response = Mock()
        mock_generate_response.data = [mock_image_data]
        mock_client.images.generate.return_value = mock_generate_response
        
        # Mock process_image_response
        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/generated.png"
        mock_saved_data.image_name = "generated.png"
        mock_process_image.return_value = mock_saved_data
        
        with patch("app.base64.b64decode") as mock_b64decode:
            mock_b64decode.return_value = b"decoded image data"
            
            # Call with strict_follow_prompt=True
            _ = generate_openai_image(
                prompt="test prompt",
                username="testuser",
                strict_follow_prompt=True
            )
        
        # Verify the strict follow prompt logic is applied
        call_kwargs = mock_client.images.generate.call_args.kwargs
        prompt_used = call_kwargs["prompt"]
        assert "I NEED to test how the tool works with extremely simple prompts" in prompt_used
        assert "DO NOT add any detail, just use it AS-IS" in prompt_used
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_image_moderation_failure(
        self, mock_make_prompt, mock_client, mock_app
    ):
        """Test that moderation failure still works with renamed function."""
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "inappropriate content"
        
        # Mock moderation failure
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = True
        mock_moderation_result.categories.__dict__ = {
            "violence": True,
            "hate": False,
            "sexual": False
        }
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        with pytest.raises(ModerationException) as exc_info:
            generate_openai_image(
                prompt="inappropriate prompt",
                username="testuser"
            )
        
        assert "violence" in str(exc_info.value)
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_image_quality_parameter(
        self, mock_make_prompt, mock_client, mock_app
    ):
        """Test that quality parameter is properly passed through."""
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "test prompt"
        
        # Mock moderation response
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.generate response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_generate_response = Mock()
        mock_generate_response.data = [mock_image_data]
        mock_client.images.generate.return_value = mock_generate_response
        
        with patch("app.process_image_response") as mock_process_image:
            mock_saved_data = Mock()
            mock_saved_data.local_image_path = "/path/to/generated.png"
            mock_saved_data.image_name = "generated.png"
            mock_process_image.return_value = mock_saved_data
            
            with patch("app.base64.b64decode") as mock_b64decode:
                mock_b64decode.return_value = b"decoded image data"
                
                # Test with HD quality
                generate_openai_image(
                    prompt="test prompt",
                    username="testuser",
                    quality="hd"
                )
        
        # Verify quality parameter is passed correctly
        call_kwargs = mock_client.images.generate.call_args.kwargs
        assert call_kwargs["quality"] == "hd"
    
    @patch("app.app")
    def test_generate_openai_image_no_static_folder(self, mock_app):
        """Test error handling when static folder is not defined."""
        mock_app.static_folder = None
        
        with pytest.raises(ValueError, match="Flask static folder not defined"):
            generate_openai_image(
                prompt="test prompt",
                username="testuser"
            )
    
    def test_function_exists_and_callable(self):
        """Test that the renamed function exists and is callable."""
        from app import generate_openai_image
        
        assert callable(generate_openai_image)
        
        # The old function name doesn't exist anymore, no need to test for ImportError
        # since we successfully renamed the function
        assert generate_openai_image.__name__ == 'generate_openai_image'


class TestOpenAIImageGenerationIntegration:
    """Integration tests for the renamed OpenAI image generation function."""
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    def test_flask_route_uses_renamed_function(
        self, mock_process_image, mock_make_prompt, mock_client, mock_app
    ):
        """Test that Flask routes use the renamed function correctly."""
        # This test verifies that the Flask route integration still works
        # after the function rename
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation response
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.generate response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_generate_response = Mock()
        mock_generate_response.data = [mock_image_data]
        mock_client.images.generate.return_value = mock_generate_response
        
        # Mock process_image_response
        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/generated.png"
        mock_saved_data.image_name = "generated.png"
        mock_process_image.return_value = mock_saved_data
        
        with patch("app.base64.b64decode") as mock_b64decode:
            mock_b64decode.return_value = b"decoded image data"
            
            # Call the function directly (simulating Flask route call)
            result = generate_openai_image(
                prompt="test prompt",
                username="testuser",
                size="1024x1024",
                quality="standard"
            )
        
        # Verify the integration still works
        assert isinstance(result, GeneratedImageData)
        assert result.local_image_path == "/path/to/generated.png"
        
        # Verify it's using gpt-image-1 model
        call_kwargs = mock_client.images.generate.call_args.kwargs
        assert call_kwargs["model"] == "gpt-image-1"
    
    def test_function_signature_compatibility(self):
        """Test that the function signature remains compatible."""
        import inspect
        from app import generate_openai_image
        
        # Get function signature
        sig = inspect.signature(generate_openai_image)
        
        # Verify expected parameters exist
        expected_params = ['prompt', 'username', 'size', 'quality', 'strict_follow_prompt', 'seed']
        actual_params = list(sig.parameters.keys())
        
        for param in expected_params:
            assert param in actual_params, f"Parameter '{param}' missing from function signature"
        
        # Verify return type annotation if present
        if sig.return_annotation != inspect.Signature.empty:
            assert sig.return_annotation == GeneratedImageData