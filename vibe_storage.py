"""
Storage manager for NovelAI vibe collections with JSON persistence.

This module provides the VibeStorageManager class for managing vibe collection
storage, including JSON persistence and file organization.
"""

import os
import shutil
import time
import uuid
from typing import Dict, List, Optional

from file_manager_utils import UserFileManager, load_json_file_with_backup, save_json_file_atomic
from vibe_models import VibeCollection, VibeCollectionSummary


class VibeStorageManager(UserFileManager):
    """Manages vibe collection storage per user with JSON persistence."""
    
    def __init__(self, static_folder: str):
        """Initialize the vibe storage manager.
        
        Args:
            static_folder: Base static folder path
        """
        super().__init__(static_folder, "vibes")
    
    def save_collection(self, username: str, collection: VibeCollection) -> None:
        """Save vibe collection to user's vibes.json and create directory structure.
        
        Args:
            username: Username to save collection for
            collection: VibeCollection to save
            
        Raises:
            IOError: If file operations fail
            ValueError: If collection validation fails
        """
        with self._get_user_lock(username):
            # Load existing collections
            collections_data = self._load_collections_data(username)
            
            # Add new collection
            collections_data["collections"][collection.guid] = collection.model_dump()
            
            # Save updated collections
            file_path = self._get_user_file_path(username)
            save_json_file_atomic(file_path, collections_data, "vibe collections", username)
            
            # Create directory structure for this collection
            self._create_collection_directory(username, collection.guid)
    
    def load_collection(self, username: str, guid: str) -> Optional[VibeCollection]:
        """Load a specific vibe collection by GUID.
        
        Args:
            username: Username to load collection for
            guid: GUID of the collection to load
            
        Returns:
            VibeCollection if found, None otherwise
        """
        with self._get_user_lock(username):
            collections_data = self._load_collections_data(username)
            
            collection_data = collections_data["collections"].get(guid)
            if collection_data is None:
                return None
            
            return VibeCollection(**collection_data)
    
    def list_collections(self, username: str) -> List[VibeCollectionSummary]:
        """List all vibe collections for a user.
        
        Args:
            username: Username to list collections for
            
        Returns:
            List of VibeCollectionSummary objects
        """
        with self._get_user_lock(username):
            collections_data = self._load_collections_data(username)
            
            summaries = []
            for guid, collection_data in collections_data["collections"].items():
                # Get the first preview image as representative image
                preview_images = collection_data.get("preview_images", {})
                preview_image = ""
                if preview_images:
                    # Use the highest strength combination as the representative image
                    preview_image = preview_images.get("enc1.0_ref1.0", list(preview_images.values())[0])
                
                summary = VibeCollectionSummary(
                    guid=guid,
                    name=collection_data["name"],
                    model=collection_data["model"],
                    created_at=collection_data["created_at"],
                    preview_image=preview_image
                )
                summaries.append(summary)
            
            # Sort by creation date, newest first
            summaries.sort(key=lambda x: x.created_at, reverse=True)
            return summaries
    
    def delete_collection(self, username: str, guid: str) -> bool:
        """Delete a vibe collection and all associated files.
        
        Args:
            username: Username to delete collection for
            guid: GUID of the collection to delete
            
        Returns:
            True if collection was deleted, False if not found
        """
        with self._get_user_lock(username):
            collections_data = self._load_collections_data(username)
            
            # Check if collection exists
            if guid not in collections_data["collections"]:
                return False
            
            # Remove from collections data
            del collections_data["collections"][guid]
            
            # Save updated collections
            file_path = self._get_user_file_path(username)
            save_json_file_atomic(file_path, collections_data, "vibe collections", username)
            
            # Delete collection directory and all files
            collection_dir = self._get_collection_directory(username, guid)
            if os.path.exists(collection_dir):
                shutil.rmtree(collection_dir)
            
            return True
    
    def get_encoding(self, username: str, guid: str, encoding_strength: float) -> Optional[str]:
        """Get encoded vibe data for specific strength.
        
        Args:
            username: Username to get encoding for
            guid: GUID of the collection
            encoding_strength: Strength value to get encoding for
            
        Returns:
            Base64 encoded vibe data if found, None otherwise
        """
        collection = self.load_collection(username, guid)
        if collection is None:
            return None
        
        encoding_key = str(encoding_strength)
        encoding = collection.encodings.get(encoding_key)
        if encoding is None:
            return None
        
        return encoding.encoded_data
    
    def get_collection_directory(self, username: str, guid: str) -> str:
        """Get the directory path for a collection's files.
        
        Args:
            username: Username
            guid: Collection GUID
            
        Returns:
            Full path to the collection directory
        """
        return self._get_collection_directory(username, guid)
    
    def _load_collections_data(self, username: str) -> Dict:
        """Load collections data from JSON file.
        
        Args:
            username: Username to load data for
            
        Returns:
            Dictionary with collections data
        """
        file_path = self._get_user_file_path(username)
        return load_json_file_with_backup(
            file_path, 
            "vibe collections", 
            username, 
            {"collections": {}}
        )
    
    def _create_collection_directory(self, username: str, guid: str) -> None:
        """Create directory structure for a collection.
        
        Args:
            username: Username
            guid: Collection GUID
        """
        collection_dir = self._get_collection_directory(username, guid)
        os.makedirs(collection_dir, exist_ok=True)
    
    def _get_collection_directory(self, username: str, guid: str) -> str:
        """Get the directory path for a collection's files.
        
        Args:
            username: Username
            guid: Collection GUID
            
        Returns:
            Full path to the collection directory
        """
        return os.path.join(self.data_dir, username, guid)
    
    @staticmethod
    def generate_guid() -> str:
        """Generate a new GUID for a vibe collection.
        
        Returns:
            String representation of a new UUID
        """
        return str(uuid.uuid4())