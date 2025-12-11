"""
Tests for the VibeEncoderService class.

This module contains unit tests for the vibe encoding service functionality,
including API interaction and error handling.
"""

import tempfile
from unittest.mock import Mock, patch, mock_open

import pytest

from novelai_client import NovelAIClient, NovelAIAPIError, NovelAIClientError
from vibe_encoder import VibeEncoderService
from vibe_models import VibeCollection
from vibe_storage import VibeStorageManager


class TestVibeEncoderService:
    """Unit tests for VibeEncoderService functionality."""
    
    @pytest.fixture
    def mock_novelai_client(self):
        """Create a mock NovelAI client."""
        return Mock(spec=NovelAIClient)
    
    @pytest.fixture
    def storage_manager(self):
        """Create a temporary storage manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield VibeStorageManager(temp_dir)
    
    @pytest.fixture
    def encoder_service(self, mock_novelai_client, storage_manager):
        """Create a VibeEncoderService with mocked dependencies."""
        return VibeEncoderService(mock_novelai_client, storage_manager)
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing."""
        return b"fake_image_data_for_testing"
    
    def test_encode_vibe_success(self, encoder_service, mock_novelai_client, sample_image_bytes):
        """Test successful vibe encoding at all strength levels."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock file reading and storage manager
        with patch("builtins.open", mock_open(read_data=sample_image_bytes)):
            with patch("os.path.exists", return_value=True):
                with patch.object(encoder_service.storage_manager, 'save_collection') as mock_save:
                    # Mock API responses for each strength
                    mock_novelai_client.encode_vibe.side_effect = [
                        f"encoded_data_{strength}" for strength in VibeEncoderService.ENCODING_STRENGTHS
                    ]
                    
                    # Call encode_vibe
                    result = encoder_service.encode_vibe(username, image_path, name, model)
                    
                    # Verify the result
                    assert isinstance(result, VibeCollection)
                    assert result.name == name
                    assert result.model == model
                    assert len(result.encodings) == 5
                    
                    # Verify all required strengths are present
                    expected_strengths = {"1.0", "0.85", "0.7", "0.5", "0.35"}
                    assert set(result.encodings.keys()) == expected_strengths
                    
                    # Verify API was called 5 times with correct parameters
                    assert mock_novelai_client.encode_vibe.call_count == 5
                    
                    # Verify each call had the correct parameters
                    for i, strength in enumerate(VibeEncoderService.ENCODING_STRENGTHS):
                        call_args = mock_novelai_client.encode_vibe.call_args_list[i]
                        assert call_args[1]["image_bytes"] == sample_image_bytes
                        assert call_args[1]["information_extracted"] == strength
                        assert call_args[1]["model"] == model
                    
                    # Verify storage manager was called
                    mock_save.assert_called_once_with(username, result)
    
    def test_encode_vibe_with_progress_callback(self, encoder_service, mock_novelai_client, sample_image_bytes):
        """Test that progress callback is called correctly."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock progress callback
        progress_callback = Mock()
        
        # Mock file reading and API responses
        with patch("builtins.open", mock_open(read_data=sample_image_bytes)):
            with patch("os.path.exists", return_value=True):
                with patch.object(encoder_service.storage_manager, 'save_collection'):
                    mock_novelai_client.encode_vibe.side_effect = [
                        f"encoded_data_{strength}" for strength in VibeEncoderService.ENCODING_STRENGTHS
                    ]
                    
                    # Call encode_vibe with progress callback
                    encoder_service.encode_vibe(username, image_path, name, model, progress_callback)
                
                    # Verify progress callback was called 5 times
                    assert progress_callback.call_count == 5
                    
                    # Verify callback parameters
                    for i, strength in enumerate(VibeEncoderService.ENCODING_STRENGTHS):
                        call_args = progress_callback.call_args_list[i]
                        step, total, message = call_args[0]
                        assert step == i + 1
                        assert total == 5
                        assert f"strength {strength}" in message
    
    def test_encode_vibe_file_not_found(self, encoder_service):
        """Test error handling when source image file doesn't exist."""
        username = "testuser"
        image_path = "/nonexistent/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Source image not found"):
                encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_empty_name(self, encoder_service):
        """Test error handling for empty vibe collection name."""
        username = "testuser"
        image_path = "/test/image.png"
        name = ""  # Empty name
        model = "nai-diffusion-4-5-full"
        
        with patch("os.path.exists", return_value=True):
            with pytest.raises(ValueError, match="Vibe collection name cannot be empty"):
                encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_empty_model(self, encoder_service):
        """Test error handling for empty model name."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = ""  # Empty model
        
        with patch("os.path.exists", return_value=True):
            with pytest.raises(ValueError, match="Model name cannot be empty"):
                encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_api_error(self, encoder_service, mock_novelai_client, sample_image_bytes):
        """Test error handling when NovelAI API returns an error."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock file reading
        with patch("builtins.open", mock_open(read_data=sample_image_bytes)):
            with patch("os.path.exists", return_value=True):
                # Mock API error on first call
                mock_novelai_client.encode_vibe.side_effect = NovelAIAPIError(500, "Server error")
                
                # Should propagate the API error with context
                with pytest.raises(NovelAIAPIError, match="Failed to encode at strength 1.0"):
                    encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_client_error(self, encoder_service, mock_novelai_client, sample_image_bytes):
        """Test error handling when NovelAI client has an error."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock file reading
        with patch("builtins.open", mock_open(read_data=sample_image_bytes)):
            with patch("os.path.exists", return_value=True):
                # Mock client error on second call
                mock_novelai_client.encode_vibe.side_effect = [
                    "encoded_data_1.0",  # First call succeeds
                    NovelAIClientError("Network error")  # Second call fails
                ]
                
                # Should propagate the client error with context
                with pytest.raises(NovelAIClientError, match="Failed to encode at strength 0.85"):
                    encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_empty_response(self, encoder_service, mock_novelai_client, sample_image_bytes):
        """Test error handling when API returns empty encoded data."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock file reading
        with patch("builtins.open", mock_open(read_data=sample_image_bytes)):
            with patch("os.path.exists", return_value=True):
                # Mock empty response
                mock_novelai_client.encode_vibe.return_value = ""
                
                # Should raise client error for empty response
                with pytest.raises(NovelAIClientError, match="Received empty encoded data from API"):
                    encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_encode_vibe_file_read_error(self, encoder_service, sample_image_bytes):
        """Test error handling when file cannot be read."""
        username = "testuser"
        image_path = "/test/image.png"
        name = "Test Vibe"
        model = "nai-diffusion-4-5-full"
        
        # Mock file exists but reading fails
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                with pytest.raises(FileNotFoundError, match="Failed to read source image"):
                    encoder_service.encode_vibe(username, image_path, name, model)
    
    def test_call_encode_api_success(self, encoder_service, mock_novelai_client):
        """Test the internal _call_encode_api method."""
        image_bytes = b"test_image_data"
        strength = 0.7
        model = "nai-diffusion-4-5-full"
        expected_result = "encoded_data_test"
        
        # Mock successful API call
        mock_novelai_client.encode_vibe.return_value = expected_result
        
        # Call the method
        result = encoder_service._call_encode_api(image_bytes, strength, model)
        
        # Verify result and API call
        assert result == expected_result
        mock_novelai_client.encode_vibe.assert_called_once_with(
            image_bytes=image_bytes,
            information_extracted=strength,
            model=model
        )
    
    def test_call_encode_api_unexpected_error(self, encoder_service, mock_novelai_client):
        """Test _call_encode_api with unexpected error."""
        image_bytes = b"test_image_data"
        strength = 0.7
        model = "nai-diffusion-4-5-full"
        
        # Mock unexpected error
        mock_novelai_client.encode_vibe.side_effect = RuntimeError("Unexpected error")
        
        # Should wrap as client error
        with pytest.raises(NovelAIClientError, match="Unexpected error during encoding"):
            encoder_service._call_encode_api(image_bytes, strength, model)