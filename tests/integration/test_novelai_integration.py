"""
Integration tests for the NovelAI client using real API calls.

These tests require a valid NOVELAI_API_KEY in the environment and will
make actual API calls to the NovelAI service. They are marked with the
'integration' marker and can be skipped if API keys are not available.
"""

import pytest
import os
from novelai_client import NovelAIClient, NovelAIAPIError


@pytest.mark.integration
class TestNovelAIClientIntegration:
    """Integration tests for NovelAI client with real API calls."""
    
    def test_generate_image_real_api(self, skip_if_no_api_key):
        """Test actual image generation using real NovelAI API."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        # Generate a simple image
        result = client.generate_image(
            prompt="a simple red circle on white background",
            width=512,
            height=512,
            steps=10  # Use fewer steps for faster testing
        )
        
        # Verify we got image data back
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Basic check that it looks like image data (PNG header)
        assert result.startswith(b'\x89PNG')
    
    def test_generate_image_with_negative_prompt_real_api(self, skip_if_no_api_key):
        """Test image generation with negative prompt using real API."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        result = client.generate_image(
            prompt="a beautiful landscape",
            negative_prompt="people, humans, faces",
            width=512,
            height=512,
            steps=10
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b'\x89PNG')
    
    def test_generate_image_with_character_prompts_real_api(self, skip_if_no_api_key):
        """Test image generation with character prompts using real API."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        character_prompts = [
            {"positive": "red hair, blue eyes", "negative": ""},
            {"positive": "blonde hair, green eyes", "negative": "glasses"}
        ]
        
        result = client.generate_image(
            prompt="two characters standing together",
            character_prompts=character_prompts,
            width=512,
            height=512,
            steps=10
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b'\x89PNG')
    
    def test_invalid_api_key_error(self):
        """Test that invalid API key raises appropriate error."""
        client = NovelAIClient("invalid-api-key")
        
        with pytest.raises(NovelAIAPIError) as exc_info:
            client.generate_image("test prompt", steps=10)
        
        # Should get a 401 or 403 error for invalid API key
        assert exc_info.value.status_code in [401, 403]
    
    def test_custom_parameters_real_api(self, skip_if_no_api_key):
        """Test image generation with custom parameters using real API."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        result = client.generate_image(
            prompt="abstract art",
            width=768,
            height=512,
            seed=42,
            steps=15,
            scale=8.0
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b'\x89PNG')
    
    @pytest.mark.skip(reason="Expensive test - only run manually")
    def test_high_resolution_generation(self, skip_if_no_api_key):
        """Test high resolution image generation (expensive, skip by default)."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        result = client.generate_image(
            prompt="detailed landscape painting",
            width=1024,
            height=1024,
            steps=28  # Full steps for quality
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b'\x89PNG')
        
        # High resolution images should be larger
        assert len(result) > 100000  # At least 100KB
    
    def test_upscale_image_real_api(self, skip_if_no_api_key):
        """Test actual image upscaling using real NovelAI API."""
        skip_if_no_api_key('novelai')
        
        api_key = os.getenv('NOVELAI_API_KEY')
        client = NovelAIClient(api_key)
        
        # First generate a small image
        original_image = client.generate_image(
            prompt="a simple test image",
            width=512,
            height=512,
            steps=10
        )
        
        # Then upscale it
        upscaled_image = client.upscale_image(original_image, 512, 512)
        
        # Verify we got upscaled image data back
        assert isinstance(upscaled_image, bytes)
        assert len(upscaled_image) > 0
        assert upscaled_image.startswith(b'\x89PNG')
        
        # Upscaled image should be larger than original
        assert len(upscaled_image) > len(original_image)