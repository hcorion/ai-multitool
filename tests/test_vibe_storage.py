"""
Property-based tests for vibe storage infrastructure.

This module contains property-based tests to validate the correctness of
vibe storage operations and GUID generation.
"""

import os
import tempfile
import time
import uuid
from typing import Dict

import pytest
from hypothesis import given, strategies as st

from vibe_models import VibeCollection, VibeEncoding
from vibe_storage import VibeStorageManager


# Test data generators
@st.composite
def vibe_encoding_data(draw):
    """Generate valid VibeEncoding data."""
    strength = draw(st.sampled_from([1.0, 0.85, 0.7, 0.5, 0.35]))
    encoded_data = draw(st.text(min_size=1, max_size=1000))
    return VibeEncoding(encoding_strength=strength, encoded_data=encoded_data)


@st.composite
def vibe_collection_data(draw):
    """Generate valid VibeCollection data."""
    guid = str(uuid.uuid4())
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    model = draw(st.text(min_size=1, max_size=50))
    created_at = draw(st.integers(min_value=1000000000, max_value=2000000000))
    source_image_path = draw(st.text(min_size=1, max_size=200))
    
    # Generate all required encodings
    encodings = {}
    for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
        encoded_data = draw(st.text(min_size=1, max_size=1000))
        encodings[str(strength)] = VibeEncoding(
            encoding_strength=strength,
            encoded_data=encoded_data
        )
    
    # Generate preview images dict
    preview_images = {}
    for enc_strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
        for ref_strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
            key = f"enc{enc_strength}_ref{ref_strength}"
            path = draw(st.text(min_size=1, max_size=200))
            preview_images[key] = path
    
    return VibeCollection(
        guid=guid,
        name=name,
        model=model,
        created_at=created_at,
        source_image_path=source_image_path,
        encodings=encodings,
        preview_images=preview_images
    )


class TestVibeStorageProperties:
    """Property-based tests for vibe storage operations."""
    
    @given(vibe_collection_data())
    def test_stored_vibe_completeness(self, collection):
        """
        **Feature: novelai-vibe-encoding, Property 2: Stored vibe completeness**
        
        For any stored vibe collection, the data should contain: a valid GUID, 
        the model name, and for each of the 5 encoding strengths (1.0, 0.85, 0.7, 0.5, 0.35) 
        the encoded base64 data.
        
        **Validates: Requirements 1.4, 1.5, 6.1**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = VibeStorageManager(temp_dir)
            username = "testuser"
            
            # Store the collection
            storage_manager.save_collection(username, collection)
            
            # Load it back
            loaded_collection = storage_manager.load_collection(username, collection.guid)
            
            # Verify completeness
            assert loaded_collection is not None
            assert loaded_collection.guid == collection.guid
            assert loaded_collection.model == collection.model
            
            # Verify all required encoding strengths are present
            required_strengths = {1.0, 0.85, 0.7, 0.5, 0.35}
            loaded_strengths = {float(key) for key in loaded_collection.encodings.keys()}
            assert loaded_strengths == required_strengths
            
            # Verify each encoding has base64 data
            for strength_key, encoding in loaded_collection.encodings.items():
                assert encoding.encoded_data is not None
                assert len(encoding.encoded_data) > 0
                assert encoding.encoding_strength == float(strength_key)
    
    @given(st.lists(vibe_collection_data(), min_size=2, max_size=10))
    def test_guid_uniqueness(self, collections):
        """
        **Feature: novelai-vibe-encoding, Property 3: GUID uniqueness**
        
        For any two vibe collections created by the system, their GUIDs should be different.
        
        **Validates: Requirements 1.5**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = VibeStorageManager(temp_dir)
            username = "testuser"
            
            # Store all collections
            for collection in collections:
                storage_manager.save_collection(username, collection)
            
            # Load all collections and verify GUID uniqueness
            loaded_collections = storage_manager.list_collections(username)
            guids = [collection.guid for collection in loaded_collections]
            
            # All GUIDs should be unique
            assert len(guids) == len(set(guids))
            
            # Also verify that generated GUIDs are unique
            generated_guids = [VibeStorageManager.generate_guid() for _ in range(100)]
            assert len(generated_guids) == len(set(generated_guids))


