"""
Tests for the refactored generate_novelai_image function integration.

Tests verify that the function correctly uses the NovelAIClient while
maintaining backward compatibility with the existing function signature.
"""

import pytest
from unittest.mock import Mock, patch

from app import generate_novelai_image, GeneratedImageData
from novelai_client import NovelAIAPIError, NovelAIClientError


class TestGenerateNovelAIImageRefactored:
    """Test cases for the refactored generate_novelai_image function."""

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    @patch("app.NovelAIClient")
    def test_generate_novelai_image_basic(
        self, mock_client_class, mock_process_image, mock_make_prompt
    ):
        """Test basic image generation using the new client."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_image.return_value = b"fake image data"

        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/image.png"
        mock_saved_data.image_name = "image.png"
        mock_process_image.return_value = mock_saved_data

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function
            result = generate_novelai_image(
                prompt="test prompt",
                negative_prompt="avoid this",
                username="testuser",
                size=(512, 768),
                seed=42,
            )

        # Verify client was created with correct API key
        mock_client_class.assert_called_once_with("test-api-key")

        # Verify client.generate_image was called with correct parameters
        mock_client.generate_image.assert_called_once_with(
            prompt="processed prompt",
            negative_prompt="avoid this",
            width=512,
            height=768,
            seed=42,
            character_prompts=[],
        )

        # Verify result
        assert isinstance(result, GeneratedImageData)
        assert result.local_image_path == "/path/to/image.png"
        assert result.revised_prompt == "processed prompt"
        assert result.prompt == "test prompt"
        assert result.image_name == "image.png"

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.make_character_prompts_dynamic")
    @patch("app.process_image_response")
    @patch("app.NovelAIClient")
    def test_generate_novelai_image_with_character_prompts(
        self,
        mock_client_class,
        mock_process_image,
        mock_make_char_prompts,
        mock_make_prompt,
    ):
        """Test image generation with character prompts."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"
        mock_make_char_prompts.return_value = [
            {"positive": "processed char 1", "negative": "processed neg 1"},
            {"positive": "processed char 2", "negative": ""},
        ]

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_image.return_value = b"fake image data"

        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/image.png"
        mock_saved_data.image_name = "image.png"
        mock_process_image.return_value = mock_saved_data

        character_prompts = [
            {"positive": "char 1 prompt", "negative": "char 1 negative"},
            {"positive": "char 2 prompt", "negative": ""},
        ]

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function
            result = generate_novelai_image(
                prompt="test prompt",
                negative_prompt=None,
                username="testuser",
                size=(1024, 1024),
                character_prompts=character_prompts,
            )

        # Verify character prompts were processed
        mock_make_char_prompts.assert_called_once_with(
            character_prompts, "testuser", "/test/static", 0, None
        )

        # Verify client was called with processed character prompts
        mock_client.generate_image.assert_called_once_with(
            prompt="processed prompt",
            negative_prompt=None,
            width=1024,
            height=1024,
            seed=0,
            character_prompts=[
                {"positive": "processed char 1", "negative": "processed neg 1"},
                {"positive": "processed char 2", "negative": ""},
            ],
        )

        # Verify metadata includes character prompts
        call_args = mock_process_image.call_args
        metadata = call_args[0][4]  # Fifth argument is image_metadata

        assert "Character 1 Prompt" in metadata
        assert metadata["Character 1 Prompt"] == "char 1 prompt"
        assert "Character 1 Processed Prompt" in metadata
        assert metadata["Character 1 Processed Prompt"] == "processed char 1"
        assert "Character 2 Prompt" in metadata
        assert metadata["Character 2 Prompt"] == "char 2 prompt"

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.process_image_response")
    @patch("app.NovelAIClient")
    def test_generate_novelai_image_with_upscale(
        self, mock_client_class, mock_process_image, mock_make_prompt
    ):
        """Test image generation with upscaling enabled."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_image.return_value = b"fake image data"
        mock_client.upscale_image.return_value = b"upscaled image data"

        mock_saved_data = Mock()
        mock_saved_data.local_image_path = "/path/to/image.png"
        mock_saved_data.image_name = "image.png"
        mock_process_image.return_value = mock_saved_data

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function with upscale=True
            result = generate_novelai_image(
                prompt="test prompt",
                negative_prompt=None,
                username="testuser",
                size=(512, 512),
                upscale=True,
            )

        # Verify upscale was called on the client
        mock_client.upscale_image.assert_called_once_with(b"fake image data", 512, 512)

        # Verify process_image_response was called with upscaled data
        mock_process_image.assert_called_once()
        process_args = mock_process_image.call_args[0]
        # The file_bytes should be a BytesIO object containing the upscaled data
        assert process_args[0].read() == b"upscaled image data"

    @patch("app.novelai_api_key", None)
    def test_generate_novelai_image_no_api_key(self):
        """Test that missing API key raises appropriate error."""
        with pytest.raises(ValueError, match="NovelAI API key not configured"):
            generate_novelai_image(
                prompt="test prompt",
                negative_prompt=None,
                username="testuser",
                size=(512, 512),
            )

    def test_generate_novelai_image_no_static_folder(self):
        """Test that missing static folder raises appropriate error."""
        with patch("app.app") as mock_app:
            mock_app.static_folder = None

            with pytest.raises(ValueError, match="Flask static folder not defined"):
                generate_novelai_image(
                    prompt="test prompt",
                    negative_prompt=None,
                    username="testuser",
                    size=(512, 512),
                )

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.NovelAIClient")
    def test_generate_novelai_image_api_error(
        self, mock_client_class, mock_make_prompt
    ):
        """Test handling of NovelAI API errors."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_image.side_effect = NovelAIAPIError(400, "Bad request")

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function and expect an exception
            with pytest.raises(
                Exception, match="NovelAI Generate Image 400: Bad request"
            ):
                generate_novelai_image(
                    prompt="test prompt",
                    negative_prompt=None,
                    username="testuser",
                    size=(512, 512),
                )

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.NovelAIClient")
    def test_generate_novelai_image_client_error(
        self, mock_client_class, mock_make_prompt
    ):
        """Test handling of NovelAI client errors."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.generate_image.side_effect = NovelAIClientError("Network error")

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function and expect an exception
            with pytest.raises(
                Exception, match="NovelAI Generate Image Error: Network error"
            ):
                generate_novelai_image(
                    prompt="test prompt",
                    negative_prompt=None,
                    username="testuser",
                    size=(512, 512),
                )

    @patch("app.novelai_api_key", "test-api-key")
    @patch("app.make_prompt_dynamic")
    @patch("app.make_character_prompts_dynamic")
    def test_generate_novelai_image_character_prompt_error(
        self, mock_make_char_prompts, mock_make_prompt
    ):
        """Test handling of character prompt processing errors."""
        # Setup mocks
        mock_make_prompt.return_value = "processed prompt"
        mock_make_char_prompts.side_effect = ValueError("Invalid character prompt")

        character_prompts = [{"positive": "test", "negative": ""}]

        with patch("app.app") as mock_app:
            mock_app.static_folder = "/test/static"

            # Call the function and expect an exception
            with pytest.raises(
                ValueError,
                match="Error processing character prompts: Invalid character prompt",
            ):
                generate_novelai_image(
                    prompt="test prompt",
                    negative_prompt=None,
                    username="testuser",
                    size=(512, 512),
                    character_prompts=character_prompts,
                )
