"""Tests for NovelAI variety toggle functionality."""

import pytest
from unittest.mock import Mock, patch
from image_models import ImageGenerationRequest, Provider


class TestNovelAIVarietyToggle:
    """Test variety toggle functionality for NovelAI operations."""

    def test_image_generation_request_variety_parameter(self):
        """Test that ImageGenerationRequest includes variety parameter."""
        request = ImageGenerationRequest(
            prompt="test prompt",
            provider=Provider.NOVELAI,
            variety=True
        )
        
        assert request.variety is True
        
        # Test default value
        request_default = ImageGenerationRequest(
            prompt="test prompt",
            provider=Provider.NOVELAI
        )
        
        assert request_default.variety is False

    def test_novelai_client_variety_parameter(self):
        """Test that NovelAI client methods accept variety parameter."""
        from novelai_client import NovelAIClient
        
        # Test that the client methods have variety parameter in their signatures
        import inspect
        
        # Check generate_image method
        sig = inspect.signature(NovelAIClient.generate_image)
        assert 'variety' in sig.parameters
        assert sig.parameters['variety'].default is False
        
        # Check generate_inpaint_image method
        sig = inspect.signature(NovelAIClient.generate_inpaint_image)
        assert 'variety' in sig.parameters
        assert sig.parameters['variety'].default is False
        
        # Check generate_img2img_image method
        sig = inspect.signature(NovelAIClient.generate_img2img_image)
        assert 'variety' in sig.parameters
        assert sig.parameters['variety'].default is False