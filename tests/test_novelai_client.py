"""
Unit tests for the NovelAI client module.

Tests cover the NovelAIClient class functionality including image generation,
error handling, and API request management with mocked responses.
"""

import pytest
import json
import zipfile
import io
from unittest.mock import Mock, patch, MagicMock

from novelai_client import (
    NovelAIClient,
    NovelAIModel,
    NovelAIAction,
    NovelAIGenerationPayload,
    NovelAIClientError,
    NovelAIAPIError
)


class TestNovelAIClient:
    """Test cases for the NovelAIClient class."""
    
    def test_client_initialization(self):
        """Test that the client initializes correctly with API key."""
        api_key = "test-api-key"
        client = NovelAIClient(api_key)
        
        assert client.api_key == api_key
        assert client.base_url == "https://image.novelai.net"
        assert client.session.headers["authorization"] == f"Bearer {api_key}"
        assert client.session.headers["content-type"] == "application/json"
    
    def test_client_initialization_custom_base_url(self):
        """Test client initialization with custom base URL."""
        api_key = "test-api-key"
        base_url = "https://custom.novelai.net"
        client = NovelAIClient(api_key, base_url)
        
        assert client.base_url == base_url
    
    @patch('novelai_client.requests.Session')
    def test_make_request_success(self, mock_session_class):
        """Test successful API request handling."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test response"
        mock_session.post.return_value = mock_response
        
        client = NovelAIClient("test-key")
        payload = {"test": "data"}
        
        response = client._make_request("test-endpoint", payload)
        
        assert response == mock_response
        mock_session.post.assert_called_once_with(
            "https://image.novelai.net/test-endpoint",
            data=json.dumps(payload)
        )
    
    @patch('novelai_client.requests.Session')
    def test_make_request_api_error(self, mock_session_class):
        """Test API error handling in _make_request."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Bad request"}
        mock_session.post.return_value = mock_response
        
        client = NovelAIClient("test-key")
        
        with pytest.raises(NovelAIAPIError) as exc_info:
            client._make_request("test-endpoint", {})
        
        assert exc_info.value.status_code == 400
        assert "Bad request" in str(exc_info.value)
    
    def test_make_request_network_error(self):
        """Test network error handling in _make_request."""
        client = NovelAIClient("test-key")
        
        # Mock the session.post method to raise a requests exception
        with patch.object(client.session, 'post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            with pytest.raises(NovelAIClientError) as exc_info:
                client._make_request("test-endpoint", {})
            
            assert "Network error" in str(exc_info.value)
    
    def test_generate_image_basic(self):
        """Test basic image generation with minimal parameters."""
        # Create a mock ZIP file with image data
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("image.png", b"fake image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            client = NovelAIClient("test-key")
            result = client.generate_image("test prompt")
            
            assert result == b"fake image data"
            
            # Verify the request payload
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            endpoint, payload = call_args[0]
            
            assert endpoint == "ai/generate-image"
            assert payload["action"] == "generate"
            assert payload["model"] == "nai-diffusion-4-5-full"
            assert payload["parameters"]["v4_prompt"]["caption"]["base_caption"] == "test prompt"
    
    def test_generate_image_with_negative_prompt(self):
        """Test image generation with negative prompt."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("image.png", b"fake image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            client = NovelAIClient("test-key")
            result = client.generate_image(
                "test prompt",
                negative_prompt="avoid this"
            )
            
            assert result == b"fake image data"
            
            # Verify negative prompt in payload
            call_args = mock_request.call_args
            payload = call_args[0][1]
            assert payload["parameters"]["v4_negative_prompt"]["caption"]["base_caption"] == "avoid this"
    
    def test_generate_image_with_character_prompts(self):
        """Test image generation with character prompts."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("image.png", b"fake image data")
        zip_content = zip_buffer.getvalue()
        
        character_prompts = [
            {"positive": "character 1 positive", "negative": "character 1 negative"},
            {"positive": "character 2 positive", "negative": ""}
        ]
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            client = NovelAIClient("test-key")
            result = client.generate_image(
                "test prompt",
                character_prompts=character_prompts
            )
            
            assert result == b"fake image data"
            
            # Verify character prompts in payload
            call_args = mock_request.call_args
            payload = call_args[0][1]
            
            char_captions_pos = payload["parameters"]["v4_prompt"]["caption"]["char_captions"]
            char_captions_neg = payload["parameters"]["v4_negative_prompt"]["caption"]["char_captions"]
            
            assert len(char_captions_pos) == 2
            assert char_captions_pos[0]["char_caption"] == "character 1 positive"
            assert char_captions_pos[0]["centers"] == [{"x": 0, "y": 0}]
            assert char_captions_pos[1]["char_caption"] == "character 2 positive"
            assert char_captions_pos[1]["centers"] == [{"x": 0, "y": 0}]
            
            assert len(char_captions_neg) == 1  # Only one has negative prompt
            assert char_captions_neg[0]["char_caption"] == "character 1 negative"
            assert char_captions_neg[0]["centers"] == [{"x": 0, "y": 0}]
    
    def test_generate_image_custom_parameters(self):
        """Test image generation with custom parameters."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("image.png", b"fake image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            client = NovelAIClient("test-key")
            result = client.generate_image(
                "test prompt",
                width=512,
                height=768,
                seed=12345,
                steps=20,
                scale=7.5
            )
            
            assert result == b"fake image data"
            
            # Verify custom parameters
            call_args = mock_request.call_args
            payload = call_args[0][1]
            params = payload["parameters"]
            
            assert params["width"] == 512
            assert params["height"] == 768
            assert params["seed"] == 12345
            assert params["steps"] == 20
            assert params["scale"] == 7.5
    
    def test_generate_image_zip_extraction_error(self):
        """Test error handling when ZIP extraction fails."""
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = b"invalid zip data"
            mock_request.return_value = mock_response
            
            client = NovelAIClient("test-key")
            
            with pytest.raises(NovelAIClientError) as exc_info:
                client.generate_image("test prompt")
            
            assert "Failed to extract image from response" in str(exc_info.value)
    
    def test_upscale_image_basic(self):
        """Test basic image upscaling functionality."""
        # Create a mock ZIP file with upscaled image data
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("upscaled.png", b"upscaled image data")
        zip_content = zip_buffer.getvalue()
        
        client = NovelAIClient("test-key")
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = zip_content
            mock_session.post.return_value = mock_response
            
            result = client.upscale_image(b"original image data", 512, 512)
            
            assert result == b"upscaled image data"
            
            # Verify the request was made to the upscale endpoint
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            url = call_args[0][0]
            assert url == "https://api.novelai.net/ai/upscale"
            
            # Verify the payload structure
            json_data = call_args[1]['json']
            assert json_data['scale'] == 4
            assert json_data['width'] == 512
            assert json_data['height'] == 512
            assert 'image' in json_data
    
    @patch('novelai_client.PILImage')
    def test_upscale_image_large_resolution(self, mock_pil):
        """Test upscaling with large resolution that needs resizing."""
        # Mock PIL Image operations
        mock_image = Mock()
        mock_pil.open.return_value = mock_image
        
        # Create a mock ZIP file with upscaled image data
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("upscaled.png", b"upscaled image data")
        zip_content = zip_buffer.getvalue()
        
        client = NovelAIClient("test-key")
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = zip_content
            mock_session.post.return_value = mock_response
            
            result = client.upscale_image(b"original image data", 1024, 1024)  # Large resolution
            
            assert result == b"upscaled image data"
            
            # Verify PIL operations were called for resizing
            mock_pil.open.assert_called_once()
            mock_image.thumbnail.assert_called_once()
            mock_image.save.assert_called_once()
    
    def test_upscale_image_api_error(self):
        """Test upscale API error handling."""
        client = NovelAIClient("test-key")
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "Bad upscale request"}
            mock_session.post.return_value = mock_response
            
            with pytest.raises(NovelAIAPIError) as exc_info:
                client.upscale_image(b"image data", 512, 512)
            
            assert exc_info.value.status_code == 400
            assert "Bad upscale request" in str(exc_info.value)
    
    def test_upscale_image_zip_extraction_error(self):
        """Test upscale ZIP extraction error handling."""
        client = NovelAIClient("test-key")
        with patch.object(client, 'session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"invalid zip data"
            mock_session.post.return_value = mock_response
            
            with pytest.raises(NovelAIClientError) as exc_info:
                client.upscale_image(b"image data", 512, 512)
            
            assert "Failed to extract upscaled image from response" in str(exc_info.value)


class TestNovelAIEnums:
    """Test cases for NovelAI enum classes."""
    
    def test_novelai_model_enum(self):
        """Test NovelAIModel enum values."""
        assert NovelAIModel.DIFFUSION_4_5_FULL == "nai-diffusion-4-5-full"
        assert NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING == "nai-diffusion-4-5-full-inpainting"
    
    def test_novelai_action_enum(self):
        """Test NovelAIAction enum values."""
        assert NovelAIAction.GENERATE == "generate"
        assert NovelAIAction.INPAINT == "infill"
        assert NovelAIAction.IMG2IMG == "img2img"


class TestNovelAIGenerationPayload:
    """Test cases for NovelAIGenerationPayload dataclass."""
    
    def test_payload_creation(self):
        """Test basic payload creation."""
        payload = NovelAIGenerationPayload("test prompt")
        
        assert payload.input == "test prompt"
        assert payload.model == NovelAIModel.DIFFUSION_4_5_FULL
        assert payload.action == NovelAIAction.GENERATE
        assert payload.parameters == {}
    
    def test_payload_with_custom_values(self):
        """Test payload creation with custom values."""
        custom_params = {"width": 512, "height": 512}
        payload = NovelAIGenerationPayload(
            "test prompt",
            model=NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING,
            action=NovelAIAction.INPAINT,
            parameters=custom_params
        )
        
        assert payload.input == "test prompt"
        assert payload.model == NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING
        assert payload.action == NovelAIAction.INPAINT
        assert payload.parameters == custom_params


class TestNovelAIExceptions:
    """Test cases for NovelAI exception classes."""
    
    def test_novelai_client_error(self):
        """Test NovelAIClientError exception."""
        error = NovelAIClientError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_novelai_api_error(self):
        """Test NovelAIAPIError exception."""
        error = NovelAIAPIError(400, "Bad request")
        
        assert error.status_code == 400
        assert error.message == "Bad request"
        assert str(error) == "NovelAI API Error 400: Bad request"
        assert isinstance(error, NovelAIClientError)