"""
Unit tests for OpenAI inpainting functionality.

Tests cover the generate_openai_inpaint_image function with mocked OpenAI API responses
and various error conditions.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch
from PIL import Image as PILImage

from app import generate_openai_inpaint_image, GeneratedImageData, ModerationException


class TestGenerateOpenAIInpaintImage:
    """Test cases for the generate_openai_inpaint_image function."""
    
    @pytest.fixture
    def temp_image_files(self):
        """Create temporary image files for testing."""
        # Create temporary base image
        base_image = PILImage.new('RGB', (512, 512), color='blue')
        base_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        base_temp.close()  # Close file handle before saving
        base_image.save(base_temp.name, 'PNG')
        
        # Create temporary mask image
        mask_image = PILImage.new('RGB', (512, 512), color='black')
        # Add white area for inpainting
        for x in range(200, 312):
            for y in range(200, 312):
                mask_image.putpixel((x, y), (255, 255, 255))
        mask_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        mask_temp.close()  # Close file handle before saving
        mask_image.save(mask_temp.name, 'PNG')
        
        yield base_temp.name, mask_temp.name
        
        # Cleanup
        try:
            os.unlink(base_temp.name)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows
        try:
            os.unlink(mask_temp.name)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    def test_generate_openai_inpaint_image_basic(
        self, mock_process_image, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test basic OpenAI inpainting functionality."""
        base_image_path, mask_path = temp_image_files
        
        # Setup mocks
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed inpaint prompt"
        
        # Mock moderation response
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.edit response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_edit_response = Mock()
        mock_edit_response.data = [mock_image_data]
        mock_client.images.edit.return_value = mock_edit_response
        
        # Mock process_image_response
        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/inpainted.png"
        mock_saved_data.image_name = "inpainted.png"
        mock_process_image.return_value = mock_saved_data
        
        with patch("app.base64.b64decode") as mock_b64decode:
            mock_b64decode.return_value = b"decoded image data"
            
            # Call the function
            result = generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="add a red flower",
                username="testuser",
                size="1024x1024",
                seed=42
            )
        
        # Verify moderation was called
        mock_client.moderations.create.assert_called_once_with(input="processed inpaint prompt")
        
        # Verify images.edit was called correctly
        mock_client.images.edit.assert_called_once()
        call_kwargs = mock_client.images.edit.call_args.kwargs
        assert call_kwargs["prompt"] == "processed inpaint prompt"
        assert call_kwargs["size"] == "1024x1024"
        assert call_kwargs["n"] == 1
        
        # Verify process_image_response was called with correct metadata
        mock_process_image.assert_called_once()
        call_args = mock_process_image.call_args[0]
        metadata = call_args[4]
        assert metadata["Prompt"] == "add a red flower"
        assert metadata["Operation"] == "inpaint"
        assert metadata["Provider"] == "openai"
        assert metadata["Size"] == "1024x1024"
        
        # Verify result
        assert isinstance(result, GeneratedImageData)
        assert result.local_image_path == "/path/to/inpainted.png"
        assert result.revised_prompt == "processed inpaint prompt"
        assert result.prompt == "add a red flower"
        assert result.image_name == "inpainted.png"
    
    @patch("app.app")
    def test_generate_openai_inpaint_image_no_static_folder(self, mock_app, temp_image_files):
        """Test error when Flask static folder is not defined."""
        base_image_path, mask_path = temp_image_files
        mock_app.static_folder = None
        
        with pytest.raises(ValueError, match="Flask static folder not defined"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    def test_generate_openai_inpaint_image_missing_base_image(self, mock_app):
        """Test error when base image file doesn't exist."""
        mock_app.static_folder = "/test/static"
        
        with pytest.raises(FileNotFoundError, match="Base image file not found"):
            generate_openai_inpaint_image(
                base_image_path="/nonexistent/base.png",
                mask_path="/fake/mask.png",
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    def test_generate_openai_inpaint_image_missing_mask(self, mock_app, temp_image_files):
        """Test error when mask file doesn't exist."""
        base_image_path, _ = temp_image_files
        mock_app.static_folder = "/test/static"
        
        with pytest.raises(FileNotFoundError, match="Mask image file not found"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path="/nonexistent/mask.png",
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_inpaint_image_moderation_failure(
        self, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test handling of moderation failure."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "inappropriate content"
        
        # Mock moderation failure
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = True
        mock_moderation_result.categories.__dict__ = {
            "violence": True,
            "hate": False,
            "sexual": True
        }
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        with pytest.raises(ModerationException) as exc_info:
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="inappropriate prompt",
                username="testuser"
            )
        
        assert "violence, sexual" in str(exc_info.value)
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_inpaint_image_api_bad_request(
        self, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test handling of OpenAI BadRequestError."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation success
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Create a real exception-like object
        from openai import BadRequestError
        error_response = Mock()
        error_response.content = json.dumps({
            "error": {
                "message": "Invalid image format",
                "code": "invalid_image"
            }
        }).encode()
        
        # Create a mock that behaves like BadRequestError
        mock_error = BadRequestError("Invalid image format", response=error_response, body=None)
        mock_client.images.edit.side_effect = mock_error
        
        with pytest.raises(Exception, match="OpenAI Inpainting Error invalid_image: Invalid image format"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_inpaint_image_content_policy_violation(
        self, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test handling of content policy violation."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation success
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Create a real exception-like object
        from openai import BadRequestError
        error_response = Mock()
        error_response.content = json.dumps({
            "error": {
                "message": "Content policy violation",
                "code": "content_policy_violation"
            }
        }).encode()
        
        mock_error = BadRequestError("Content policy violation", response=error_response, body=None)
        mock_client.images.edit.side_effect = mock_error
        
        with pytest.raises(Exception, match="OpenAI inpainting has generated content that doesn't pass moderation filters"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_inpaint_image_api_error(
        self, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test handling of general OpenAI API error."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation success
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Create a generic exception that will be caught by the general exception handler
        mock_error = Exception("Rate limit exceeded")
        mock_client.images.edit.side_effect = mock_error
        
        with pytest.raises(Exception, match="OpenAI Inpainting Error: Rate limit exceeded"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    def test_generate_openai_inpaint_image_no_response_data(
        self, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test handling when API returns no image data."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation success
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock empty response
        mock_edit_response = Mock()
        mock_edit_response.data = []
        mock_client.images.edit.return_value = mock_edit_response
        
        with pytest.raises(Exception, match="OpenAI inpainting API did not return image data"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
    
    @patch("app.app")
    @patch("app.client")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    def test_generate_openai_inpaint_image_custom_size(
        self, mock_process_image, mock_make_prompt, mock_client, mock_app, temp_image_files
    ):
        """Test inpainting with custom image size."""
        base_image_path, mask_path = temp_image_files
        
        mock_app.static_folder = "/test/static"
        mock_make_prompt.return_value = "processed prompt"
        
        # Mock moderation success
        mock_moderation_result = Mock()
        mock_moderation_result.flagged = False
        mock_moderation_response = Mock()
        mock_moderation_response.results = [mock_moderation_result]
        mock_client.moderations.create.return_value = mock_moderation_response
        
        # Mock images.edit response
        mock_image_data = Mock()
        mock_image_data.b64_json = "fake_base64_image_data"
        mock_edit_response = Mock()
        mock_edit_response.data = [mock_image_data]
        mock_client.images.edit.return_value = mock_edit_response
        
        # Mock process_image_response
        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/inpainted.png"
        mock_saved_data.image_name = "inpainted.png"
        mock_process_image.return_value = mock_saved_data
        
        with patch("app.base64.b64decode") as mock_b64decode:
            mock_b64decode.return_value = b"decoded image data"
            
            # Call with custom size
            result = generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser",
                size="512x512"
            )
        
        # Verify size was passed correctly
        call_kwargs = mock_client.images.edit.call_args.kwargs
        assert call_kwargs["size"] == "512x512"
        
        # Verify metadata includes correct size
        call_args = mock_process_image.call_args[0]
        metadata = call_args[4]
        assert metadata["Size"] == "512x512"