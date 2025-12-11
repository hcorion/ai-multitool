"""
Vibe encoding service for NovelAI vibe collections.

This module provides the VibeEncoderService class that orchestrates the encoding
of images at multiple strength levels and coordinates with the NovelAI API.
"""

import os
import time
from typing import Callable, Optional

from novelai_client import NovelAIClient, NovelAIClientError, NovelAIAPIError
from vibe_models import VibeCollection, VibeEncoding
from vibe_storage import VibeStorageManager


class VibeEncoderService:
    """Service for encoding images into vibe collections at multiple strength levels."""
    
    # Standard encoding strengths as defined in the design
    ENCODING_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35]
    
    def __init__(self, novelai_client: NovelAIClient, storage_manager: VibeStorageManager):
        """Initialize the vibe encoder service.
        
        Args:
            novelai_client: NovelAI client for API calls
            storage_manager: Storage manager for persisting vibe collections
        """
        self.novelai_client = novelai_client
        self.storage_manager = storage_manager
    
    def encode_vibe(
        self, 
        username: str,
        image_path: str, 
        name: str, 
        model: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> VibeCollection:
        """Encode image at all strength levels and return collection.
        
        Args:
            username: Username for the vibe collection
            image_path: Path to the source image file
            name: User-provided name for the vibe collection
            model: Model name used for encoding
            progress_callback: Optional callback for progress updates (step, total, message)
            
        Returns:
            VibeCollection with all encodings
            
        Raises:
            FileNotFoundError: If the source image file doesn't exist
            NovelAIAPIError: If the NovelAI API returns an error
            NovelAIClientError: If there's a client-side error
            ValueError: If validation fails
        """
        # Validate inputs
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")
        
        if not name or not name.strip():
            raise ValueError("Vibe collection name cannot be empty")
        
        if not model or not model.strip():
            raise ValueError("Model name cannot be empty")
        
        # Generate GUID for the collection
        guid = VibeStorageManager.generate_guid()
        
        # Read the source image
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
        except IOError as e:
            raise FileNotFoundError(f"Failed to read source image: {str(e)}")
        
        # Encode at all strength levels
        encodings = {}
        total_steps = len(self.ENCODING_STRENGTHS)
        
        for step, strength in enumerate(self.ENCODING_STRENGTHS, 1):
            if progress_callback:
                progress_callback(step, total_steps, f"Encoding at strength {strength}")
            
            try:
                encoded_data = self._call_encode_api(image_bytes, strength, model)
                
                # Create VibeEncoding object
                encoding = VibeEncoding(
                    encoding_strength=strength,
                    encoded_data=encoded_data
                )
                
                # Store with string key for JSON serialization
                encodings[str(strength)] = encoding
                
            except (NovelAIAPIError, NovelAIClientError) as e:
                # Re-raise API errors with context
                if isinstance(e, NovelAIAPIError):
                    raise NovelAIAPIError(e.status_code, f"Failed to encode at strength {strength}: {e.message}")
                else:
                    raise NovelAIClientError(f"Failed to encode at strength {strength}: {str(e)}")
        
        # Create the vibe collection
        collection = VibeCollection(
            guid=guid,
            name=name.strip(),
            model=model,
            created_at=int(time.time()),
            source_image_path=image_path,
            encodings=encodings,
            preview_images={}  # Will be populated by preview generator
        )
        
        # Save the collection
        try:
            self.storage_manager.save_collection(username, collection)
        except Exception as e:
            raise ValueError(f"Failed to save vibe collection: {str(e)}")
        
        return collection
    
    def encode_vibe_with_guid(
        self, 
        username: str,
        guid: str,
        image_path: str, 
        name: str, 
        model: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> VibeCollection:
        """Encode image at all strength levels with a pre-generated GUID.
        
        Args:
            username: Username for the vibe collection
            guid: Pre-generated GUID for the collection
            image_path: Path to the source image file
            name: User-provided name for the vibe collection
            model: Model name used for encoding
            progress_callback: Optional callback for progress updates (step, total, message)
            
        Returns:
            VibeCollection with all encodings
            
        Raises:
            FileNotFoundError: If the source image file doesn't exist
            NovelAIAPIError: If the NovelAI API returns an error
            NovelAIClientError: If there's a client-side error
            ValueError: If validation fails
        """
        # Validate inputs
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")
        
        if not name or not name.strip():
            raise ValueError("Vibe collection name cannot be empty")
        
        if not model or not model.strip():
            raise ValueError("Model name cannot be empty")
        
        if not guid or not guid.strip():
            raise ValueError("GUID cannot be empty")
        
        # Read the source image
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
        except IOError as e:
            raise FileNotFoundError(f"Failed to read source image: {str(e)}")
        
        # Encode at all strength levels
        encodings = {}
        total_steps = len(self.ENCODING_STRENGTHS)
        
        for step, strength in enumerate(self.ENCODING_STRENGTHS, 1):
            if progress_callback:
                progress_callback(step, total_steps, f"Encoding at strength {strength}")
            
            try:
                encoded_data = self._call_encode_api(image_bytes, strength, model)
                
                # Create VibeEncoding object
                encoding = VibeEncoding(
                    encoding_strength=strength,
                    encoded_data=encoded_data
                )
                
                # Store with string key for JSON serialization
                encodings[str(strength)] = encoding
                
            except (NovelAIAPIError, NovelAIClientError) as e:
                # Re-raise API errors with context
                if isinstance(e, NovelAIAPIError):
                    raise NovelAIAPIError(e.status_code, f"Failed to encode at strength {strength}: {e.message}")
                else:
                    raise NovelAIClientError(f"Failed to encode at strength {strength}: {str(e)}")
        
        # Create the vibe collection with the provided GUID
        collection = VibeCollection(
            guid=guid,
            name=name.strip(),
            model=model,
            created_at=int(time.time()),
            source_image_path=image_path,
            encodings=encodings,
            preview_images={}  # Will be populated by preview generator
        )
        
        # Save the collection
        try:
            self.storage_manager.save_collection(username, collection)
        except Exception as e:
            raise ValueError(f"Failed to save vibe collection: {str(e)}")
        
        return collection
    
    def _call_encode_api(self, image_bytes: bytes, strength: float, model: str) -> str:
        """Call NovelAI encode-vibe endpoint.
        
        Args:
            image_bytes: Raw image bytes to encode
            strength: Encoding strength (information_extracted parameter)
            model: Model name for encoding
            
        Returns:
            encoded_data as base64 string
            
        Raises:
            NovelAIAPIError: If the API returns an error
            NovelAIClientError: If there's a client-side error
        """
        try:
            encoded_data = self.novelai_client.encode_vibe(
                image_bytes=image_bytes,
                information_extracted=strength,
                model=model
            )
            
            # Validate that we got a non-empty response
            if not encoded_data or not encoded_data.strip():
                raise NovelAIClientError("Received empty encoded data from API")
            
            return encoded_data
            
        except (NovelAIAPIError, NovelAIClientError):
            # Re-raise NovelAI errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions as client errors
            raise NovelAIClientError(f"Unexpected error during encoding: {str(e)}")