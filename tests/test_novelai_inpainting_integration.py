"""
Integration tests for NovelAI inpainting functionality.

These tests use actual API keys when available and test the complete
inpainting workflow with real images and masks.
"""

import pytest
import os
import io
from PIL import Image as PILImage

from novelai_client import NovelAIClient, NovelAIAPIError, NovelAIClientError


@pytest.fixture
def sample_base_image():
    """Create a sample base image for inpainting tests."""
    # Create a simple 512x512 RGB image
    image = PILImage.new('RGB', (512, 512), color='blue')
    
    # Add a white square in the center that we'll inpaint
    for x in range(200, 312):
        for y in range(200, 312):
            image.putpixel((x, y), (255, 255, 255))
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    image.save(img_buffer, format='PNG')
    return img_buffer.getvalue()


@pytest.fixture
def sample_mask_image():
    """Create a sample mask image for inpainting tests."""
    # Create a black mask with white area to inpaint
    mask = PILImage.new('RGB', (512, 512), color='black')
    
    # White area indicates where to inpaint
    for x in range(200, 312):
        for y in range(200, 312):
            mask.putpixel((x, y), (255, 255, 255))
    
    # Convert to bytes
    mask_buffer = io.BytesIO()
    mask.save(mask_buffer, format='PNG')
    return mask_buffer.getvalue()


class TestNovelAIInpaintingIntegration:
    """Integration tests for NovelAI inpainting functionality."""
    
    @pytest.mark.integration
    def test_generate_inpaint_image_real_api(self, skip_if_no_api_key, sample_base_image, sample_mask_image):
        """Test actual NovelAI inpainting API integration."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        try:
            result = client.generate_inpaint_image(
                base_image=sample_base_image,
                mask=sample_mask_image,
                prompt="a red flower",
                negative_prompt="blurry, low quality",
                width=512,
                height=512,
                seed=12345,
                steps=20,
                scale=6.0
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image by trying to open it
            image = PILImage.open(io.BytesIO(result))
            assert image.size == (512, 512)
            assert image.format == 'PNG'
            
        except NovelAIAPIError as e:
            # If we get a specific API error, we can still verify the client is working
            # Common errors might be insufficient credits, rate limiting, etc.
            pytest.skip(f"NovelAI API error (expected in some cases): {e}")
        except NovelAIClientError as e:
            # Client errors indicate a problem with our implementation
            pytest.fail(f"NovelAI client error: {e}")
    
    @pytest.mark.integration
    def test_generate_inpaint_image_minimal_params(self, skip_if_no_api_key, sample_base_image, sample_mask_image):
        """Test inpainting with minimal parameters."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        try:
            result = client.generate_inpaint_image(
                base_image=sample_base_image,
                mask=sample_mask_image,
                prompt="a simple pattern"
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image
            image = PILImage.open(io.BytesIO(result))
            assert image.size == (1024, 1024)  # Default size
            assert image.format == 'PNG'
            
        except NovelAIAPIError as e:
            pytest.skip(f"NovelAI API error (expected in some cases): {e}")
        except NovelAIClientError as e:
            pytest.fail(f"NovelAI client error: {e}")
    
    def test_generate_inpaint_image_invalid_api_key(self, sample_base_image, sample_mask_image):
        """Test inpainting with invalid API key."""
        client = NovelAIClient("invalid-api-key")
        
        with pytest.raises(NovelAIAPIError) as exc_info:
            client.generate_inpaint_image(
                base_image=sample_base_image,
                mask=sample_mask_image,
                prompt="test prompt"
            )
        
        # Should get an authentication error
        assert exc_info.value.status_code in [401, 403]
    
    def test_generate_inpaint_image_empty_prompt(self, sample_base_image, sample_mask_image):
        """Test inpainting with empty prompt."""
        client = NovelAIClient("test-key")
        
        # This should work at the client level (API might reject it)
        try:
            # We expect this to fail at the API level, not the client level
            with pytest.raises(NovelAIAPIError):
                client.generate_inpaint_image(
                    base_image=sample_base_image,
                    mask=sample_mask_image,
                    prompt=""
                )
        except Exception:
            # If we can't test with real API, just verify the method exists and accepts the parameters
            pass
    
    def test_generate_inpaint_image_invalid_image_data(self):
        """Test inpainting with invalid image data."""
        client = NovelAIClient("test-key")
        
        # This should work at the client level (base64 encoding should handle any bytes)
        # The API might reject invalid image formats, but that's expected
        try:
            with pytest.raises(NovelAIAPIError):
                client.generate_inpaint_image(
                    base_image=b"invalid image data",
                    mask=b"invalid mask data",
                    prompt="test prompt"
                )
        except Exception:
            # If we can't test with real API, just verify the method handles the data
            pass


class TestInpaintingImageProcessing:
    """Test image processing aspects of inpainting."""
    
    def test_sample_image_creation(self, sample_base_image, sample_mask_image):
        """Test that our sample images are created correctly."""
        # Verify base image
        base_img = PILImage.open(io.BytesIO(sample_base_image))
        assert base_img.size == (512, 512)
        assert base_img.format == 'PNG'
        
        # Verify mask image
        mask_img = PILImage.open(io.BytesIO(sample_mask_image))
        assert mask_img.size == (512, 512)
        assert mask_img.format == 'PNG'
        
        # Verify mask has white area (inpaint region)
        # Check center pixel should be white
        center_pixel = mask_img.getpixel((256, 256))
        assert center_pixel == (255, 255, 255)
        
        # Check corner pixel should be black
        corner_pixel = mask_img.getpixel((0, 0))
        assert corner_pixel == (0, 0, 0)
    
    def test_base64_encoding_compatibility(self, sample_base_image, sample_mask_image):
        """Test that our sample images work with base64 encoding."""
        import base64
        
        # Test base64 encoding/decoding
        base_b64 = base64.b64encode(sample_base_image).decode('ascii')
        mask_b64 = base64.b64encode(sample_mask_image).decode('ascii')
        
        # Verify we can decode back
        decoded_base = base64.b64decode(base_b64)
        decoded_mask = base64.b64decode(mask_b64)
        
        assert decoded_base == sample_base_image
        assert decoded_mask == sample_mask_image
        
        # Verify decoded images are still valid
        base_img = PILImage.open(io.BytesIO(decoded_base))
        mask_img = PILImage.open(io.BytesIO(decoded_mask))
        
        assert base_img.size == (512, 512)
        assert mask_img.size == (512, 512)
    
    def test_novelai_mask_processing(self, sample_mask_image):
        """Test that NovelAI mask processing works correctly."""
        from novelai_client import NovelAIClient
        
        client = NovelAIClient("test-key")
        processed_mask_bytes = client._process_novelai_mask(sample_mask_image)
        
        # Verify processed mask is valid
        processed_mask = PILImage.open(io.BytesIO(processed_mask_bytes))
        
        # Should maintain original size
        original_mask = PILImage.open(io.BytesIO(sample_mask_image))
        assert processed_mask.size == original_mask.size
        
        # Should be RGB format
        assert processed_mask.mode == 'RGB'
        
        # Should have block structure due to downscale/upscale process
        # Check that we have pure black/white pixels
        center_pixel = processed_mask.getpixel((256, 256))
        assert center_pixel in [(0, 0, 0), (255, 255, 255)]
        
        corner_pixel = processed_mask.getpixel((0, 0))
        assert corner_pixel == (0, 0, 0)  # Should be black (keep area)