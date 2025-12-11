"""
Data models for unified image generation API with strict typing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator
from dynamic_prompts import GridDynamicPromptInfo


class Provider(str, Enum):
    """Supported image generation providers."""

    OPENAI = "openai"
    NOVELAI = "novelai"
    STABILITY = "stability"


class Operation(str, Enum):
    """Supported image operations."""

    GENERATE = "generate"
    INPAINT = "inpaint"
    IMG2IMG = "img2img"


class Quality(str, Enum):
    """Image quality settings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NovelAIModel(str, Enum):
    """NovelAI model options."""

    DIFFUSION_4_5_FULL = "nai-diffusion-4-5-full"
    DIFFUSION_4_5_FULL_INPAINTING = "nai-diffusion-4-5-full-inpainting"
    DIFFUSION_3 = "nai-diffusion-3"


class OpenAIModel(str, Enum):
    """OpenAI model options."""

    GPT_IMAGE_1 = "gpt-image-1"


class VibeReference(BaseModel):
    """Reference to a vibe for image generation."""
    
    encoded_data: str = Field(..., description="Base64 encoded vibe data")
    reference_strength: float = Field(..., ge=0.0, le=1.0, description="Reference strength 0.0-1.0")
    
    @field_validator("encoded_data")
    @classmethod
    def validate_encoded_data(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Encoded data cannot be empty")
        return v


@dataclass
class ImageGenerationRequest:
    """Base request model for image generation operations."""

    prompt: str
    provider: Provider = Provider.OPENAI
    operation: Operation = Operation.GENERATE
    negative_prompt: str | None = None
    width: int = 1024
    height: int = 1024
    quality: Quality = Quality.HIGH
    model: str | None = None
    character_prompts: list[dict[str, str]] | None = None
    variety: bool = False
    seed: int = (0,)
    grid_dynamic_prompt: GridDynamicPromptInfo | None = None

    def __post_init__(self):
        """Validate prompt and dimensions after object initialization."""
        if not self.prompt or not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive integers")

        # Validate dimensions for specific providers
        if self.provider == Provider.OPENAI:
            valid_sizes = [(1024, 1024), (1536, 1024), (1024, 1536)]
            if (self.width, self.height) not in valid_sizes:
                raise ValueError(
                    f"Invalid dimensions for OpenAI: {self.width}x{self.height}"
                )


@dataclass
class InpaintingRequest(ImageGenerationRequest):
    """Request model for inpainting operations."""

    base_image_path: str = ""
    mask_path: str = ""
    operation: Operation = Operation.INPAINT

    def __post_init__(self):
        """Validate base image and mask paths for inpainting operation."""
        super().__post_init__()

        if not self.base_image_path or not self.base_image_path.strip():
            raise ValueError("Base image path is required for inpainting")

        if not self.mask_path or not self.mask_path.strip():
            raise ValueError("Mask path is required for inpainting")


@dataclass
class Img2ImgRequest(ImageGenerationRequest):
    """Request model for img2img operations."""

    base_image_path: str = ""
    strength: float = 0.7
    operation: Operation = Operation.IMG2IMG

    def __post_init__(self):
        """Validate base image path and strength parameter for img2img operation."""
        super().__post_init__()

        if not self.base_image_path or not self.base_image_path.strip():
            raise ValueError("Base image path is required for img2img")

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")


@dataclass
class ImageOperationResponse:
    """Unified response model for all image operations."""

    success: bool
    image_path: str | None = None
    image_name: str | None = None
    revised_prompt: str | None = None
    error_message: str | None = None
    error_type: str | None = None
    provider: str | None = None
    operation: str | None = None
    timestamp: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageRequestValidator:
    """Validates image generation requests for provider compatibility and model support."""

    @staticmethod
    def validate_provider_operation_compatibility(
        provider: Provider, operation: Operation
    ) -> bool:
        """Check if the specified provider supports the requested operation type."""
        compatibility_matrix = {
            Provider.OPENAI: [Operation.GENERATE, Operation.INPAINT],
            Provider.NOVELAI: [
                Operation.GENERATE,
                Operation.INPAINT,
                Operation.IMG2IMG,
            ],
            Provider.STABILITY: [Operation.GENERATE],
        }

        return operation in compatibility_matrix.get(provider, [])

    @staticmethod
    def validate_model_for_provider(provider: Provider, model: str | None) -> bool:
        """Validate that the specified model is available for the provider."""
        if model is None:
            return True  # Default models will be used

        provider_models = {
            Provider.OPENAI: [m.value for m in OpenAIModel],
            Provider.NOVELAI: [m.value for m in NovelAIModel],
            Provider.STABILITY: [],  # Add stability models when implemented
        }

        return model in provider_models.get(provider, [])

    @staticmethod
    def get_default_model(provider: Provider, operation: Operation) -> str:
        """Get the default model name for the specified provider and operation."""
        defaults = {
            Provider.OPENAI: {
                Operation.GENERATE: OpenAIModel.GPT_IMAGE_1.value,
                Operation.INPAINT: OpenAIModel.GPT_IMAGE_1.value,
            },
            Provider.NOVELAI: {
                Operation.GENERATE: NovelAIModel.DIFFUSION_4_5_FULL.value,
                Operation.INPAINT: NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING.value,
                Operation.IMG2IMG: NovelAIModel.DIFFUSION_4_5_FULL.value,
            },
        }

        return defaults.get(provider, {}).get(operation, "")


def create_request_from_form_data(
    form_data: dict[str, Any],
) -> ImageGenerationRequest | InpaintingRequest | Img2ImgRequest:
    """Create typed request object from HTML form data with validation."""
    # Handle empty operation field - default to GENERATE for regular image generation
    operation_value = form_data.get("operation", Operation.GENERATE.value)
    if not operation_value or operation_value.strip() == "":
        operation_value = Operation.GENERATE.value
    operation = Operation(operation_value)
    provider = Provider(form_data.get("provider", Provider.OPENAI.value))

    # Validate provider-operation compatibility
    if not ImageRequestValidator.validate_provider_operation_compatibility(
        provider, operation
    ):
        raise ValueError(
            f"Provider {provider.value} does not support operation {operation.value}"
        )

    # Extract character prompts from form data
    character_prompts: list[dict[str, str]] = []
    char_index = 0
    while True:
        positive_key = f"character_prompts[{char_index}][positive]"
        negative_key = f"character_prompts[{char_index}][negative]"

        positive_prompt = form_data.get(positive_key, "").strip()
        negative_prompt = form_data.get(negative_key, "").strip()

        # If no positive prompt found, we've reached the end
        if positive_key not in form_data:
            break

        # Only add character if it has at least a positive prompt
        if positive_prompt:
            character_prompts.append(
                {"positive": positive_prompt, "negative": negative_prompt}
            )

        char_index += 1

    # Parse size from form data (format: "widthxheight")
    size_str = form_data.get("size", "1024x1024")
    try:
        width, height = map(int, size_str.split("x"))
    except (ValueError, AttributeError):
        # Fallback to default size if parsing fails
        width, height = 1024, 1024

    # Extract and prepare parameters
    prompt = form_data.get("prompt", "")
    negative_prompt = form_data.get("negative_prompt")
    quality = Quality(form_data.get("quality", Quality.HIGH.value))
    model = form_data.get("model")
    character_prompts_final = character_prompts if character_prompts else None

    # Extract seed from form data, default to 0 if not provided or invalid
    seed = 0
    try:
        seed_str = form_data.get("seed", "0")
        seed = int(seed_str) if seed_str else 0
    except (ValueError, TypeError):
        seed = 0

    # Extract variety flag from form data
    variety = form_data.get("variety", "false").lower() == "on"

    # Set default model if not provided
    if not model:
        model = ImageRequestValidator.get_default_model(provider, operation)

    # Validate model compatibility
    if not ImageRequestValidator.validate_model_for_provider(provider, model):
        raise ValueError(
            f"Model {model} is not compatible with provider {provider.value}"
        )

    # Create appropriate request object based on operation
    if operation == Operation.INPAINT:
        return InpaintingRequest(
            prompt=prompt,
            provider=provider,
            operation=operation,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            quality=quality,
            model=model,
            character_prompts=character_prompts_final,
            variety=variety,
            seed=seed,
            base_image_path=form_data.get("base_image_path", ""),
            mask_path=form_data.get("mask_path", ""),
        )
    elif operation == Operation.IMG2IMG:
        return Img2ImgRequest(
            prompt=prompt,
            provider=provider,
            operation=operation,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            quality=quality,
            model=model,
            character_prompts=character_prompts_final,
            variety=variety,
            seed=seed,
            base_image_path=form_data.get("base_image_path", ""),
            strength=float(form_data.get("strength", 0.7)),
        )
    else:
        return ImageGenerationRequest(
            prompt=prompt,
            provider=provider,
            operation=operation,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            quality=quality,
            model=model,
            character_prompts=character_prompts_final,
            variety=variety,
            seed=seed,
        )


def create_success_response(
    image_path: str,
    image_name: str,
    provider: Provider,
    operation: Operation,
    revised_prompt: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ImageOperationResponse:
    """Create a successful image operation response with metadata."""
    import time

    return ImageOperationResponse(
        success=True,
        image_path=image_path,
        image_name=image_name,
        revised_prompt=revised_prompt,
        provider=provider.value,
        operation=operation.value,
        timestamp=int(time.time()),
        metadata=metadata or {},
    )


def create_error_response(
    error: Exception,
    provider: Provider,
    operation: Operation,
    error_message: str | None = None,
) -> ImageOperationResponse:
    """Create an error response with exception details and context."""
    import time

    return ImageOperationResponse(
        success=False,
        error_message=error_message or str(error),
        error_type=type(error).__name__,
        provider=provider.value,
        operation=operation.value,
        timestamp=int(time.time()),
    )
