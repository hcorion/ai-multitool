"""
Property-based tests for vibe preview generation system.

This module contains property-based tests to validate the correctness of
vibe preview generation operations and image properties.
"""

import os
import tempfile
import uuid
from unittest.mock import Mock
from PIL import Image as PILImage
import io

import pytest
from hypothesis import given, strategies as st

from novelai_client import NovelAIClient
from vibe_models import VibeCollection, VibeEncoding
from vibe_storage import VibeStorageManager
from vibe_preview_generator import VibePreviewGenerator


# Test data generators
@st.composite
def vibe_collection_with_encodings(draw):
    """Generate a VibeCollection with all required encodings."""
    guid = str(uuid.uuid4())
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    model = draw(st.text(min_size=1, max_size=50))
    created_at = draw(st.integers(min_value=1000000000, max_value=2000000000))
    source_image_path = draw(st.text(min_size=1, max_size=200))
    
    # Generate all required encodings
    encodings = {}
    for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
        encoded_data = draw(st.text(min_size=10, max_size=1000))
        encodings[str(strength)] = VibeEncoding(
            encoding_strength=strength,
            encoded_data=encoded_data
        )
    
    return VibeCollection(
        guid=guid,
        name=name,
        model=model,
        created_at=created_at,
        source_image_path=source_image_path,
        encodings=encodings,
        preview_images={}
    )


def create_test_image(width: int, height: int) -> bytes:
    """Create a test image with specified dimensions."""
    image = PILImage.new('RGB', (width, height), color='red')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class TestVibePreviewGeneratorProperties:
    """Property-based tests for vibe preview generation."""
    
    @given(vibe_collection_with_encodings())
    def test_preview_image_dimensions(self, collection):
        """
        **Feature: novelai-vibe-encoding, Property 4: Preview image dimensions**
        
        For any generated preview image, the dimensions should be exactly 512x768 pixels.
        
        **Validates: Requirements 2.4**
        """
        username = "testuser"
        
        # Create dependencies inside the test to avoid fixture scope issues
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = VibeStorageManager(temp_dir)
            mock_novelai_client = Mock(spec=NovelAIClient)
            preview_generator = VibePreviewGenerator(mock_novelai_client, storage_manager)
            
            # Create test image with correct dimensions
            test_image_bytes = create_test_image(
                VibePreviewGenerator.PREVIEW_WIDTH, 
                VibePreviewGenerator.PREVIEW_HEIGHT
            )
            
            # Mock the NovelAI client to return our test image
            mock_novelai_client.generate_image.return_value = test_image_bytes
            
            # Generate previews for a subset to avoid too many API calls in tests
            # Test just one combination to verify dimensions
            enc_strength = 1.0
            ref_strength = 1.0
            
            # Get collection directory
            collection_dir = storage_manager.get_collection_directory(username, collection.guid)
            os.makedirs(collection_dir, exist_ok=True)
            
            # Generate single preview
            image_path, thumb_path = preview_generator._generate_single_preview(
                collection, enc_strength, ref_strength, collection_dir
            )
            
            # Verify the generated image has correct dimensions
            assert os.path.exists(image_path)
            with PILImage.open(image_path) as img:
                assert img.width == VibePreviewGenerator.PREVIEW_WIDTH
                assert img.height == VibePreviewGenerator.PREVIEW_HEIGHT
            
            # Verify thumbnail exists and has reasonable dimensions
            assert os.path.exists(thumb_path)
            with PILImage.open(thumb_path) as thumb:
                # Thumbnail should be smaller than original
                assert thumb.width <= VibePreviewGenerator.PREVIEW_WIDTH
                assert thumb.height <= VibePreviewGenerator.PREVIEW_HEIGHT
                # But not too small
                assert thumb.width >= 100
                assert thumb.height >= 100
    
    @given(vibe_collection_with_encodings())
    def test_preview_file_completeness(self, collection):
        """
        **Feature: novelai-vibe-encoding, Property 5: Preview file completeness**
        
        For any preview image generated, both a PNG file and a JPG thumbnail should exist, 
        and the filename should contain both the encoding strength and reference strength values.
        
        **Validates: Requirements 2.5, 2.6**
        """
        username = "testuser"
        
        # Create dependencies inside the test to avoid fixture scope issues
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = VibeStorageManager(temp_dir)
            mock_novelai_client = Mock(spec=NovelAIClient)
            preview_generator = VibePreviewGenerator(mock_novelai_client, storage_manager)
            
            # Create test image
            test_image_bytes = create_test_image(512, 768)
            mock_novelai_client.generate_image.return_value = test_image_bytes
            
            # Test a few combinations to verify file completeness
            test_combinations = [(1.0, 1.0), (0.85, 0.7), (0.5, 0.35)]
            
            collection_dir = storage_manager.get_collection_directory(username, collection.guid)
            os.makedirs(collection_dir, exist_ok=True)
            
            for enc_strength, ref_strength in test_combinations:
                # Generate single preview
                image_path, thumb_path = preview_generator._generate_single_preview(
                    collection, enc_strength, ref_strength, collection_dir
                )
                
                # Verify both files exist
                assert os.path.exists(image_path), f"PNG file missing for {enc_strength}x{ref_strength}"
                assert os.path.exists(thumb_path), f"JPG thumbnail missing for {enc_strength}x{ref_strength}"
                
                # Verify filename contains strength values
                image_filename = os.path.basename(image_path)
                thumb_filename = os.path.basename(thumb_path)
                
                # Check PNG filename format
                expected_png = f"preview_enc{enc_strength}_ref{ref_strength}.png"
                assert image_filename == expected_png
                
                # Check JPG thumbnail filename format
                expected_thumb = f"preview_enc{enc_strength}_ref{ref_strength}.thumb.jpg"
                assert thumb_filename == expected_thumb
                
                # Verify file formats
                with PILImage.open(image_path) as img:
                    assert img.format == 'PNG'
                
                with PILImage.open(thumb_path) as thumb:
                    assert thumb.format == 'JPEG'


