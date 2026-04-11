"""Tests for combined img2img + inpainting operations."""
import pytest
from unittest.mock import patch, MagicMock
from image_models import (
    Operation,
    Provider,
    CombinedRequest,
    create_request_from_form_data,
    ImageRequestValidator,
)


def test_combined_operation_enum():
    """Test that COMBINED operation is in the Operation enum."""
    assert Operation.COMBINED == "combined"


def test_combined_request_creation():
    """Test creating a CombinedRequest."""
    req = CombinedRequest(
        prompt="test prompt",
        provider=Provider.NOVELAI,
        base_image_path="static/images/user/base.png",
        mask_path="static/images/user/mask.png",
    )
    assert req.operation == Operation.COMBINED
    assert req.base_image_path == "static/images/user/base.png"
    assert req.mask_path == "static/images/user/mask.png"
    assert req.strength == 0.7


def test_combined_request_requires_base_image():
    """Test that CombinedRequest requires base_image_path."""
    with pytest.raises(ValueError, match="Base image path is required"):
        CombinedRequest(
            prompt="test",
            provider=Provider.NOVELAI,
            base_image_path="",
            mask_path="static/images/user/mask.png",
        )


def test_combined_request_requires_mask():
    """Test that CombinedRequest requires mask_path."""
    with pytest.raises(ValueError, match="Mask path is required"):
        CombinedRequest(
            prompt="test",
            provider=Provider.NOVELAI,
            base_image_path="static/images/user/base.png",
            mask_path="",
        )


def test_novelai_supports_combined():
    """Test that NovelAI supports combined operations."""
    assert ImageRequestValidator.validate_provider_operation_compatibility(
        Provider.NOVELAI, Operation.COMBINED
    )


def test_openai_does_not_support_combined():
    """Test that OpenAI does not support combined operations."""
    assert not ImageRequestValidator.validate_provider_operation_compatibility(
        Provider.OPENAI, Operation.COMBINED
    )


def test_create_request_from_form_data_combined():
    """Test creating a combined request from form data."""
    form_data = {
        "prompt": "test prompt",
        "provider": "novelai",
        "operation": "combined",
        "size": "1024x1024",
        "quality": "high",
        "seed": "42",
        "base_image_path": "static/images/user/base.png",
        "mask_path": "static/images/user/mask.png",
        "strength": "0.55",
    }
    req = create_request_from_form_data(form_data)
    assert isinstance(req, CombinedRequest)
    assert req.operation == Operation.COMBINED
    assert req.base_image_path == "static/images/user/base.png"
    assert req.mask_path == "static/images/user/mask.png"
    assert req.strength == 0.55


def test_create_request_from_form_data_inpaint_strength_and_noise():
    """Inpaint uses a single strength plus noise from the form."""
    form_data = {
        "prompt": "p",
        "provider": "novelai",
        "operation": "inpaint",
        "size": "1024x1024",
        "quality": "high",
        "seed": "1",
        "base_image_path": "static/images/user/base.png",
        "mask_path": "static/images/user/mask.png",
        "strength": "0.4",
        "noise": "0.33",
    }
    req = create_request_from_form_data(form_data)
    assert req.strength == 0.4
    assert req.noise == 0.33


def test_backward_compatibility_inpaint():
    """Test that existing inpaint requests still work."""
    form_data = {
        "prompt": "test prompt",
        "provider": "novelai",
        "operation": "inpaint",
        "size": "1024x1024",
        "quality": "high",
        "seed": "42",
        "base_image_path": "static/images/user/base.png",
        "mask_path": "static/images/user/mask.png",
    }
    from image_models import InpaintingRequest
    req = create_request_from_form_data(form_data)
    assert isinstance(req, InpaintingRequest)
    assert req.operation == Operation.INPAINT
    assert req.strength == 1.0


def test_backward_compatibility_img2img():
    """Test that existing img2img requests still work."""
    form_data = {
        "prompt": "test prompt",
        "provider": "novelai",
        "operation": "img2img",
        "size": "1024x1024",
        "quality": "high",
        "seed": "42",
        "base_image_path": "static/images/user/base.png",
        "strength": "0.7",
    }
    from image_models import Img2ImgRequest
    req = create_request_from_form_data(form_data)
    assert isinstance(req, Img2ImgRequest)
    assert req.operation == Operation.IMG2IMG
