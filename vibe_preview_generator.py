"""
Vibe preview generation system for NovelAI vibe collections.

This module provides the VibePreviewGenerator class that generates preview images
showing the effect of different encoding and reference strength combinations.
"""

import os
from typing import Callable, Optional, Dict, Tuple
from PIL import Image as PILImage
import io

from novelai_client import NovelAIClient, NovelAIClientError, NovelAIAPIError
from vibe_models import VibeCollection, VibeReference
from vibe_storage import VibeStorageManager


class VibePreviewGenerator:
    """Generates preview images for vibe collections at all strength combinations."""
    
    # Preview generation constants
    PREVIEW_WIDTH = 512
    PREVIEW_HEIGHT = 768
    PREVIEW_SEED = 42
    PREVIEW_PROMPT = "1girl, portrait, masterpiece, best quality, very aesthetic"
    PREVIEW_PROMPT_NEGATIVE = "nsfw, ugly, nipples, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, bad quality, jpeg artifacts, signature, watermark, username, blurry, very displeasing"
    
    # Standard strength values
    ENCODING_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35]
    REFERENCE_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35]
    
    def __init__(self, novelai_client: NovelAIClient, storage_manager: VibeStorageManager):
        """Initialize the vibe preview generator.
        
        Args:
            novelai_client: NovelAI client for API calls
            storage_manager: Storage manager for file operations
        """
        self.novelai_client = novelai_client
        self.storage_manager = storage_manager
    
    def generate_previews(
        self,
        username: str,
        collection: VibeCollection,
        progress_callback: Optional[Callable[[int, int, str, Optional[str]], None]] = None
    ) -> Dict[Tuple[float, float], str]:
        """Generate all 25 preview images for a vibe collection.
        
        Args:
            username: Username for file storage
            collection: VibeCollection to generate previews for
            progress_callback: Optional callback for progress updates (step, total, message, preview_url)
            
        Returns:
            Dictionary mapping (enc_strength, ref_strength) tuples to web-relative file paths
            
        Raises:
            NovelAIAPIError: If the NovelAI API returns an error
            NovelAIClientError: If there's a client-side error
            ValueError: If validation fails
        """
        # Validate collection has all required encodings
        required_strengths = {str(s) for s in self.ENCODING_STRENGTHS}
        available_strengths = set(collection.encodings.keys())
        if required_strengths != available_strengths:
            raise ValueError(f"Collection missing required encodings. Expected: {required_strengths}, Got: {available_strengths}")
        
        # Get collection directory (absolute path for file operations)
        collection_dir = self.storage_manager.get_collection_directory(username, collection.guid)
        os.makedirs(collection_dir, exist_ok=True)
        
        # Web-relative path prefix for stored URLs
        web_path_prefix = f"/static/vibes/{username}/{collection.guid}"
        
        # Generate all combinations
        preview_paths = {}
        total_combinations = len(self.ENCODING_STRENGTHS) * len(self.REFERENCE_STRENGTHS)
        step = 0
        
        for enc_strength in self.ENCODING_STRENGTHS:
            for ref_strength in self.REFERENCE_STRENGTHS:
                step += 1
                
                try:
                    # Generate the preview image (returns absolute paths for file ops)
                    image_filename, thumb_filename = self._generate_single_preview(
                        collection, enc_strength, ref_strength, collection_dir
                    )
                    
                    # Convert to web-relative paths for storage
                    web_image_path = f"{web_path_prefix}/{image_filename}"
                    web_thumb_path = f"{web_path_prefix}/{thumb_filename}"
                    
                    # Store the web-relative paths
                    key = (enc_strength, ref_strength)
                    preview_paths[key] = web_image_path
                    
                    # Update collection's preview_images dict with web-relative paths
                    preview_key = f"enc{enc_strength}_ref{ref_strength}"
                    collection.preview_images[preview_key] = web_image_path
                    
                    # Notify progress with the generated thumbnail URL
                    if progress_callback:
                        progress_callback(
                            step,
                            total_combinations,
                            f"Generated preview {enc_strength}x{ref_strength}",
                            web_thumb_path
                        )
                    
                except (NovelAIAPIError, NovelAIClientError) as e:
                    # Re-raise API errors with context
                    if isinstance(e, NovelAIAPIError):
                        raise NovelAIAPIError(
                            e.status_code, 
                            f"Failed to generate preview {enc_strength}x{ref_strength}: {e.message}"
                        )
                    else:
                        raise NovelAIClientError(
                            f"Failed to generate preview {enc_strength}x{ref_strength}: {str(e)}"
                        )
        
        # Save updated collection with preview paths
        self.storage_manager.save_collection(username, collection)
        
        return preview_paths
    
    def _generate_single_preview(
        self, 
        collection: VibeCollection, 
        enc_strength: float, 
        ref_strength: float,
        collection_dir: str
    ) -> Tuple[str, str]:
        """Generate a single preview image for the given strength combination.
        
        Args:
            collection: VibeCollection containing the encodings
            enc_strength: Encoding strength to use
            ref_strength: Reference strength to use
            collection_dir: Directory to save the preview files
            
        Returns:
            Tuple of (image_filename, thumbnail_filename) - just the filenames, not full paths
            
        Raises:
            NovelAIAPIError: If the NovelAI API returns an error
            NovelAIClientError: If there's a client-side error
        """
        # Get the encoded vibe data for this encoding strength
        encoding_key = str(enc_strength)
        encoding = collection.encodings.get(encoding_key)
        if encoding is None:
            raise ValueError(f"No encoding found for strength {enc_strength}")
        
        # Create vibe reference
        vibe_ref = VibeReference(
            encoded_data=encoding.encoded_data,
            reference_strength=ref_strength
        )
        
        # Generate the image using NovelAI
        image_bytes = self.novelai_client.generate_image(
            prompt=self.PREVIEW_PROMPT,
            negative_prompt=self.PREVIEW_PROMPT_NEGATIVE,
            width=self.PREVIEW_WIDTH,
            height=self.PREVIEW_HEIGHT,
            seed=self.PREVIEW_SEED,
            vibes=[vibe_ref]
        )
        
        # Save the full PNG image
        image_filename = f"preview_enc{enc_strength}_ref{ref_strength}.png"
        image_path = os.path.join(collection_dir, image_filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        # Create and save JPG thumbnail
        thumb_filename = f"preview_enc{enc_strength}_ref{ref_strength}.thumb.jpg"
        thumb_path = os.path.join(collection_dir, thumb_filename)
        
        self._create_thumbnail(image_bytes, thumb_path)
        
        # Return just filenames, caller will construct web paths
        return image_filename, thumb_filename
    
    def _create_thumbnail(self, image_bytes: bytes, thumb_path: str) -> None:
        """Create a JPG thumbnail from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            thumb_path: Path to save the thumbnail
            
        Raises:
            ValueError: If thumbnail creation fails
        """
        try:
            # Open the image
            image = PILImage.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (for JPG compatibility)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create thumbnail (maintains aspect ratio)
            # Use a reasonable thumbnail size
            thumbnail_size = (256, 384)  # Half the preview size
            image.thumbnail(thumbnail_size, PILImage.Resampling.LANCZOS)
            
            # Save as JPG with good quality
            image.save(thumb_path, 'JPEG', quality=85, optimize=True)
            
        except Exception as e:
            raise ValueError(f"Failed to create thumbnail: {str(e)}")