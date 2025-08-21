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
from PIL import Image as PILImage

from novelai_client import (
    NovelAIClient,
    NovelAIModel,
    NovelAIAction,
    NovelAIGenerationPayload,
    NovelAIInpaintPayload,
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
    
    def test_generate_inpaint_image_basic(self):
        """Test basic inpainting functionality."""
        # Create a mock ZIP file with inpainted image data
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("inpainted.png", b"inpainted image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            with patch.object(NovelAIClient, '_process_novelai_mask') as mock_process_mask:
                mock_process_mask.return_value = b"processed mask data"
                
                client = NovelAIClient("test-key")
                result = client.generate_inpaint_image(
                    base_image=b"base image data",
                    mask=b"mask image data",
                    prompt="inpaint this area"
                )
                
                assert result == b"inpainted image data"
                
                # Verify mask processing was called
                mock_process_mask.assert_called_once_with(b"mask image data")
                
                # Verify the request payload
                mock_request.assert_called_once()
                call_args = mock_request.call_args
                endpoint, payload = call_args[0]
                
                assert endpoint == "ai/generate-image"
                assert payload["action"] == "infill"
                assert payload["model"] == "nai-diffusion-4-5-full-inpainting"
                assert payload["parameters"]["v4_prompt"]["caption"]["base_caption"] == "inpaint this area"
                assert "image" in payload
                assert "mask" in payload
    
    def test_generate_inpaint_image_with_negative_prompt(self):
        """Test inpainting with negative prompt."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("inpainted.png", b"inpainted image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            with patch.object(NovelAIClient, '_process_novelai_mask') as mock_process_mask:
                mock_process_mask.return_value = b"processed mask data"
                
                client = NovelAIClient("test-key")
                result = client.generate_inpaint_image(
                    base_image=b"base image data",
                    mask=b"mask image data",
                    prompt="inpaint this area",
                    negative_prompt="avoid this"
                )
                
                assert result == b"inpainted image data"
                
                # Verify negative prompt in payload
                call_args = mock_request.call_args
                payload = call_args[0][1]
                assert payload["parameters"]["v4_negative_prompt"]["caption"]["base_caption"] == "avoid this"
    
    def test_generate_inpaint_image_custom_parameters(self):
        """Test inpainting with custom parameters."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("inpainted.png", b"inpainted image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            with patch.object(NovelAIClient, '_process_novelai_mask') as mock_process_mask:
                mock_process_mask.return_value = b"processed mask data"
                
                client = NovelAIClient("test-key")
                result = client.generate_inpaint_image(
                    base_image=b"base image data",
                    mask=b"mask image data",
                    prompt="inpaint this area",
                    width=512,
                    height=768,
                    seed=12345,
                    steps=20,
                    scale=7.5
                )
                
                assert result == b"inpainted image data"
                
                # Verify custom parameters
                call_args = mock_request.call_args
                payload = call_args[0][1]
                params = payload["parameters"]
                
                assert params["width"] == 512
                assert params["height"] == 768
                assert params["seed"] == 12345
                assert params["steps"] == 20
                assert params["scale"] == 7.5
    
    @patch('novelai_client.base64.b64encode')
    def test_generate_inpaint_image_base64_encoding(self, mock_b64encode):
        """Test that base64 encoding is called correctly for inpainting."""
        # Mock base64 encoding
        mock_b64encode.side_effect = [
            Mock(decode=Mock(return_value="base64_base_image")),
            Mock(decode=Mock(return_value="base64_processed_mask"))
        ]
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("inpainted.png", b"inpainted image data")
        zip_content = zip_buffer.getvalue()
        
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = zip_content
            mock_request.return_value = mock_response
            
            with patch.object(NovelAIClient, '_process_novelai_mask') as mock_process_mask:
                mock_process_mask.return_value = b"processed mask data"
                
                client = NovelAIClient("test-key")
                result = client.generate_inpaint_image(
                    base_image=b"base image data",
                    mask=b"mask image data",
                    prompt="inpaint this area"
                )
                
                assert result == b"inpainted image data"
                
                # Verify mask processing was called
                mock_process_mask.assert_called_once_with(b"mask image data")
                
                # Verify base64 encoding was called for both images
                assert mock_b64encode.call_count == 2
                mock_b64encode.assert_any_call(b"base image data")
                mock_b64encode.assert_any_call(b"processed mask data")  # Should use processed mask
                
                # Verify encoded data is in payload
                call_args = mock_request.call_args
                payload = call_args[0][1]
                assert payload["image"] == "base64_base_image"
                assert payload["mask"] == "base64_processed_mask"
    
    def test_generate_inpaint_image_zip_extraction_error(self):
        """Test error handling when inpainting ZIP extraction fails."""
        with patch.object(NovelAIClient, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = b"invalid zip data"
            mock_request.return_value = mock_response
            
            with patch.object(NovelAIClient, '_process_novelai_mask') as mock_process_mask:
                mock_process_mask.return_value = b"processed mask data"
                
                client = NovelAIClient("test-key")
                
                with pytest.raises(NovelAIClientError) as exc_info:
                    client.generate_inpaint_image(
                        base_image=b"base image data",
                        mask=b"mask image data",
                        prompt="inpaint this area"
                    )
                
                assert "Failed to extract inpainted image from response" in str(exc_info.value)
    
    def test_process_novelai_mask(self):
        """Test the NovelAI mask processing function."""
        # Create a test mask image
        mask_image = PILImage.new('RGB', (64, 64), color='black')
        
        # Add a white square in the center
        for x in range(24, 40):
            for y in range(24, 40):
                mask_image.putpixel((x, y), (255, 255, 255))
        
        # Convert to bytes
        mask_buffer = io.BytesIO()
        mask_image.save(mask_buffer, format='PNG')
        mask_bytes = mask_buffer.getvalue()
        
        client = NovelAIClient("test-key")
        processed_mask_bytes = client._process_novelai_mask(mask_bytes)
        
        # Verify the processed mask
        processed_mask = PILImage.open(io.BytesIO(processed_mask_bytes))
        
        # Should be same size as original
        assert processed_mask.size == (64, 64)
        
        # Should be RGB format
        assert processed_mask.mode == 'RGB'
        
        # Check that the mask has the expected block structure
        # Due to the 8x downscale and upscale, we should have 8x8 pixel blocks
        # Sample a few pixels to verify block structure
        center_pixel = processed_mask.getpixel((32, 32))  # Should be white
        assert center_pixel == (255, 255, 255) or center_pixel == (0, 0, 0)  # Should be pure black or white
        
        corner_pixel = processed_mask.getpixel((0, 0))  # Should be black
        assert corner_pixel == (0, 0, 0)
    
    def test_process_novelai_mask_grayscale_input(self):
        """Test mask processing with grayscale input."""
        # Create a grayscale test mask
        mask_image = PILImage.new('L', (32, 32), color=0)  # Black background
        
        # Add white area
        for x in range(12, 20):
            for y in range(12, 20):
                mask_image.putpixel((x, y), 255)
        
        mask_buffer = io.BytesIO()
        mask_image.save(mask_buffer, format='PNG')
        mask_bytes = mask_buffer.getvalue()
        
        client = NovelAIClient("test-key")
        processed_mask_bytes = client._process_novelai_mask(mask_bytes)
        
        # Should process without error
        processed_mask = PILImage.open(io.BytesIO(processed_mask_bytes))
        assert processed_mask.size == (32, 32)
        assert processed_mask.mode == 'RGB'
    
    def test_process_novelai_mask_error_handling(self):
        """Test mask processing error handling."""
        client = NovelAIClient("test-key")
        
        # Test with invalid image data
        with pytest.raises(NovelAIClientError) as exc_info:
            client._process_novelai_mask(b"invalid image data")
        
        assert "Failed to process NovelAI mask" in str(exc_info.value)
    
    def test_process_novelai_mask_block_structure(self):
        """Test that mask processing creates the expected 8x8 block structure."""
        # Create a test mask with a specific pattern
        mask_image = PILImage.new('RGB', (80, 80), color='black')  # Size divisible by 8
        
        # Add a white square that should create blocks
        for x in range(32, 48):  # 16x16 white area
            for y in range(32, 48):
                mask_image.putpixel((x, y), (255, 255, 255))
        
        # Convert to bytes
        mask_buffer = io.BytesIO()
        mask_image.save(mask_buffer, format='PNG')
        mask_bytes = mask_buffer.getvalue()
        
        client = NovelAIClient("test-key")
        processed_mask_bytes = client._process_novelai_mask(mask_bytes)
        
        # Verify the processed mask has block structure
        processed_mask = PILImage.open(io.BytesIO(processed_mask_bytes))
        
        # Check that adjacent pixels in an 8x8 block have the same value
        # Sample a few positions to verify block structure
        pixel_40_40 = processed_mask.getpixel((40, 40))  # Should be white (in the white area)
        pixel_41_40 = processed_mask.getpixel((41, 40))  # Should be same as pixel_40_40 (same 8x8 block)
        pixel_47_47 = processed_mask.getpixel((47, 47))  # Should be same as pixel_40_40 (same 8x8 block)
        
        # All pixels in the same 8x8 block should have the same value
        assert pixel_40_40 == pixel_41_40
        assert pixel_40_40 == pixel_47_47
        
        # Check a pixel outside the white area
        pixel_16_16 = processed_mask.getpixel((16, 16))  # Should be black
        assert pixel_16_16 == (0, 0, 0)
        
        # The white area pixels should be different from black area pixels
        assert pixel_40_40 != pixel_16_16
    
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


class TestNovelAIInpaintPayload:
    """Test cases for NovelAIInpaintPayload dataclass."""
    
    def test_inpaint_payload_creation(self):
        """Test basic inpaint payload creation."""
        payload = NovelAIInpaintPayload("inpaint prompt")
        
        assert payload.input == "inpaint prompt"
        assert payload.model == NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING
        assert payload.action == NovelAIAction.INPAINT
        assert payload.parameters == {}
        assert payload.mask == ""
        assert payload.image == ""
    
    def test_inpaint_payload_with_image_data(self):
        """Test inpaint payload creation with image data."""
        payload = NovelAIInpaintPayload(
            "inpaint prompt",
            mask="base64_mask_data",
            image="base64_image_data"
        )
        
        assert payload.input == "inpaint prompt"
        assert payload.mask == "base64_mask_data"
        assert payload.image == "base64_image_data"
    
    def test_inpaint_payload_inheritance(self):
        """Test that inpaint payload inherits from generation payload."""
        payload = NovelAIInpaintPayload("test")
        assert isinstance(payload, NovelAIGenerationPayload)


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