class TestVibePreviewGeneratorBasic:
    """Basic unit tests for vibe preview generation functionality."""
    
    @pytest.fixture
    def mock_novelai_client(self):
        """Create a mock NovelAI client."""
        return Mock(spec=NovelAIClient)
    
    @pytest.fixture
    def storage_manager(self):
        """Create a temporary storage manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield VibeStorageManager(temp_dir)
    
    @pytest.fixture
    def preview_generator(self, mock_novelai_client, storage_manager):
        """Create a VibePreviewGenerator with mocked dependencies."""
        return VibePreviewGenerator(mock_novelai_client, storage_manager)
    
    @pytest.fixture
    def sample_collection(self):
        """Create a sample vibe collection for testing."""
        encodings = {}
        for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
            encodings[str(strength)] = VibeEncoding(
                encoding_strength=strength,
                encoded_data=f"encoded_data_{strength}"
            )
        
        return VibeCollection(
            guid=str(uuid.uuid4()),
            name="Test Vibe",
            model="nai-diffusion-4-5-full",
            created_at=1234567890,
            source_image_path="/test/source.png",
            encodings=encodings,
            preview_images={}
        )
    
    def test_generate_previews_success(self, preview_generator, mock_novelai_client, storage_manager, sample_collection):
        """Test successful preview generation for all combinations."""
        username = "testuser"
        
        # Create test image
        test_image_bytes = create_test_image(512, 768)
        mock_novelai_client.generate_image.return_value = test_image_bytes
        
        # Mock progress callback
        progress_callback = Mock()
        
        # Generate previews
        result = preview_generator.generate_previews(username, sample_collection, progress_callback)
        
        # Verify result structure
        assert len(result) == 25  # 5 encoding × 5 reference strengths
        
        # Verify all combinations are present
        expected_combinations = [
            (enc, ref) 
            for enc in VibePreviewGenerator.ENCODING_STRENGTHS 
            for ref in VibePreviewGenerator.REFERENCE_STRENGTHS
        ]
        assert set(result.keys()) == set(expected_combinations)
        
        # Verify progress callback was called correctly
        assert progress_callback.call_count == 25
        
        # Verify NovelAI client was called for each combination
        assert mock_novelai_client.generate_image.call_count == 25
        
        # Verify collection was updated with preview paths
        assert len(sample_collection.preview_images) == 25
        
        # Verify all files exist
        for (enc_strength, ref_strength), image_path in result.items():
            assert os.path.exists(image_path)
            
            # Check corresponding thumbnail
            thumb_path = image_path.replace('.png', '.thumb.jpg')
            assert os.path.exists(thumb_path)
    
    def test_generate_previews_missing_encodings(self, preview_generator, storage_manager):
        """Test error handling when collection is missing required encodings."""
        username = "testuser"
        
        # Create a valid collection first
        complete_collection = VibeCollection(
            guid=str(uuid.uuid4()),
            name="Complete Vibe",
            model="nai-diffusion-4-5-full",
            created_at=1234567890,
            source_image_path="/test/source.png",
            encodings={
                "1.0": VibeEncoding(encoding_strength=1.0, encoded_data="data1"),
                "0.85": VibeEncoding(encoding_strength=0.85, encoded_data="data2"),
                "0.7": VibeEncoding(encoding_strength=0.7, encoded_data="data3"),
                "0.5": VibeEncoding(encoding_strength=0.5, encoded_data="data4"),
                "0.35": VibeEncoding(encoding_strength=0.35, encoded_data="data5"),
            },
            preview_images={}
        )
        
        # Manually remove some encodings to simulate missing encodings
        # This bypasses Pydantic validation since we're modifying after creation
        del complete_collection.encodings["0.7"]
        del complete_collection.encodings["0.5"]
        del complete_collection.encodings["0.35"]
        
        # Should raise ValueError for missing encodings
        with pytest.raises(ValueError, match="Collection missing required encodings"):
            preview_generator.generate_previews(username, complete_collection)
    
    def test_create_thumbnail_success(self, preview_generator):
        """Test thumbnail creation functionality."""
        # Create test image
        test_image_bytes = create_test_image(512, 768)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            thumb_path = temp_file.name
        
        try:
            # Create thumbnail
            preview_generator._create_thumbnail(test_image_bytes, thumb_path)
            
            # Verify thumbnail exists and has correct format
            assert os.path.exists(thumb_path)
            
            with PILImage.open(thumb_path) as thumb:
                assert thumb.format == 'JPEG'
                assert thumb.width <= 512
                assert thumb.height <= 768
                
        finally:
            # Clean up
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)
    
    def test_create_thumbnail_invalid_image(self, preview_generator):
        """Test thumbnail creation with invalid image data."""
        invalid_image_bytes = b"not_an_image"
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            thumb_path = temp_file.name
        
        try:
            # Should raise ValueError for invalid image
            with pytest.raises(ValueError, match="Failed to create thumbnail"):
                preview_generator._create_thumbnail(invalid_image_bytes, thumb_path)
                
        finally:
            # Clean up
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)