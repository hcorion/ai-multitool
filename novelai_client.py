"""
NovelAI API client for image generation operations.

This module provides a clean abstraction for interacting with the NovelAI API,
supporting text-to-image generation, inpainting, and img2img operations.
"""

import base64
import io
import json
import math
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

import requests
from PIL import Image as PILImage


class NovelAIModel(str, Enum):
    """Available NovelAI models for image generation."""
    DIFFUSION_4_5_FULL = "nai-diffusion-4-5-full"
    DIFFUSION_4_5_FULL_INPAINTING = "nai-diffusion-4-5-full-inpainting"


class NovelAIAction(str, Enum):
    """Available NovelAI actions for image operations."""
    GENERATE = "generate"
    INPAINT = "infill"
    IMG2IMG = "img2img"


class NovelAIClientError(Exception):
    """Base exception for NovelAI client errors."""
    pass


class NovelAIAPIError(NovelAIClientError):
    """API-specific errors from NovelAI."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"NovelAI API Error {status_code}: {message}")


@dataclass
class NovelAIGenerationPayload:
    """Payload structure for NovelAI image generation requests."""
    input: str
    model: NovelAIModel = NovelAIModel.DIFFUSION_4_5_FULL
    action: NovelAIAction = NovelAIAction.GENERATE
    parameters: Dict[str, Any] = field(default_factory=dict)


class NovelAIClient:
    """Client for interacting with the NovelAI API."""
    
    def __init__(self, api_key: str, base_url: str = "https://image.novelai.net"):
        """
        Initialize the NovelAI client.
        
        Args:
            api_key: NovelAI API key for authentication
            base_url: Base URL for the NovelAI API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json"
        })
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> requests.Response:
        """
        Make a request to the NovelAI API.
        
        Args:
            endpoint: API endpoint to call
            payload: Request payload
            
        Returns:
            Response object from the API
            
        Raises:
            NovelAIAPIError: If the API returns an error response
            NovelAIClientError: If there's a network or client error
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.post(url, data=json.dumps(payload))
            
            if response.status_code != 200:
                try:
                    error_body = response.json()
                    error_message = error_body.get('message', 'Unknown error')
                except (json.JSONDecodeError, KeyError):
                    error_message = f"HTTP {response.status_code}"
                
                raise NovelAIAPIError(response.status_code, error_message)
            
            return response
            
        except NovelAIAPIError:
            # Re-raise API errors as-is
            raise
        except requests.RequestException as e:
            raise NovelAIClientError(f"Network error: {str(e)}")
        except Exception as e:
            raise NovelAIClientError(f"Network error: {str(e)}")
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: int = 0,
        steps: int = 28,
        scale: float = 6.0,
        character_prompts: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> bytes:
        """
        Generate an image using NovelAI's text-to-image model.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to avoid certain elements
            width: Image width in pixels
            height: Image height in pixels
            seed: Random seed for reproducible generation
            steps: Number of diffusion steps (max 28 for free tier)
            scale: CFG scale for prompt adherence
            character_prompts: List of character-specific prompts
            **kwargs: Additional parameters for the generation
            
        Returns:
            Raw image bytes from the generated image
            
        Raises:
            NovelAIAPIError: If the API returns an error
            NovelAIClientError: If there's a client-side error
        """
        # Build character captions
        char_captions_positive = []
        char_captions_negative = []
        
        if character_prompts:
            for char_prompt in character_prompts:
                positive_prompt = char_prompt.get("positive", "")
                if positive_prompt and str(positive_prompt).strip():
                    char_captions_positive.append({
                        "centers": [{"x": 0, "y": 0}],
                        "char_caption": str(positive_prompt).strip(),
                    })
                
                negative_prompt = char_prompt.get("negative", "")
                if negative_prompt and str(negative_prompt).strip():
                    char_captions_negative.append({
                        "centers": [{"x": 0, "y": 0}],
                        "char_caption": str(negative_prompt).strip(),
                    })
        
        # Build the request payload
        parameters = {
            "add_original_image": True,
            "autoSmea": False,
            "cfg_rescale": 0.4,
            "controlnet_strength": 1,
            "deliberate_euler_ancestral_bug": False,
            "dynamic_thresholding": True,
            "width": width,
            "height": height,
            "inpaintImg2ImgStrength": 1,
            "legacy": False,
            "legacy_uc": False,
            "legacy_v3_extend": False,
            "n_samples": 1,
            "noise": 0.2,
            "noise_schedule": "karras",
            "normalize_reference_strength_multiple": True,
            "params_version": 3,
            "prefer_brownian": True,
            "qualityToggle": True,
            "sampler": "k_euler_ancestral",
            "scale": scale,
            "steps": steps,
            "strength": 0.6,
            "ucPreset": 4,
            "seed": seed,
            "v4_prompt": {
                "caption": {
                    "base_caption": prompt,
                    "char_captions": char_captions_positive,
                },
                "use_coords": False,
                "use_order": True,
            },
            "v4_negative_prompt": {
                "caption": {
                    "base_caption": negative_prompt or "",
                    "char_captions": char_captions_negative,
                },
                "use_coords": False,
                "use_order": True,
            },
        }
        
        # Override with any additional parameters
        parameters.update(kwargs)
        
        payload = {
            "action": NovelAIAction.GENERATE.value,
            "model": NovelAIModel.DIFFUSION_4_5_FULL.value,
            "parameters": parameters
        }
        
        response = self._make_request("ai/generate-image", payload)
        
        # Extract image from ZIP response
        try:
            zipped_file = zipfile.ZipFile(io.BytesIO(response.content))
            image_bytes = zipped_file.read(zipped_file.infolist()[0])
            return image_bytes
        except (zipfile.BadZipFile, IndexError) as e:
            raise NovelAIClientError(f"Failed to extract image from response: {str(e)}")
    
    def upscale_image(
        self,
        image_bytes: bytes,
        original_width: int,
        original_height: int,
        scale: int = 4
    ) -> bytes:
        """
        Upscale an image using NovelAI's upscaling service.
        
        Args:
            image_bytes: Raw image bytes to upscale
            original_width: Original image width
            original_height: Original image height
            scale: Upscaling factor (default: 4)
            
        Returns:
            Raw bytes of the upscaled image
            
        Raises:
            NovelAIAPIError: If the API returns an error
            NovelAIClientError: If there's a client-side error
        """
        # 640x640 images cost 0 Anlas with Opus, so resize down to that res before sending it to upscale
        max_resolution = 640 * 640
        
        image_buffer = io.BytesIO(image_bytes)
        
        if original_width * original_height > max_resolution:
            resized_image = PILImage.open(image_buffer)
            resized_width = int(
                math.floor(math.sqrt(max_resolution * (original_width / original_height)))
            )
            resized_height = int(
                math.floor(math.sqrt(max_resolution * (original_height / original_width)))
            )

            resized_image.thumbnail(
                (resized_width, resized_height), PILImage.Resampling.LANCZOS
            )
            processed_image_bytes = io.BytesIO()
            resized_image.save(processed_image_bytes, format="PNG")
            processed_image_bytes.seek(0)
        else:
            processed_image_bytes = image_buffer
            resized_height = original_height
            resized_width = original_width

        # Prepare upscale request
        data = {
            "scale": scale,
            "width": resized_width,
            "height": resized_height,
            "image": base64.b64encode(processed_image_bytes.getbuffer()).decode("ascii"),
        }
        
        # Make upscale request to different endpoint
        upscale_url = "https://api.novelai.net/ai/upscale"
        
        try:
            response = self.session.post(upscale_url, json=data)
            
            if response.status_code != 200:
                try:
                    error_body = response.json()
                    error_message = error_body.get('message', 'Unknown error')
                except (json.JSONDecodeError, KeyError):
                    error_message = f"HTTP {response.status_code}"
                
                raise NovelAIAPIError(response.status_code, error_message)
            
            # Extract upscaled image from ZIP response
            try:
                zipped_file = zipfile.ZipFile(io.BytesIO(response.content))
                upscaled_image_bytes = zipped_file.read(zipped_file.infolist()[0])
                return upscaled_image_bytes
            except (zipfile.BadZipFile, IndexError) as e:
                raise NovelAIClientError(f"Failed to extract upscaled image from response: {str(e)}")
                
        except NovelAIAPIError:
            # Re-raise API errors as-is
            raise
        except requests.RequestException as e:
            raise NovelAIClientError(f"Network error during upscale: {str(e)}")
        except Exception as e:
            raise NovelAIClientError(f"Error during upscale: {str(e)}")