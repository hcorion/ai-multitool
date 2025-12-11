"""
Pydantic models for NovelAI vibe encoding system.

This module defines the data models for vibe collections, encodings, and related
validation logic for the vibe encoding feature.
"""

import uuid
from typing import Dict

from pydantic import BaseModel, Field, field_validator


class VibeEncoding(BaseModel):
    """Single vibe encoding at a specific strength."""
    
    encoding_strength: float = Field(..., description="Encoding strength (1.0, 0.85, 0.7, 0.5, 0.35)")
    encoded_data: str = Field(..., description="Base64 encoded vibe data")
    
    @field_validator("encoding_strength")
    @classmethod
    def validate_encoding_strength(cls, v: float) -> float:
        """Validate that encoding strength is one of the allowed values."""
        valid_strengths = {1.0, 0.85, 0.7, 0.5, 0.35}
        if v not in valid_strengths:
            raise ValueError(f"Encoding strength must be one of {valid_strengths}")
        return v


class VibeCollection(BaseModel):
    """Complete vibe collection with all encodings and preview images."""
    
    guid: str = Field(..., description="Unique identifier for the collection")
    name: str = Field(..., description="User-provided name")
    model: str = Field(..., description="Model used for encoding")
    created_at: int = Field(..., description="Unix timestamp of creation")
    source_image_path: str = Field(..., description="Path to original source image")
    encodings: Dict[str, VibeEncoding] = Field(..., description="Encodings keyed by strength as string")
    preview_images: Dict[str, str] = Field(..., description="Preview image paths keyed by 'enc{X}_ref{Y}'")
    
    @field_validator("guid")
    @classmethod
    def validate_guid(cls, v: str) -> str:
        """Validate that GUID is a valid UUID format."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("GUID must be a valid UUID")
        return v
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @field_validator("encodings")
    @classmethod
    def validate_encodings(cls, v: Dict[str, VibeEncoding]) -> Dict[str, VibeEncoding]:
        """Validate that all required encoding strengths are present."""
        required_strengths = {"1.0", "0.85", "0.7", "0.5", "0.35"}
        provided_strengths = set(v.keys())
        
        if provided_strengths != required_strengths:
            missing = required_strengths - provided_strengths
            extra = provided_strengths - required_strengths
            error_parts = []
            if missing:
                error_parts.append(f"missing: {missing}")
            if extra:
                error_parts.append(f"extra: {extra}")
            raise ValueError(f"Invalid encoding strengths - {', '.join(error_parts)}")
        
        # Validate that string keys match the encoding strength values
        for key, encoding in v.items():
            if str(encoding.encoding_strength) != key:
                raise ValueError(f"Encoding key '{key}' does not match strength '{encoding.encoding_strength}'")
        
        return v


class VibeCollectionSummary(BaseModel):
    """Summary information for vibe collection listing."""
    
    guid: str = Field(..., description="Unique identifier for the collection")
    name: str = Field(..., description="User-provided name")
    model: str = Field(..., description="Model used for encoding")
    created_at: int = Field(..., description="Unix timestamp of creation")
    preview_image: str = Field(..., description="Path to representative preview image")


class VibeReference(BaseModel):
    """Reference to a vibe for image generation."""
    
    encoded_data: str = Field(..., description="Base64 encoded vibe data")
    reference_strength: float = Field(..., ge=0.0, le=1.0, description="Reference strength 0.0-1.0")