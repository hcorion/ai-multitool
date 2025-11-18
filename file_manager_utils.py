"""
Utility functions for user file management with thread safety and error handling.

This module provides shared utilities for managing user-specific JSON files with:
- Thread-safe concurrent access
- Atomic file operations
- Comprehensive error handling with automatic backup on corruption
"""

import json
import logging
import os
import shutil
import threading
import time
from typing import Any


def load_json_file_with_backup(
    file_path: str, entity_type: str, username: str, default_return: Any
) -> dict[str, Any]:
    """
    Load JSON file with comprehensive error handling and automatic backup on corruption.

    Args:
        file_path: Path to the JSON file to load
        entity_type: Type of entity being loaded (e.g., "conversations", "presets") for logging
        username: Username associated with the file for logging
        default_return: Default value to return if file doesn't exist or loading fails

    Returns:
        Loaded JSON data as dictionary, or default_return on error

    Note:
        Creates a timestamped backup file if JSON is corrupted
    """
    if not os.path.exists(file_path):
        return default_return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error loading {entity_type} for {username}: {e}")
        # Try to create backup of corrupted file
        try:
            backup_file = f"{file_path}.backup.{int(time.time())}"
            shutil.copy2(file_path, backup_file)
            logging.info(f"Created backup of corrupted file: {backup_file}")
        except Exception as backup_error:
            logging.error(f"Failed to create backup: {backup_error}")
        return default_return
    except IOError as e:
        logging.error(f"IO error loading {entity_type} for {username}: {e}")
        return default_return
    except Exception as e:
        logging.error(
            f"Unexpected error loading {entity_type} for {username}: {e}",
            exc_info=True,
        )
        return default_return


def save_json_file_atomic(
    file_path: str, data: dict[str, Any], entity_type: str, username: str
) -> None:
    """
    Save JSON file atomically using temp file pattern with comprehensive error handling.

    Args:
        file_path: Path where the JSON file should be saved
        data: Dictionary data to save as JSON
        entity_type: Type of entity being saved (e.g., "conversations", "presets") for logging
        username: Username associated with the file for logging

    Raises:
        IOError: If file write operation fails
        ValueError: If JSON encoding fails
        Exception: For other unexpected errors

    Note:
        Uses atomic write pattern with temp file to prevent corruption.
        Temp file is automatically cleaned up on error.
    """
    # Create unique temp file name to avoid conflicts in concurrent operations
    temp_file = f"{file_path}.tmp.{threading.current_thread().ident}.{int(time.time() * 1000000)}"

    try:
        # Write to temporary file first
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

        # Atomic move to final location
        shutil.move(temp_file, file_path)

    except IOError as e:
        logging.error(f"IO error saving {entity_type} for {username}: {e}")
        # Clean up temp file if it exists
        _cleanup_temp_file(temp_file)
        raise IOError(f"Failed to save {entity_type} for {username}: {e}")
    except json.JSONEncodeError as e:
        logging.error(f"JSON encode error saving {entity_type} for {username}: {e}")
        _cleanup_temp_file(temp_file)
        raise ValueError(f"Failed to encode {entity_type} for {username}: {e}")
    except Exception as e:
        logging.error(
            f"Unexpected error saving {entity_type} for {username}: {e}", exc_info=True
        )
        _cleanup_temp_file(temp_file)
        raise Exception(f"Unexpected error saving {entity_type} for {username}: {e}")


def _cleanup_temp_file(temp_file: str) -> None:
    """Clean up temporary file if it exists, suppressing errors."""
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except OSError:
        pass  # Ignore cleanup errors


class UserFileManager:
    """
    Base class for managers that handle user-specific file operations with thread safety.

    Provides:
    - Thread-safe concurrent access using per-user locks
    - Standard directory structure
    - Common file path generation

    Subclasses should implement their own load/save logic using the provided utilities.
    """

    def __init__(self, static_folder: str, subdirectory: str):
        """
        Initialize the user file manager.

        Args:
            static_folder: Base static folder path
            subdirectory: Subdirectory name for this manager's data (e.g., "chats", "agents")
        """
        self.static_folder = static_folder
        self.data_dir = os.path.join(static_folder, subdirectory)
        os.makedirs(self.data_dir, exist_ok=True)

        # Thread locks for concurrent access protection
        self._user_locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

    def _get_user_lock(self, username: str) -> threading.Lock:
        """
        Get or create a thread lock for safe concurrent access to user data.

        Args:
            username: Username to get lock for

        Returns:
            Threading lock for the specified user
        """
        with self._locks_lock:
            if username not in self._user_locks:
                self._user_locks[username] = threading.Lock()
            return self._user_locks[username]

    def _get_user_file_path(self, username: str) -> str:
        """
        Get the JSON file path for storing user's data.

        Args:
            username: Username to get file path for

        Returns:
            Full path to the user's JSON file
        """
        return os.path.join(self.data_dir, f"{username}.json")