class TestVibeStorageBasic:
    """Basic unit tests for vibe storage functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        """Create a temporary storage manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield VibeStorageManager(temp_dir)
    
    def test_save_and_load_collection(self, storage_manager):
        """Test basic save and load functionality."""
        username = "testuser"
        
        # Create a test collection
        collection = VibeCollection(
            guid=str(uuid.uuid4()),
            name="Test Vibe",
            model="nai-diffusion-4-5-full",
            created_at=int(time.time()),
            source_image_path="/test/path.png",
            encodings={
                "1.0": VibeEncoding(encoding_strength=1.0, encoded_data="test_data_1"),
                "0.85": VibeEncoding(encoding_strength=0.85, encoded_data="test_data_2"),
                "0.7": VibeEncoding(encoding_strength=0.7, encoded_data="test_data_3"),
                "0.5": VibeEncoding(encoding_strength=0.5, encoded_data="test_data_4"),
                "0.35": VibeEncoding(encoding_strength=0.35, encoded_data="test_data_5"),
            },
            preview_images={"enc1.0_ref1.0": "/test/preview.jpg"}
        )
        
        # Save and load
        storage_manager.save_collection(username, collection)
        loaded = storage_manager.load_collection(username, collection.guid)
        
        assert loaded is not None
        assert loaded.guid == collection.guid
        assert loaded.name == collection.name
        assert len(loaded.encodings) == 5
    
    def test_delete_collection(self, storage_manager):
        """Test collection deletion."""
        username = "testuser"
        
        # Create and save a test collection
        collection = VibeCollection(
            guid=str(uuid.uuid4()),
            name="Test Vibe",
            model="nai-diffusion-4-5-full",
            created_at=int(time.time()),
            source_image_path="/test/path.png",
            encodings={
                "1.0": VibeEncoding(encoding_strength=1.0, encoded_data="test_data"),
                "0.85": VibeEncoding(encoding_strength=0.85, encoded_data="test_data"),
                "0.7": VibeEncoding(encoding_strength=0.7, encoded_data="test_data"),
                "0.5": VibeEncoding(encoding_strength=0.5, encoded_data="test_data"),
                "0.35": VibeEncoding(encoding_strength=0.35, encoded_data="test_data"),
            },
            preview_images={}
        )
        
        storage_manager.save_collection(username, collection)
        
        # Verify it exists
        assert storage_manager.load_collection(username, collection.guid) is not None
        
        # Delete it
        result = storage_manager.delete_collection(username, collection.guid)
        assert result is True
        
        # Verify it's gone
        assert storage_manager.load_collection(username, collection.guid) is None
    
    def test_list_collections(self, storage_manager):
        """Test listing collections."""
        username = "testuser"
        
        # Create multiple collections
        collections = []
        for i in range(3):
            collection = VibeCollection(
                guid=str(uuid.uuid4()),
                name=f"Test Vibe {i}",
                model="nai-diffusion-4-5-full",
                created_at=int(time.time()) + i,
                source_image_path=f"/test/path{i}.png",
                encodings={
                    "1.0": VibeEncoding(encoding_strength=1.0, encoded_data="test_data"),
                    "0.85": VibeEncoding(encoding_strength=0.85, encoded_data="test_data"),
                    "0.7": VibeEncoding(encoding_strength=0.7, encoded_data="test_data"),
                    "0.5": VibeEncoding(encoding_strength=0.5, encoded_data="test_data"),
                    "0.35": VibeEncoding(encoding_strength=0.35, encoded_data="test_data"),
                },
                preview_images={"enc1.0_ref1.0": f"/test/preview{i}.jpg"}
            )
            collections.append(collection)
            storage_manager.save_collection(username, collection)
        
        # List collections
        summaries = storage_manager.list_collections(username)
        
        assert len(summaries) == 3
        # Should be sorted by creation date, newest first
        assert summaries[0].created_at >= summaries[1].created_at >= summaries[2].created_at