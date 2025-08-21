"""
Tests for image generation data models.
"""

import pytest
from image_models import (
    Provider,
    Operation,
    Quality,
    ImageGenerationRequest,
    InpaintingRequest,
    Img2ImgRequest,
    ImageOperationResponse,
    ImageRequestValidator,
    create_request_from_form_data,
    create_success_response,
    create_error_response,
    NovelAIModel,
    OpenAIModel
)


class TestEnums:
    """Test enum definitions."""
    
    def test_provider_enum_values(self):
        """Test Provider enum has correct values."""
        assert Provider.OPENAI == "openai"
        assert Provider.NOVELAI == "novelai"
        assert Provider.STABILITY == "stability"
    
    def test_operation_enum_values(self):
        """Test Operation enum has correct values."""
        assert Operation.GENERATE == "generate"
        assert Operation.INPAINT == "inpaint"
        assert Operation.IMG2IMG == "img2img"
    
    def test_quality_enum_values(self):
        """Test Quality enum has correct values."""
        assert Quality.HIGH == "high"
        assert Quality.MEDIUM == "medium"
        assert Quality.LOW == "low"


class TestImageGenerationRequest:
    """Test ImageGenerationRequest dataclass."""
    
    def test_basic_request_creation(self):
        """Test creating a basic image generation request."""
        request = ImageGenerationRequest(prompt="test prompt")
        
        assert request.prompt == "test prompt"
        assert request.provider == Provider.OPENAI
        assert request.operation == Operation.GENERATE
        assert request.width == 1024
        assert request.height == 1024
        assert request.quality == Quality.HIGH
        assert request.negative_prompt is None
    
    def test_custom_parameters(self):
        """Test creating request with custom parameters."""
        request = ImageGenerationRequest(
            prompt="custom prompt",
            provider=Provider.NOVELAI,
            negative_prompt="bad quality",
            width=512,
            height=768,
            quality=Quality.HIGH
        )
        
        assert request.prompt == "custom prompt"
        assert request.provider == Provider.NOVELAI
        assert request.negative_prompt == "bad quality"
        assert request.width == 512
        assert request.height == 768
        assert request.quality == Quality.HIGH
    
    def test_empty_prompt_validation(self):
        """Test that empty prompts raise ValueError."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            ImageGenerationRequest(prompt="")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            ImageGenerationRequest(prompt="   ")
    
    def test_invalid_dimensions_validation(self):
        """Test that invalid dimensions raise ValueError."""
        with pytest.raises(ValueError, match="Width and height must be positive integers"):
            ImageGenerationRequest(prompt="test", width=0)
        
        with pytest.raises(ValueError, match="Width and height must be positive integers"):
            ImageGenerationRequest(prompt="test", height=-1)
    
    def test_openai_dimension_validation(self):
        """Test OpenAI-specific dimension validation."""
        # Valid dimensions should work
        valid_request = ImageGenerationRequest(
            prompt="test",
            provider=Provider.OPENAI,
            width=1536,
            height=1024
        )
        assert valid_request.width == 1536
        assert valid_request.height == 1024
        
        # Invalid dimensions should raise error
        with pytest.raises(ValueError, match="Invalid dimensions for OpenAI"):
            ImageGenerationRequest(
                prompt="test",
                provider=Provider.OPENAI,
                width=512,
                height=512
            )


class TestInpaintingRequest:
    """Test InpaintingRequest dataclass."""
    
    def test_inpainting_request_creation(self):
        """Test creating an inpainting request."""
        request = InpaintingRequest(
            prompt="inpaint this",
            base_image_path="/path/to/image.png",
            mask_path="/path/to/mask.png"
        )
        
        assert request.prompt == "inpaint this"
        assert request.operation == Operation.INPAINT
        assert request.base_image_path == "/path/to/image.png"
        assert request.mask_path == "/path/to/mask.png"
    
    def test_missing_base_image_validation(self):
        """Test that missing base image path raises ValueError."""
        with pytest.raises(ValueError, match="Base image path is required for inpainting"):
            InpaintingRequest(
                prompt="test",
                base_image_path="",
                mask_path="/path/to/mask.png"
            )
    
    def test_missing_mask_validation(self):
        """Test that missing mask path raises ValueError."""
        with pytest.raises(ValueError, match="Mask path is required for inpainting"):
            InpaintingRequest(
                prompt="test",
                base_image_path="/path/to/image.png",
                mask_path=""
            )


class TestImg2ImgRequest:
    """Test Img2ImgRequest dataclass."""
    
    def test_img2img_request_creation(self):
        """Test creating an img2img request."""
        request = Img2ImgRequest(
            prompt="transform this",
            base_image_path="/path/to/image.png",
            strength=0.8
        )
        
        assert request.prompt == "transform this"
        assert request.operation == Operation.IMG2IMG
        assert request.base_image_path == "/path/to/image.png"
        assert request.strength == 0.8
    
    def test_default_strength(self):
        """Test default strength value."""
        request = Img2ImgRequest(
            prompt="test",
            base_image_path="/path/to/image.png"
        )
        
        assert request.strength == 0.7
    
    def test_missing_base_image_validation(self):
        """Test that missing base image path raises ValueError."""
        with pytest.raises(ValueError, match="Base image path is required for img2img"):
            Img2ImgRequest(
                prompt="test",
                base_image_path=""
            )
    
    def test_invalid_strength_validation(self):
        """Test that invalid strength values raise ValueError."""
        with pytest.raises(ValueError, match="Strength must be between 0.0 and 1.0"):
            Img2ImgRequest(
                prompt="test",
                base_image_path="/path/to/image.png",
                strength=-0.1
            )
        
        with pytest.raises(ValueError, match="Strength must be between 0.0 and 1.0"):
            Img2ImgRequest(
                prompt="test",
                base_image_path="/path/to/image.png",
                strength=1.1
            )


class TestImageOperationResponse:
    """Test ImageOperationResponse dataclass."""
    
    def test_success_response_creation(self):
        """Test creating a successful response."""
        response = ImageOperationResponse(
            success=True,
            image_path="/path/to/generated.png",
            image_name="generated.png",
            provider="openai",
            operation="generate"
        )
        
        assert response.success is True
        assert response.image_path == "/path/to/generated.png"
        assert response.image_name == "generated.png"
        assert response.provider == "openai"
        assert response.operation == "generate"
        assert response.error_message is None
    
    def test_error_response_creation(self):
        """Test creating an error response."""
        response = ImageOperationResponse(
            success=False,
            error_message="Something went wrong",
            error_type="APIError",
            provider="novelai",
            operation="inpaint"
        )
        
        assert response.success is False
        assert response.error_message == "Something went wrong"
        assert response.error_type == "APIError"
        assert response.provider == "novelai"
        assert response.operation == "inpaint"
        assert response.image_path is None


class TestImageRequestValidator:
    """Test ImageRequestValidator class."""
    
    def test_provider_operation_compatibility(self):
        """Test provider-operation compatibility validation."""
        # OpenAI supports generate and inpaint
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.OPENAI, Operation.GENERATE
        )
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.OPENAI, Operation.INPAINT
        )
        assert not ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.OPENAI, Operation.IMG2IMG
        )
        
        # NovelAI supports all operations
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.NOVELAI, Operation.GENERATE
        )
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.NOVELAI, Operation.INPAINT
        )
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.NOVELAI, Operation.IMG2IMG
        )
        
        # Stability only supports generate
        assert ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.STABILITY, Operation.GENERATE
        )
        assert not ImageRequestValidator.validate_provider_operation_compatibility(
            Provider.STABILITY, Operation.INPAINT
        )
    
    def test_model_validation(self):
        """Test model validation for providers."""
        # Valid OpenAI models
        assert ImageRequestValidator.validate_model_for_provider(
            Provider.OPENAI, OpenAIModel.GPT_IMAGE_1.value
        )
        
        # Invalid model for OpenAI
        assert not ImageRequestValidator.validate_model_for_provider(
            Provider.OPENAI, NovelAIModel.DIFFUSION_4_5_FULL.value
        )
        
        # Valid NovelAI models
        assert ImageRequestValidator.validate_model_for_provider(
            Provider.NOVELAI, NovelAIModel.DIFFUSION_4_5_FULL.value
        )
        
        # None model should be valid (defaults will be used)
        assert ImageRequestValidator.validate_model_for_provider(
            Provider.OPENAI, None
        )
    
    def test_default_model_selection(self):
        """Test default model selection."""
        # OpenAI defaults
        assert ImageRequestValidator.get_default_model(
            Provider.OPENAI, Operation.GENERATE
        ) == OpenAIModel.GPT_IMAGE_1.value
        
        assert ImageRequestValidator.get_default_model(
            Provider.OPENAI, Operation.INPAINT
        ) == OpenAIModel.GPT_IMAGE_1.value
        
        # NovelAI defaults
        assert ImageRequestValidator.get_default_model(
            Provider.NOVELAI, Operation.GENERATE
        ) == NovelAIModel.DIFFUSION_4_5_FULL.value
        
        assert ImageRequestValidator.get_default_model(
            Provider.NOVELAI, Operation.INPAINT
        ) == NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING.value
        
        assert ImageRequestValidator.get_default_model(
            Provider.NOVELAI, Operation.IMG2IMG
        ) == NovelAIModel.DIFFUSION_4_5_FULL.value


class TestFactoryFunctions:
    """Test factory functions for creating requests and responses."""
    
    def test_create_request_from_form_data_generate(self):
        """Test creating generation request from form data."""
        form_data = {
            "prompt": "test prompt",
            "provider": "openai",
            "operation": "generate",
            "width": "1024",
            "height": "1024"
        }
        
        request = create_request_from_form_data(form_data)
        
        assert isinstance(request, ImageGenerationRequest)
        assert request.prompt == "test prompt"
        assert request.provider == Provider.OPENAI
        assert request.operation == Operation.GENERATE
    
    def test_create_request_from_form_data_inpaint(self):
        """Test creating inpainting request from form data."""
        form_data = {
            "prompt": "inpaint this",
            "provider": "novelai",
            "operation": "inpaint",
            "base_image_path": "/path/to/image.png",
            "mask_path": "/path/to/mask.png"
        }
        
        request = create_request_from_form_data(form_data)
        
        assert isinstance(request, InpaintingRequest)
        assert request.prompt == "inpaint this"
        assert request.provider == Provider.NOVELAI
        assert request.operation == Operation.INPAINT
        assert request.base_image_path == "/path/to/image.png"
        assert request.mask_path == "/path/to/mask.png"
    
    def test_create_request_from_form_data_img2img(self):
        """Test creating img2img request from form data."""
        form_data = {
            "prompt": "transform this",
            "provider": "novelai",
            "operation": "img2img",
            "base_image_path": "/path/to/image.png",
            "strength": "0.8"
        }
        
        request = create_request_from_form_data(form_data)
        
        assert isinstance(request, Img2ImgRequest)
        assert request.prompt == "transform this"
        assert request.provider == Provider.NOVELAI
        assert request.operation == Operation.IMG2IMG
        assert request.base_image_path == "/path/to/image.png"
        assert request.strength == 0.8
    
    def test_create_request_invalid_provider_operation(self):
        """Test error when provider doesn't support operation."""
        form_data = {
            "prompt": "test",
            "provider": "openai",
            "operation": "img2img"
        }
        
        with pytest.raises(ValueError, match="Provider openai does not support operation img2img"):
            create_request_from_form_data(form_data)
    
    def test_create_success_response(self):
        """Test creating success response."""
        response = create_success_response(
            image_path="/path/to/image.png",
            image_name="image.png",
            provider=Provider.OPENAI,
            operation=Operation.GENERATE,
            revised_prompt="revised prompt"
        )
        
        assert response.success is True
        assert response.image_path == "/path/to/image.png"
        assert response.image_name == "image.png"
        assert response.provider == "openai"
        assert response.operation == "generate"
        assert response.revised_prompt == "revised prompt"
        assert response.timestamp is not None
    
    def test_create_error_response(self):
        """Test creating error response."""
        error = ValueError("Test error")
        
        response = create_error_response(
            error=error,
            provider=Provider.NOVELAI,
            operation=Operation.INPAINT,
            error_message="Custom error message"
        )
        
        assert response.success is False
        assert response.error_message == "Custom error message"
        assert response.error_type == "ValueError"
        assert response.provider == "novelai"
        assert response.operation == "inpaint"
        assert response.timestamp is not None