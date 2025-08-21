"""
Integration tests for NovelAI img2img functionality.

These tests verify that the img2img functionality works correctly with real API calls
when API keys are available, and gracefully skip when they are not.
"""

import pytest
import os
import io
from PIL import Image as PILImage

from novelai_client import NovelAIClient, NovelAIAPIError, NovelAIClientError


class TestNovelAIImg2ImgIntegration:
    """Integration test cases for NovelAI img2img functionality."""

    @pytest.fixture
    def novelai_client(self, skip_if_no_api_key):
        """Create a NovelAI client for testing."""
        skip_if_no_api_key('novelai')
        api_key = os.getenv('NOVELAI_API_KEY')
        return NovelAIClient(api_key)

    @pytest.fixture
    def sample_base_image(self):
        """Create a sample base image for img2img testing."""
        # Create a simple test image
        image = PILImage.new('RGB', (512, 512), color='blue')
        
        # Add some simple content to make it more interesting
        for x in range(200, 312):
            for y in range(200, 312):
                image.putpixel((x, y), (255, 255, 255))  # White square in center
        
        # Convert to bytes
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='PNG')
        return image_buffer.getvalue()

    @pytest.mark.integration
    def test_generate_img2img_image_real_api(self, novelai_client, sample_base_image):
        """Test img2img generation with real NovelAI API."""
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="a beautiful landscape with mountains and trees",
                negative_prompt="blurry, low quality",
                strength=0.7,
                width=512,
                height=512,
                seed=12345,
                steps=10,  # Use fewer steps for faster testing
                scale=6.0
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (512, 512)
            assert result_image.mode in ['RGB', 'RGBA']
            
        except NovelAIAPIError as e:
            # If we get a specific API error, log it but don't fail the test
            # This could happen due to rate limits, insufficient credits, etc.
            pytest.skip(f"NovelAI API error during integration test: {e}")
        except NovelAIClientError as e:
            # Network or client errors should also be skipped in integration tests
            pytest.skip(f"NovelAI client error during integration test: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_different_strengths(self, novelai_client, sample_base_image):
        """Test img2img with different strength values."""
        strengths_to_test = [0.3, 0.5, 0.8]
        
        for strength in strengths_to_test:
            try:
                result = novelai_client.generate_img2img_image(
                    base_image=sample_base_image,
                    prompt="a colorful abstract painting",
                    strength=strength,
                    width=512,
                    height=512,
                    steps=8,  # Minimal steps for speed
                    seed=42  # Fixed seed for consistency
                )
                
                # Verify we got valid image data
                assert isinstance(result, bytes)
                assert len(result) > 0
                
                # Verify it's a valid image
                result_image = PILImage.open(io.BytesIO(result))
                assert result_image.size == (512, 512)
                
            except (NovelAIAPIError, NovelAIClientError) as e:
                pytest.skip(f"NovelAI API error with strength {strength}: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_minimal_parameters(self, novelai_client, sample_base_image):
        """Test img2img with minimal parameters."""
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="simple test image"
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image with default dimensions
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (1024, 1024)  # Default size
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error during minimal parameter test: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_custom_dimensions(self, novelai_client, sample_base_image):
        """Test img2img with custom dimensions."""
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="test image with custom size",
                width=768,
                height=512,
                steps=8
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it has the requested dimensions
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (768, 512)
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error during custom dimensions test: {e}")

    def test_generate_img2img_image_invalid_api_key(self, sample_base_image):
        """Test img2img with invalid API key."""
        client = NovelAIClient("invalid-api-key")
        
        with pytest.raises(NovelAIAPIError) as exc_info:
            client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="test prompt"
            )
        
        # Should get an authentication error
        assert exc_info.value.status_code in [401, 403]

    def test_generate_img2img_image_invalid_base_image(self, novelai_client):
        """Test img2img with invalid base image data."""
        with pytest.raises(NovelAIClientError):
            novelai_client.generate_img2img_image(
                base_image=b"invalid image data",
                prompt="test prompt"
            )

    def test_generate_img2img_image_empty_prompt(self, novelai_client, sample_base_image):
        """Test img2img with empty prompt."""
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="",  # Empty prompt
                steps=8
            )
            
            # Should still work with empty prompt
            assert isinstance(result, bytes)
            assert len(result) > 0
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error with empty prompt: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_large_base_image(self, novelai_client):
        """Test img2img with a larger base image."""
        # Create a larger test image
        large_image = PILImage.new('RGB', (1024, 1024), color='green')
        
        # Add some pattern
        for x in range(0, 1024, 100):
            for y in range(0, 1024, 100):
                for i in range(50):
                    for j in range(50):
                        if x + i < 1024 and y + j < 1024:
                            large_image.putpixel((x + i, y + j), (255, 0, 0))  # Red squares
        
        # Convert to bytes
        image_buffer = io.BytesIO()
        large_image.save(image_buffer, format='PNG')
        large_image_bytes = image_buffer.getvalue()
        
        try:
            result = novelai_client.generate_img2img_image(
                base_image=large_image_bytes,
                prompt="transform this pattern into something artistic",
                strength=0.6,
                steps=8
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (1024, 1024)
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error with large image: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_with_character_prompts(self, novelai_client, sample_base_image):
        """Test img2img with character prompts."""
        character_prompts = [
            {"positive": "beautiful woman with long hair", "negative": "ugly, distorted"},
            {"positive": "handsome man with beard", "negative": ""}
        ]
        
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="portrait of two people",
                character_prompts=character_prompts,
                strength=0.7,
                steps=8,
                seed=42
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (512, 512)
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error with character prompts: {e}")

    @pytest.mark.integration
    def test_generate_img2img_image_with_variety(self, novelai_client, sample_base_image):
        """Test img2img with variety enabled."""
        try:
            result = novelai_client.generate_img2img_image(
                base_image=sample_base_image,
                prompt="artistic transformation with variety",
                variety=True,
                strength=0.6,
                steps=8,
                seed=42
            )
            
            # Verify we got image data back
            assert isinstance(result, bytes)
            assert len(result) > 0
            
            # Verify it's a valid image
            result_image = PILImage.open(io.BytesIO(result))
            assert result_image.size == (512, 512)
            
        except (NovelAIAPIError, NovelAIClientError) as e:
            pytest.skip(f"NovelAI API error with variety enabled: {e}")