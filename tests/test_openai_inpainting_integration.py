"""
Integration tests for OpenAI inpainting functionality.

These tests use actual API keys when available and test the complete
OpenAI inpainting workflow with real images and masks.
"""

import pytest
import os
import tempfile
from PIL import Image as PILImage

from app import generate_openai_inpaint_image, GeneratedImageData


@pytest.fixture
def temp_inpaint_images():
    """Create temporary image files for OpenAI inpainting tests."""
    # Create temporary base image (512x512 for OpenAI compatibility)
    base_image = PILImage.new('RGB', (512, 512), color='lightblue')
    
    # Add a white square in the center that we'll inpaint
    for x in range(200, 312):
        for y in range(200, 312):
            base_image.putpixel((x, y), (255, 255, 255))
    
    base_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    base_temp.close()  # Close file handle before saving
    base_image.save(base_temp.name, 'PNG')
    
    # Create temporary mask image (white = inpaint, black = keep)
    mask = PILImage.new('RGB', (512, 512), color='black')
    
    # White area indicates where to inpaint
    for x in range(200, 312):
        for y in range(200, 312):
            mask.putpixel((x, y), (255, 255, 255))
    
    mask_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    mask_temp.close()  # Close file handle before saving
    mask.save(mask_temp.name, 'PNG')
    
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


class TestOpenAIInpaintingIntegration:
    """Integration tests for OpenAI inpainting functionality."""
    
    @pytest.mark.integration
    def test_generate_openai_inpaint_image_real_api(self, skip_if_no_api_key, temp_inpaint_images):
        """Test actual OpenAI inpainting API integration."""
        skip_if_no_api_key('openai')
        
        base_image_path, mask_path = temp_inpaint_images
        
        try:
            result = generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="a red rose",
                username="testuser",
                size="512x512",
                seed=12345
            )
            
            # Verify we got a valid result
            assert isinstance(result, GeneratedImageData)
            assert result.local_image_path is not None
            assert result.image_name is not None
            assert result.prompt == "a red rose"
            assert result.revised_prompt is not None
            
            # Verify the image file was created and is valid
            assert os.path.exists(result.local_image_path)
            
            # Try to open the generated image to verify it's valid
            with PILImage.open(result.local_image_path) as img:
                assert img.size == (512, 512)
                assert img.format == 'PNG'
            
        except Exception as e:
            # If we get specific API errors, we can still verify the function structure
            if "OpenAI" in str(e) and ("quota" in str(e).lower() or "rate" in str(e).lower()):
                pytest.skip(f"OpenAI API quota/rate limit (expected in some cases): {e}")
            elif "moderation" in str(e).lower():
                pytest.skip(f"OpenAI moderation issue (expected in some cases): {e}")
            else:
                pytest.fail(f"Unexpected error in OpenAI inpainting: {e}")
    
    @pytest.mark.integration
    def test_generate_openai_inpaint_image_different_sizes(self, skip_if_no_api_key, temp_inpaint_images):
        """Test OpenAI inpainting with different image sizes."""
        skip_if_no_api_key('openai')
        
        base_image_path, mask_path = temp_inpaint_images
        
        # Test with 256x256 size
        try:
            result = generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path=mask_path,
                prompt="a simple flower",
                username="testuser",
                size="256x256"
            )
            
            assert isinstance(result, GeneratedImageData)
            assert result.local_image_path is not None
            
            # Verify the generated image has correct size
            with PILImage.open(result.local_image_path) as img:
                assert img.size == (256, 256)
            
        except Exception as e:
            if "OpenAI" in str(e) and ("quota" in str(e).lower() or "rate" in str(e).lower()):
                pytest.skip(f"OpenAI API quota/rate limit (expected in some cases): {e}")
            else:
                pytest.fail(f"Unexpected error in OpenAI inpainting with different size: {e}")
    
    def test_generate_openai_inpaint_image_file_validation(self, temp_inpaint_images):
        """Test file validation without making API calls."""
        base_image_path, mask_path = temp_inpaint_images
        
        # Test with non-existent base image
        with pytest.raises(FileNotFoundError, match="Base image file not found"):
            generate_openai_inpaint_image(
                base_image_path="/nonexistent/base.png",
                mask_path=mask_path,
                prompt="test prompt",
                username="testuser"
            )
        
        # Test with non-existent mask
        with pytest.raises(FileNotFoundError, match="Mask image file not found"):
            generate_openai_inpaint_image(
                base_image_path=base_image_path,
                mask_path="/nonexistent/mask.png",
                prompt="test prompt",
                username="testuser"
            )


class TestInpaintingImageCompatibility:
    """Test image format compatibility for OpenAI inpainting."""
    
    def test_png_image_creation(self, temp_inpaint_images):
        """Test that our test images are in PNG format as required by OpenAI."""
        base_image_path, mask_path = temp_inpaint_images
        
        # Verify base image is PNG
        with PILImage.open(base_image_path) as img:
            assert img.format == 'PNG'
            assert img.size == (512, 512)
            assert img.mode == 'RGB'
        
        # Verify mask image is PNG
        with PILImage.open(mask_path) as img:
            assert img.format == 'PNG'
            assert img.size == (512, 512)
            assert img.mode == 'RGB'
    
    def test_mask_image_structure(self, temp_inpaint_images):
        """Test that mask image has correct structure (white = inpaint, black = keep)."""
        _, mask_path = temp_inpaint_images
        
        with PILImage.open(mask_path) as mask:
            # Check that center area is white (will be inpainted)
            center_pixel = mask.getpixel((256, 256))
            assert center_pixel == (255, 255, 255), "Center should be white for inpainting"
            
            # Check that corner is black (will be kept)
            corner_pixel = mask.getpixel((0, 0))
            assert corner_pixel == (0, 0, 0), "Corner should be black to keep original"
            
            # Check edge of inpaint area
            edge_pixel = mask.getpixel((200, 256))  # Left edge of white area
            assert edge_pixel == (255, 255, 255), "Edge of inpaint area should be white"
            
            # Check just outside inpaint area
            outside_pixel = mask.getpixel((199, 256))  # Just outside white area
            assert outside_pixel == (0, 0, 0), "Outside inpaint area should be black"
    
    def test_base_image_structure(self, temp_inpaint_images):
        """Test that base image has distinguishable areas for inpainting."""
        base_image_path, _ = temp_inpaint_images
        
        with PILImage.open(base_image_path) as base:
            # Check background color
            background_pixel = base.getpixel((0, 0))
            assert background_pixel == (173, 216, 230), "Background should be light blue"
            
            # Check area that will be inpainted
            inpaint_area_pixel = base.getpixel((256, 256))
            assert inpaint_area_pixel == (255, 255, 255), "Inpaint area should be white"
            
            # Verify the areas are different
            assert background_pixel != inpaint_area_pixel, "Background and inpaint areas should be different colors"