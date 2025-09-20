import base64
import io
import json
import logging
import logging.handlers
import os
import random
import re
import secrets
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from json import JSONDecodeError
from queue import Queue
from typing import Any, AnyStr, Dict, Generator, List, Mapping, NoReturn, Optional

import openai
import requests
import wand
import wand.font
from flask import (
    Flask,
    Request,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from PIL import Image as PILImage
from PIL.PngImagePlugin import PngInfo
from pydantic import BaseModel, Field, field_validator
from wand.image import Image as WandImage

import utils
from dynamic_prompts import (
    FollowUpState,
    GridDynamicPromptInfo,
    get_prompts_for_name,
    init_followup_state,
    make_character_prompts_dynamic,
    make_prompt_dynamic,
)
from image_models import (
    ImageGenerationRequest,
    ImageOperationResponse,
    Img2ImgRequest,
    InpaintingRequest,
    Operation,
    Provider,
    create_error_response,
    create_request_from_form_data,
    create_success_response,
)
from novelai_client import NovelAIAPIError, NovelAIClient, NovelAIClientError

# Configure logging to file with dated session logs
os.makedirs("logs", exist_ok=True)


# Optional: Clean up old log files (keep last 30 days)
def cleanup_old_logs(days_to_keep=30):
    """Remove log files older than specified days."""
    try:
        import glob

        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        log_files = glob.glob("logs/app_*.log")

        for log_file in log_files:
            if os.path.getmtime(log_file) < cutoff_time:
                os.remove(log_file)
                print(f"Removed old log file: {log_file}")
    except Exception as e:
        print(f"Error cleaning up old logs: {e}")


# Clean up old logs on startup
cleanup_old_logs()

# Generate dated log filename for this session
session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/app_{session_timestamp}.log"

# Create a file handler for this session
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

# Log session start
logging.info(f"=== New session started - Log file: {log_filename} ===")

app = Flask(__name__)

# Initialize the OpenAI client
client = openai.OpenAI()


stability_api_key = os.environ.get("STABILITY_API_KEY")
novelai_api_key = os.environ.get("NOVELAI_API_KEY")

secret_key_filename = "secret-key.txt"
if not os.path.isfile(secret_key_filename):
    with open(secret_key_filename, "a") as f:
        f.write(secrets.token_urlsafe(16))
with open(secret_key_filename, "r") as f:
    app.secret_key = f.read()


@app.errorhandler(404)
def resource_not_found(e: Response):
    """Handle 404 errors with JSON response."""
    return jsonify(error=str(e)), 404


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with username storage in session."""
    if request.method == "POST":
        session["username"] = request.form["username"].strip()
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/share")
def share():
    """Render the share page for viewing shared conversations."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("share.html")


@app.route("/save-mask", methods=["POST"])
def save_mask():
    """Save uploaded mask file for inpainting operations."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if "mask" not in request.files:
        return jsonify({"error": "No mask file provided"}), 400

    mask_file = request.files["mask"]
    if mask_file.filename == "":
        return jsonify({"error": "No mask file selected"}), 400

    try:
        username = session["username"]

        # Create user directory if it doesn't exist
        user_dir = os.path.join(app.static_folder, "images", username)
        os.makedirs(user_dir, exist_ok=True)

        # Generate unique filename for the mask
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mask_filename = f"mask_{timestamp}.png"
        mask_path = os.path.join(user_dir, mask_filename)

        # Save the mask file
        mask_file.save(mask_path)

        # Verify the file was saved correctly
        if not os.path.exists(mask_path):
            raise IOError(f"Mask file was not saved correctly: {mask_path}")

        # Get file size for verification
        file_size = os.path.getsize(mask_path)

        # Return the relative path for use in inpainting requests (without leading slash for Flask)
        relative_path = f"static/images/{username}/{mask_filename}"

        return jsonify(
            {
                "success": True,
                "mask_path": relative_path,
                "filename": mask_filename,
                "file_size": file_size,
            }
        )

    except Exception as e:
        logging.error(f"Error saving mask: {e}", exc_info=True)
        return jsonify({"error": f"Failed to save mask: {str(e)}"}), 500


@app.route("/logout")
def logout():
    """Clear user session and redirect to login page."""
    session.pop("username", None)
    return redirect(url_for("login"))


class ModerationException(Exception):
    """Exception raised when content fails moderation checks."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DownloadError(Exception):
    """Exception raised when image download fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConversationStorageError(Exception):
    """Exception raised when conversation storage operations fail."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class GeneratedImageData:
    """Container for generated image data and metadata."""

    local_image_path: str
    revised_prompt: str
    prompt: str
    image_name: str
    metadata: dict[str, str]

    def __init__(
        self,
        local_image_path: str,
        revised_prompt: str,
        prompt: str,
        image_name: str,
        metadata: dict[str, str] | None = None,
    ):
        self.local_image_path = local_image_path
        self.revised_prompt = revised_prompt
        self.prompt = prompt
        self.image_name = image_name
        self.metadata = metadata or {}


class SavedImageData:
    """Container for saved image file information."""

    local_image_path: str
    image_name: str

    def __init__(self, local_image_path: str, image_name: str):
        self.local_image_path = local_image_path
        self.image_name = image_name


@dataclass
class CharacterPrompt:
    """Data class for individual character prompt data."""

    positive_prompt: str
    negative_prompt: str = ""


@dataclass
class MultiCharacterPromptData:
    """Data class for multi-character prompt data including main prompts."""

    main_prompt: str
    main_negative_prompt: str = ""
    character_prompts: List[CharacterPrompt] = field(default_factory=list)


# Pydantic models for conversation data structures
class ConversationData(BaseModel):
    """Pydantic model for conversation metadata."""

    id: str
    created_at: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    object: str = "conversation"


def validate_reasoning_data(
    reasoning_data: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    """Validate reasoning data structure and ensure it contains expected fields."""
    if reasoning_data is None:
        return None

    if not isinstance(reasoning_data, dict):
        raise ValueError("Reasoning data must be a dictionary")

    # Validate required fields exist and are of correct types
    expected_fields = {
        "summary_parts": list,
        "complete_summary": str,
        "timestamp": (int, float),
        "response_id": str,
    }

    for field, expected_type in expected_fields.items():
        if field in reasoning_data:
            if not isinstance(reasoning_data[field], expected_type):
                raise ValueError(
                    f"Reasoning data field '{field}' must be of type {expected_type}"
                )

    # Ensure summary_parts contains only strings if present
    if "summary_parts" in reasoning_data:
        for part in reasoning_data["summary_parts"]:
            if not isinstance(part, str):
                raise ValueError("All items in summary_parts must be strings")

    return reasoning_data


class ChatMessage(BaseModel):
    """Pydantic model for individual chat messages."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    text: str = Field(..., description="Message content")
    timestamp: int = Field(..., description="Unix timestamp when message was created")
    response_id: str | None = Field(
        None, description="OpenAI response ID for assistant messages"
    )
    reasoning_data: Dict[str, Any] | None = Field(
        None, description="Reasoning summary data for assistant messages"
    )

    @field_validator("reasoning_data")
    @classmethod
    def validate_reasoning_data_field(
        cls, v: Dict[str, Any] | None
    ) -> Dict[str, Any] | None:
        """Validate reasoning data structure."""
        return validate_reasoning_data(v)


class Conversation(BaseModel):
    """Pydantic model for complete conversation structure."""

    data: ConversationData
    chat_name: str = Field(..., description="User-friendly name for the conversation")
    last_update: int = Field(..., description="Unix timestamp of last update")
    messages: list[ChatMessage] = Field(
        default_factory=list, description="List of messages in conversation"
    )
    last_response_id: str | None = Field(
        None, description="Last response ID for conversation continuity"
    )

    def add_message(
        self,
        role: str,
        content: str,
        response_id: str | None = None,
        reasoning_data: Dict[str, Any] | None = None,
    ) -> None:
        """Add a message to the conversation."""
        message = ChatMessage(
            role=role,
            text=content,
            timestamp=int(time.time()),
            response_id=response_id,
            reasoning_data=reasoning_data,
        )
        self.messages.append(message)
        self.last_update = int(time.time())

        # Update last_response_id if this is an assistant message with a response_id
        if role == "assistant" and response_id:
            self.last_response_id = response_id

    def get_message_list(self) -> list[dict[str, str]]:
        """Get formatted message list for frontend compatibility."""
        return [{"role": msg.role, "text": msg.text} for msg in self.messages]


class UserConversations(BaseModel):
    """Pydantic model for all conversations belonging to a user."""

    conversations: dict[str, Conversation] = Field(default_factory=dict)

    def add_conversation(
        self, conversation_id: str, conversation: Conversation
    ) -> None:
        """Add a conversation to the user's conversations."""
        self.conversations[conversation_id] = conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a specific conversation by ID."""
        return self.conversations.get(conversation_id)

    def list_conversations(self) -> dict[str, Any]:
        """List all conversations in the format expected by the frontend."""
        return {
            conv_id: {
                "data": conv.data.model_dump(),
                "chat_name": conv.chat_name,
                "last_update": conv.last_update,
            }
            for conv_id, conv in self.conversations.items()
        }


class ConversationManager:
    """Manages local conversation storage and response ID tracking for the Responses API migration."""

    def __init__(self, static_folder: str):
        self.static_folder = static_folder
        self.chats_dir = os.path.join(static_folder, "chats")
        os.makedirs(self.chats_dir, exist_ok=True)

        # Add thread locks for concurrent access protection
        self._user_locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

        # Add conversation cache for performance optimization
        self._conversation_cache: Dict[str, UserConversations] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL

    def _get_user_lock(self, username: str) -> threading.Lock:
        """Get or create a thread lock for safe concurrent access to user data."""
        with self._locks_lock:
            if username not in self._user_locks:
                self._user_locks[username] = threading.Lock()
            return self._user_locks[username]

    def _get_user_file_path(self, username: str) -> str:
        """Get the JSON file path for storing user's conversation data."""
        return os.path.join(self.chats_dir, f"{username}.json")

    def _is_cache_valid(self, username: str) -> bool:
        """Check if cached conversation data is within TTL window."""
        if username not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[username]) < self._cache_ttl

    def _update_cache(
        self, username: str, user_conversations: UserConversations
    ) -> None:
        """Update the conversation cache for a user."""
        self._conversation_cache[username] = user_conversations
        self._cache_timestamps[username] = time.time()

    def _get_from_cache(self, username: str) -> UserConversations | None:
        """Get conversations from cache if valid."""
        if self._is_cache_valid(username):
            return self._conversation_cache.get(username)
        return None

    def _load_user_conversations(self, username: str) -> UserConversations:
        """Load all conversations for a user from their JSON file using Pydantic models with comprehensive error handling and caching."""
        # Check cache first
        cached_conversations = self._get_from_cache(username)
        if cached_conversations:
            return cached_conversations

        # Use thread lock for file operations
        with self._get_user_lock(username):
            # Double-check cache after acquiring lock
            cached_conversations = self._get_from_cache(username)
            if cached_conversations:
                return cached_conversations

            user_file = self._get_user_file_path(username)
            if os.path.exists(user_file):
                try:
                    with open(user_file, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        # Use Pydantic's model_validate to create UserConversations directly
                        user_conversations = UserConversations.model_validate(
                            {"conversations": data}
                        )
                        # Update cache
                        self._update_cache(username, user_conversations)
                        return user_conversations
                except json.JSONDecodeError as e:
                    logging.error(
                        f"JSON decode error loading conversations for {username}: {e}"
                    )
                    # Try to create backup of corrupted file
                    try:
                        backup_file = f"{user_file}.backup.{int(time.time())}"
                        import shutil

                        shutil.copy2(user_file, backup_file)
                        logging.info(f"Created backup of corrupted file: {backup_file}")
                    except Exception as backup_error:
                        logging.error(f"Failed to create backup: {backup_error}")
                    return UserConversations()
                except IOError as e:
                    logging.error(f"IO error loading conversations for {username}: {e}")
                    return UserConversations()
                except ValueError as e:
                    logging.error(
                        f"Validation error loading conversations for {username}: {e}"
                    )
                    return UserConversations()
                except Exception as e:
                    logging.error(
                        f"Unexpected error loading conversations for {username}: {e}",
                        exc_info=True,
                    )
                    return UserConversations()
            return UserConversations()

    def _save_user_conversations(
        self, username: str, user_conversations: UserConversations
    ) -> None:
        """Save all conversations for a user to their JSON file using Pydantic models with comprehensive error handling and thread safety."""
        # Use thread lock for file operations
        with self._get_user_lock(username):
            user_file = self._get_user_file_path(username)
            # Use unique temp file name to avoid conflicts
            temp_file = f"{user_file}.tmp.{threading.current_thread().ident}.{int(time.time() * 1000000)}"

            try:
                # Write to temporary file first for atomic operation
                with open(temp_file, "w", encoding="utf-8") as file:
                    # Convert Pydantic models to JSON-serializable format
                    data = {}
                    for (
                        conv_id,
                        conversation,
                    ) in user_conversations.conversations.items():
                        data[conv_id] = conversation.model_dump()
                    json.dump(data, file, indent=2, ensure_ascii=False)

                # Atomic move to final location
                import shutil

                shutil.move(temp_file, user_file)

                # Update cache after successful save
                self._update_cache(username, user_conversations)

            except IOError as e:
                logging.error(f"IO error saving conversations for {username}: {e}")
                # Clean up temp file if it exists
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
                raise ConversationStorageError(
                    f"Failed to save conversations for {username}: {e}"
                )
            except JSONDecodeError as e:
                logging.error(
                    f"JSON encode error saving conversations for {username}: {e}"
                )
                # Clean up temp file if it exists
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
                raise ConversationStorageError(
                    f"Failed to encode conversations for {username}: {e}"
                )
            except Exception as e:
                logging.error(
                    f"Unexpected error saving conversations for {username}: {e}",
                    exc_info=True,
                )
                # Clean up temp file if it exists
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
                raise ConversationStorageError(
                    f"Unexpected error saving conversations for {username}: {e}"
                )

    def create_conversation(self, username: str, chat_name: str) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        current_time = int(time.time())

        user_conversations = self._load_user_conversations(username)

        # Clean chat name for storage
        clean_chat_name = re.sub(r"[^\w_. -]", "_", chat_name)

        # Create new conversation using Pydantic models
        conversation_data = ConversationData(
            id=conversation_id,
            created_at=current_time,
            metadata={},
            object="conversation",
        )

        new_conversation = Conversation(
            data=conversation_data,
            chat_name=clean_chat_name,
            last_update=current_time,
            messages=[],
            last_response_id=None,
        )

        user_conversations.add_conversation(conversation_id, new_conversation)
        self._save_user_conversations(username, user_conversations)
        return conversation_id

    def get_conversation(
        self, username: str, conversation_id: str
    ) -> Conversation | None:
        """Get a specific conversation by ID."""
        user_conversations = self._load_user_conversations(username)
        return user_conversations.get_conversation(conversation_id)

    def add_message(
        self,
        username: str,
        conversation_id: str,
        role: str,
        content: str,
        response_id: str | None = None,
        reasoning_data: Dict[str, Any] | None = None,
    ) -> None:
        """Add a message to a conversation."""
        user_conversations = self._load_user_conversations(username)

        conversation = user_conversations.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {username}"
            )

        # Use the Pydantic model's add_message method
        conversation.add_message(role, content, response_id, reasoning_data)

        self._save_user_conversations(username, user_conversations)

    def get_last_response_id(self, username: str, conversation_id: str) -> str | None:
        """Get the last response ID for conversation continuity."""
        conversation = self.get_conversation(username, conversation_id)
        if conversation:
            return conversation.last_response_id
        return None

    def update_conversation_metadata(
        self, username: str, conversation_id: str, **kwargs: Any
    ) -> None:
        """Update conversation metadata."""
        user_conversations = self._load_user_conversations(username)

        conversation = user_conversations.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {username}"
            )

        for key, value in kwargs.items():
            setattr(conversation, key, value)

        conversation.last_update = int(time.time())
        self._save_user_conversations(username, user_conversations)

    def update_conversation_title(
        self, username: str, conversation_id: str, title: str
    ) -> bool:
        """Update the title of an existing conversation."""
        try:
            user_conversations = self._load_user_conversations(username)

            conversation = user_conversations.get_conversation(conversation_id)
            if not conversation:
                logging.warning(
                    f"Conversation {conversation_id} not found for user {username}"
                )
                return False

            # Validate and sanitize the title
            if not title:
                logging.warning(
                    f"Invalid title provided for conversation {conversation_id}: {title}"
                )
                return False

            # Clean the title for storage (same logic as create_conversation)
            clean_title = re.sub(r"[^\w_. -]", "_", title.strip())
            if len(clean_title) > 30:
                clean_title = f"{clean_title[:27]}..."

            # Update the conversation title
            conversation.chat_name = clean_title
            conversation.last_update = int(time.time())

            # Save the updated conversations
            self._save_user_conversations(username, user_conversations)

            logging.info(
                f"Updated title for conversation {conversation_id} to '{clean_title}'"
            )
            return True

        except ConversationStorageError as e:
            logging.error(
                f"Storage error updating title for conversation {conversation_id}: {e}"
            )
            return False
        except Exception as e:
            logging.error(
                f"Unexpected error updating title for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return False

    def list_conversations(self, username: str) -> dict[str, Any]:
        """List all conversations for a user."""
        user_conversations = self._load_user_conversations(username)
        return user_conversations.list_conversations()

    def get_message_list(
        self, username: str, conversation_id: str
    ) -> list[dict[str, str]]:
        """Get formatted message list for frontend compatibility."""
        conversation = self.get_conversation(username, conversation_id)
        if not conversation:
            return []

        # Use the Pydantic model's get_message_list method
        return conversation.get_message_list()

    def get_message_reasoning_data(
        self, username: str, conversation_id: str, message_index: int
    ) -> Dict[str, Any] | None:
        """Get reasoning data for a specific message by index with comprehensive error handling."""
        try:
            conversation = self.get_conversation(username, conversation_id)
            if not conversation:
                logging.warning(
                    f"Conversation {conversation_id} not found for user {username} when retrieving reasoning data"
                )
                return None

            # Validate message index
            if message_index < 0 or message_index >= len(conversation.messages):
                logging.warning(
                    f"Invalid message index {message_index} for conversation {conversation_id}. "
                    f"Valid range: 0-{len(conversation.messages) - 1}"
                )
                return None

            message = conversation.messages[message_index]

            # Log message details for debugging
            logging.debug(
                f"Retrieving reasoning data for message {message_index} in conversation {conversation_id}: "
                f"role={message.role}, has_reasoning={message.reasoning_data is not None}"
            )

            # Only return reasoning data if it exists and is valid
            if message.reasoning_data:
                try:
                    # Validate the reasoning data before returning
                    validated_data = validate_reasoning_data(message.reasoning_data)
                    if validated_data:
                        summary_length = len(validated_data.get("complete_summary", ""))
                        parts_count = len(validated_data.get("summary_parts", []))
                        logging.debug(
                            f"Successfully retrieved reasoning data: {summary_length} chars, {parts_count} parts"
                        )
                    return validated_data
                except ValueError as e:
                    logging.warning(
                        f"Invalid reasoning data for message {message_index} in conversation {conversation_id}: {e}"
                    )
                    return None
            else:
                logging.debug(
                    f"No reasoning data available for message {message_index} in conversation {conversation_id}"
                )

            return None

        except Exception as e:
            logging.error(
                f"Unexpected error retrieving reasoning data for message {message_index} in conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return None

    def get_message_by_index(
        self, username: str, conversation_id: str, message_index: int
    ) -> ChatMessage | None:
        """Get a specific message by index."""
        try:
            conversation = self.get_conversation(username, conversation_id)
            if not conversation:
                return None

            # Validate message index
            if message_index < 0 or message_index >= len(conversation.messages):
                return None

            return conversation.messages[message_index]

        except Exception as e:
            logging.error(
                f"Error retrieving message {message_index} from conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return None

    def has_reasoning_data(
        self, username: str, conversation_id: str, message_index: int
    ) -> bool:
        """Check if a message has reasoning data available."""
        try:
            reasoning_data = self.get_message_reasoning_data(
                username, conversation_id, message_index
            )
            return reasoning_data is not None
        except Exception:
            return False

    def get_conversation_message_count(
        self, username: str, conversation_id: str
    ) -> int:
        """Get the total number of messages in a conversation."""
        try:
            conversation = self.get_conversation(username, conversation_id)
            if not conversation:
                return 0
            return len(conversation.messages)
        except Exception as e:
            logging.error(
                f"Error getting message count for conversation {conversation_id}: {e}"
            )
            return 0

    def get_reasoning_availability_status(
        self, username: str, conversation_id: str
    ) -> Dict[str, Any]:
        """Get reasoning availability status for a conversation to help with graceful degradation."""
        try:
            conversation = self.get_conversation(username, conversation_id)
            if not conversation:
                return {
                    "available": False,
                    "reason": "conversation_not_found",
                    "message_count": 0,
                    "reasoning_count": 0,
                }

            total_messages = len(conversation.messages)
            assistant_messages = [
                msg for msg in conversation.messages if msg.role == "assistant"
            ]
            messages_with_reasoning = [
                msg for msg in assistant_messages if msg.reasoning_data
            ]

            return {
                "available": len(messages_with_reasoning) > 0,
                "reason": "available"
                if len(messages_with_reasoning) > 0
                else "no_reasoning_data",
                "message_count": total_messages,
                "assistant_message_count": len(assistant_messages),
                "reasoning_count": len(messages_with_reasoning),
                "reasoning_percentage": (
                    len(messages_with_reasoning) / len(assistant_messages) * 100
                )
                if assistant_messages
                else 0,
            }

        except Exception as e:
            logging.error(
                f"Error getting reasoning availability status for conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return {
                "available": False,
                "reason": "error",
                "message_count": 0,
                "reasoning_count": 0,
                "error": str(e),
            }


class ResponsesAPIClient:
    """Client wrapper for OpenAI Responses API with o4-mini model."""

    def __init__(self, openai_client: openai.OpenAI):
        self.client = openai_client
        self.model = "gpt-5"

    def create_response(
        self,
        input_text: str,
        previous_response_id: str | None = None,
        stream: bool = True,
        username: str | None = None,
    ) -> Any:
        """Create a response using the Responses API with comprehensive error handling."""
        try:
            params: Dict[str, Any] = {
                "model": self.model,
                "input": input_text,
                "stream": stream,
                "store": True,  # Store responses for conversation continuity
                "tools": [{"type": "web_search_preview"}],
                "instructions": f"""You are CodeGPT, a large language model trained by OpenAI, based on the GPT-5 architecture. Knowledge cutoff: 2024-09-30. Current date: {datetime.today().strftime("%Y-%m-%d")}.
You are trained to act and respond like a professional software engineer would, with vast knowledge of every programming language and excellent reasoning skills. You write industry-standard clean, elegant, idomatic code. You output code in Markdown format like so:
```lang
code
```""",
            }

            # Add reasoning configuration with error handling
            try:
                params["reasoning"] = {"effort": "high", "summary": "detailed"}
                logging.debug("Added reasoning configuration to API request")
            except Exception as e:
                logging.warning(f"Failed to add reasoning configuration: {e}")
                # Continue without reasoning - chat should still work

            # Add previous response ID for conversation continuity
            if previous_response_id:
                params["previous_response_id"] = previous_response_id

            # Add user identifier for better caching and abuse detection
            if username:
                params["user"] = username

            return self.client.responses.create(**params)

        except openai.RateLimitError as e:
            return self._handle_rate_limit_error(e)
        except openai.APIError as e:
            return self._handle_api_error(e)
        except Exception as e:
            return self._handle_general_error(e)

    def _handle_rate_limit_error(self, error: openai.RateLimitError) -> dict[str, str]:
        """Handle rate limiting errors with detailed logging and user guidance."""
        logging.error(f"Rate limit exceeded: {error}")

        # Extract retry information if available
        retry_after = getattr(error, "retry_after", None)
        if retry_after:
            message = f"Too many requests. Please wait {retry_after} seconds before trying again."
        else:
            message = "Too many requests. Please wait a moment before trying again."

        return {
            "error": "rate_limit",
            "message": message,
            "retry_after": str(retry_after) if retry_after is not None else "",
            "user_action": "Please wait before sending another message.",
        }

    def _handle_api_error(self, error: openai.APIError) -> dict[str, str]:
        """Handle OpenAI API errors with comprehensive error mapping."""
        logging.error(f"OpenAI API error: {error}")

        # Handle specific error types with user-friendly messages
        if hasattr(error, "code"):
            if error.code == "model_not_found" or error.code == "model_unavailable":
                return {
                    "error": "model_unavailable",
                    "message": "The gpt5 model is currently unavailable. Please try again in a few minutes.",
                    "user_action": "Try again later or contact support if the issue persists.",
                }
            elif error.code == "insufficient_quota":
                return {
                    "error": "quota_exceeded",
                    "message": "API usage limit reached. Please check your OpenAI account or try again later.",
                    "user_action": "Check your OpenAI account billing or wait for quota reset.",
                }
            elif error.code == "invalid_request_error":
                return {
                    "error": "invalid_request",
                    "message": "There was an issue with your request. Please try rephrasing your message.",
                    "user_action": "Try sending a different message or refresh the page.",
                }
            elif error.code == "authentication_error":
                return {
                    "error": "authentication_error",
                    "message": "Authentication failed. Please refresh the page and try again.",
                    "user_action": "Refresh the page or contact support if the issue continues.",
                }
            elif error.code == "permission_error":
                return {
                    "error": "permission_error",
                    "message": "Access denied. You don't have permission to use this feature.",
                    "user_action": "Contact support for assistance with account permissions.",
                }

        # Handle HTTP status codes
        if hasattr(error, "status_code"):
            status_code = getattr(error, "status_code", None)
            if status_code == 503:
                return {
                    "error": "service_unavailable",
                    "message": "The AI service is temporarily unavailable. Please try again in a few minutes.",
                    "user_action": "Wait a few minutes and try again.",
                }
            elif status_code == 502 or status_code == 504:
                return {
                    "error": "gateway_error",
                    "message": "Connection to AI service failed. Please try again.",
                    "user_action": "Check your internet connection and try again.",
                }

        return {
            "error": "api_error",
            "message": "An error occurred while processing your request. Please try again.",
            "user_action": "Try again or refresh the page if the problem continues.",
        }

    def _handle_general_error(self, error: Exception) -> dict[str, str]:
        """Handle general errors with logging and user-friendly messages."""
        logging.error(f"General error in ResponsesAPIClient: {error}", exc_info=True)

        # Handle specific exception types
        if isinstance(error, ConnectionError):
            return {
                "error": "connection_error",
                "message": "Unable to connect to the AI service. Please check your internet connection.",
                "user_action": "Check your internet connection and try again.",
            }
        elif isinstance(error, TimeoutError):
            return {
                "error": "timeout_error",
                "message": "The request timed out. Please try again.",
                "user_action": "Try again with a shorter message or check your connection.",
            }
        elif isinstance(error, json.JSONDecodeError):
            return {
                "error": "parsing_error",
                "message": "Received an invalid response. Please try again.",
                "user_action": "Try again or refresh the page.",
            }

        return {
            "error": "general_error",
            "message": "An unexpected error occurred. Please try again.",
            "user_action": "Try again or refresh the page if the problem continues.",
        }

    def process_stream_with_processor(
        self, stream: Any, event_processor: "StreamEventProcessor"
    ) -> None:
        """Process streaming responses using the StreamEventProcessor."""
        try:
            event_processor.process_stream(stream)
        except Exception as e:
            event_processor.event_queue.put(
                json.dumps(
                    {"type": "error", "message": "Error processing response stream"}
                )
            )

    def process_stream_events(
        self, stream: Any
    ) -> Generator[dict[str, Any], None, None]:
        """Process streaming responses from the Responses API (legacy method)."""
        try:
            for event in stream:
                # Extract event data based on the Responses API stream format
                if hasattr(event, "type"):
                    if event.type == "response.text.created":
                        yield {"type": "text_created", "text": ""}
                    elif event.type == "response.text.delta":
                        yield {
                            "type": "text_delta",
                            "delta": getattr(event, "delta", ""),
                        }
                    elif event.type == "response.text.done":
                        yield {
                            "type": "text_done",
                            "text": getattr(event, "text", ""),
                            "response_id": getattr(event, "response_id", None),
                        }
                    elif event.type == "response.done":
                        # Final event with complete response information
                        yield {
                            "type": "response_done",
                            "response_id": getattr(event, "response_id", None),
                        }
        except Exception as e:
            yield {"type": "error", "message": "Error processing response stream"}

    def generate_conversation_title(self, user_message: str) -> str:
        """Generate a conversation title using o3-mini with minimal reasoning."""
        try:
            # Truncate very long messages to avoid excessive API costs
            truncated_message = (
                user_message[:500] if len(user_message) > 500 else user_message
            )

            # Call OpenAI API responses API with minimal reasoning for cost efficiency
            response = self.client.responses.create(
                model="gpt-5-nano",  # Use gpt-5-nano for cost efficiency
                input=f"Generate a title for this conversation:\n\nUser message: {truncated_message}",
                instructions=self._get_title_generation_instructions(),
                stream=False,
                reasoning={"effort": "low"},  # Minimal reasoning for cost efficiency
            )

            # Extract title from response
            if hasattr(response, "output_text") and response.output_text:
                return self._sanitize_title(response.output_text)
            else:
                logging.warning("Empty response from o3-mini for title generation")
                return self._generate_fallback_title()

        except openai.RateLimitError as e:
            logging.warning(f"Rate limit exceeded for title generation: {e}")
            return self._generate_fallback_title()

        except openai.APIError as e:
            logging.error(f"OpenAI API error during title generation: {e}")
            return self._generate_fallback_title()

        except Exception as e:
            logging.error(
                f"Unexpected error during title generation: {e}", exc_info=True
            )
            return self._generate_fallback_title()

    def _get_title_generation_instructions(self) -> str:
        """Get the system instructions for title generation."""
        return """You are a title generator for chat conversations. Create a concise, descriptive title (maximum 30 characters) based on the user's message.

INSTRUCTIONS:
- Extract the main topic, technology, or subject matter
- Use specific technical terms when mentioned (e.g., "Python", "React", "API")
- For coding questions, include the programming language or framework
- For general questions, focus on the core subject
- Avoid generic words like "help", "question", "how to", "assistance"
- Use title case (capitalize important words)
- Be specific and descriptive within the character limit

EXAMPLES:
- "How do I implement binary search in Python?" → "Python Binary Search"
- "What's the difference between React and Vue?" → "React vs Vue Comparison"
- "Help me debug this JavaScript error" → "JavaScript Debug Error"
- "Can you explain machine learning?" → "Machine Learning Basics"
- "I need help with CSS flexbox" → "CSS Flexbox Layout"

Generate only the title (no quotes, no extra text)."""

    def _sanitize_title(self, title: str) -> str:
        """Ensure title meets length and content requirements."""
        if not title:
            logging.error("No title to sanitize!")
            return self._generate_fallback_title()

        # Remove any quotes or extra whitespace
        title = title.strip().strip("\"'")

        # Remove any newlines or special characters that might break display
        title = re.sub(r"[\n\r\t]", " ", title)
        title = re.sub(r"\s+", " ", title)  # Collapse multiple spaces

        # Truncate to 30 characters maximum
        if len(title) > 30:
            title = title[:27] + "..."

        # If title is too short or generic, use fallback
        if len(title.strip()) < 3 or title.lower() in [
            "chat",
            "conversation",
            "help",
            "hi",
            "hello",
        ]:
            logging.error(f'Title "{title.strip()}" too generic!')
            return self._generate_fallback_title()

        return title

    def _generate_fallback_title(self) -> str:
        """Generate fallback title when AI generation fails."""
        from datetime import datetime

        date_str = datetime.now().strftime("%m/%d %H:%M")
        return f"Chat - {date_str}"


# Initialize the conversation manager
conversation_manager = ConversationManager(app.static_folder or "static")

# Initialize the Responses API client
responses_client = ResponsesAPIClient(client)


def upscale_stability_creative(
    lowres_response_bytes: io.BytesIO,
    prompt: str,
    stability_headers: Mapping[str, str | bytes | None],
) -> requests.Response:
    lowres_image = PILImage.open(lowres_response_bytes)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        lowres_image.save(tmp_file.name, "PNG")

    upscale_response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/upscale/creative",
        headers=stability_headers,
        files={"image": open(tmp_file.name, "rb")},
        data={"prompt": prompt},
    )
    if upscale_response.status_code == 200:
        generation_id = upscale_response.json().get("id")

        upscale_finished = False
        while not upscale_finished:
            upscale_response = requests.request(
                "GET",
                f"https://api.stability.ai/v2beta/stable-image/upscale/creative/result/{generation_id}",
                headers=stability_headers,
            )
            if upscale_response.status_code == 202:
                time.sleep(1)
            else:
                upscale_finished = True
        if upscale_response.status_code == 200:
            return upscale_response
        else:
            body = upscale_response.json()
            error_message = f"SAI Get Upscale Result {upscale_response.status_code}: {body['name']}: "
            for error in body["errors"]:
                error_message += f"{error}\n"
            raise Exception(error_message)
    else:
        body = upscale_response.json()
        error_message = (
            f"SAI Creative Upscale {upscale_response.status_code}: {body['name']}: "
        )
        for error in body["errors"]:
            error_message += f"{error}\n"
        raise Exception(error_message)


def generate_novelai_image(
    prompt: str,
    negative_prompt: str | None,
    username: str,
    size: tuple[int, int],
    seed: int = 0,
    upscale: bool = False,
    variety: bool = False,
    grid_dynamic_prompt: GridDynamicPromptInfo | None = None,
    character_prompts: Optional[List[Dict[str, str]]] = None,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> GeneratedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    if not novelai_api_key:
        raise ValueError("NovelAI API key not configured")

    # Use provided follow-up state or initialize new state for this generation
    if followup_state is None:
        followup_state = init_followup_state()

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, grid_dynamic_prompt, followup_state
    )

    # Process character prompts if provided
    processed_character_prompts = []
    if character_prompts:
        try:
            processed_character_prompts = make_character_prompts_dynamic(
                character_prompts,
                username,
                app.static_folder,
                seed,
                grid_dynamic_prompt,
                followup_state,  # Pass the same follow-up state used by base prompt
            )
        except (ValueError, LookupError) as e:
            raise ValueError(f"Error processing character prompts: {str(e)}")

    width = size[0]
    height = size[1]

    # Create NovelAI client
    client = NovelAIClient(novelai_api_key)

    try:
        # Generate image using the client
        image_bytes = client.generate_image(  # type: ignore
            prompt=revised_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            variety=variety,
            character_prompts=processed_character_prompts,
        )

        if upscale:
            image_bytes = client.upscale_image(image_bytes, width, height)

        file_bytes = io.BytesIO(image_bytes)

        # Build image metadata
        image_metadata: dict[str, str] = {
            "Prompt": prompt,
            "Revised Prompt": revised_prompt,
            "seed": str(seed),
        }
        if negative_prompt:
            image_metadata["Negative Prompt"] = negative_prompt

        # Add character prompt metadata (both original and processed)
        if character_prompts and processed_character_prompts:
            for i, (original_char_prompt, processed_char_prompt) in enumerate(
                zip(character_prompts, processed_character_prompts)
            ):
                char_num = i + 1
                # Only include character metadata if positive prompt exists
                if original_char_prompt.get("positive", "").strip():
                    # Save original prompt (with dynamic prompt syntax) for copying
                    image_metadata[f"Character {char_num} Prompt"] = (
                        original_char_prompt["positive"]
                    )
                    # Save processed prompt for reference
                    image_metadata[f"Character {char_num} Processed Prompt"] = (
                        processed_char_prompt["positive"]
                    )

                    # Only include negative prompts if they exist
                    if original_char_prompt.get("negative", "").strip():
                        image_metadata[f"Character {char_num} Negative"] = (
                            original_char_prompt["negative"]
                        )
                    if processed_char_prompt.get("negative", "").strip():
                        image_metadata[f"Character {char_num} Processed Negative"] = (
                            processed_char_prompt["negative"]
                        )

        saved_data = process_image_response(
            file_bytes, prompt, revised_prompt, username, image_metadata
        )
        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
            image_metadata,
        )

    except NovelAIAPIError as e:
        error_message = f"NovelAI Generate Image {e.status_code}: {e.message}"
        raise Exception(error_message)
    except NovelAIClientError as e:
        error_message = f"NovelAI Generate Image Error: {str(e)}"
        raise Exception(error_message)


def generate_novelai_inpaint_image(
    base_image: bytes,
    mask: bytes,
    prompt: str,
    negative_prompt: Optional[str],
    username: str,
    size: tuple[int, int],
    seed: int = 0,
    variety: bool = False,
    grid_dynamic_prompt: GridDynamicPromptInfo | None = None,
    character_prompts: Optional[List[Dict[str, str]]] = None,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> GeneratedImageData:
    """Generate an inpainted image using NovelAI and return processed data."""
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    if not novelai_api_key:
        raise ValueError("NovelAI API key not configured")

    # Use provided follow-up state or initialize new state for this generation
    if followup_state is None:
        followup_state = init_followup_state()

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, grid_dynamic_prompt, followup_state
    )

    # Process character prompts if provided
    processed_character_prompts = []
    if character_prompts:
        try:
            processed_character_prompts = make_character_prompts_dynamic(
                character_prompts,
                username,
                app.static_folder,
                seed,
                grid_dynamic_prompt,
                followup_state,  # Pass the same follow-up state used by base prompt
            )
        except (ValueError, LookupError) as e:
            raise ValueError(f"Error processing character prompts: {str(e)}")

    width, height = size

    # Create NovelAI client
    client = NovelAIClient(novelai_api_key)

    try:
        # Generate inpainted image using the client
        image_bytes = client.generate_inpaint_image(  # type: ignore
            base_image=base_image,
            mask=mask,
            prompt=revised_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            variety=variety,
            character_prompts=processed_character_prompts,
        )

        file_bytes = io.BytesIO(image_bytes)

        # Build image metadata
        image_metadata: Dict[str, str] = {
            "Prompt": prompt,
            "Revised Prompt": revised_prompt,
            "Operation": "inpaint",
            "Provider": "novelai",
            "seed": str(seed),
        }
        if negative_prompt:
            image_metadata["Negative Prompt"] = negative_prompt

        # Add character prompt metadata (both original and processed)
        if character_prompts and processed_character_prompts:
            for i, (original_char_prompt, processed_char_prompt) in enumerate(
                zip(character_prompts, processed_character_prompts)
            ):
                char_num = i + 1
                # Only include character metadata if positive prompt exists
                if original_char_prompt.get("positive", "").strip():
                    # Save original prompt (with dynamic prompt syntax) for copying
                    image_metadata[f"Character {char_num} Prompt"] = (
                        original_char_prompt["positive"]
                    )
                    # Save processed prompt for reference
                    image_metadata[f"Character {char_num} Processed Prompt"] = (
                        processed_char_prompt["positive"]
                    )

                    # Only include negative prompts if they exist
                    if original_char_prompt.get("negative", "").strip():
                        image_metadata[f"Character {char_num} Negative"] = (
                            original_char_prompt["negative"]
                        )
                    if processed_char_prompt.get("negative", "").strip():
                        image_metadata[f"Character {char_num} Processed Negative"] = (
                            processed_char_prompt["negative"]
                        )

        saved_data = process_image_response(
            file_bytes, prompt, revised_prompt, username, image_metadata
        )
        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
            image_metadata,
        )

    except NovelAIAPIError as e:
        error_message = f"NovelAI Inpaint Image {e.status_code}: {e.message}"
        raise Exception(error_message)
    except NovelAIClientError as e:
        error_message = f"NovelAI Inpaint Image Error: {str(e)}"
        raise Exception(error_message)


def generate_novelai_img2img_image(
    base_image: bytes,
    prompt: str,
    negative_prompt: Optional[str],
    username: str,
    size: tuple[int, int],
    seed: int = 0,
    strength: float = 0.7,
    variety: bool = False,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> GeneratedImageData:
    """Generate an img2img image using NovelAI and return processed data."""
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    if not novelai_api_key:
        raise ValueError("NovelAI API key not configured")

    # Use provided follow-up state or initialize new state for this generation
    if followup_state is None:
        followup_state = init_followup_state()

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, None, followup_state
    )

    width, height = size

    # Create NovelAI client
    client = NovelAIClient(novelai_api_key)

    try:
        # Generate img2img image using the client
        image_bytes = client.generate_img2img_image(  # type: ignore
            base_image=base_image,
            prompt=revised_prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            width=width,
            height=height,
            seed=seed,
            variety=variety,
        )

        file_bytes = io.BytesIO(image_bytes)

        # Build image metadata
        image_metadata: Dict[str, str] = {
            "Prompt": prompt,
            "Revised Prompt": revised_prompt,
            "Operation": "img2img",
            "Provider": "novelai",
            "seed": str(seed),
            "strength": str(strength),
        }
        if negative_prompt:
            image_metadata["Negative Prompt"] = negative_prompt

        saved_data = process_image_response(
            file_bytes, prompt, revised_prompt, username, image_metadata
        )
        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
            image_metadata,
        )

    except NovelAIAPIError as e:
        error_message = f"NovelAI Img2Img Image {e.status_code}: {e.message}"
        raise Exception(error_message)
    except NovelAIClientError as e:
        error_message = f"NovelAI Img2Img Image Error: {str(e)}"
        raise Exception(error_message)


def generate_stability_image(
    prompt: str,
    negative_prompt: str | None,
    username: str,
    aspect_ratio: str = "1:1",
    seed: int = 0,
    upscale: bool = False,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> GeneratedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    # Use provided follow-up state or initialize new state for this generation
    if followup_state is None:
        followup_state = init_followup_state()

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, None, followup_state
    )

    data = {  # type: ignore
        "prompt": revised_prompt,
        "output_format": "png",
        "mode": "text-to-image",
        "model": "sd3.5-large-turbo",
        "seed": seed,
        "aspect_ratio": aspect_ratio,
    }

    if negative_prompt:
        data["negative_prompt"] = negative_prompt
    if not stability_api_key:
        raise Exception(
            "Stability API key not provided to server, unable to generate image using this backend!"
        )
    stability_headers = {
        "authorization": f"Bearer {stability_api_key}",
        "accept": "image/*",
        "stability-client-id": "ai-toolkit",
        "stability-client-user-id": username,
    }
    response = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/sd3",
        headers=stability_headers,
        files={"none": ""},
        data=data,  # type: ignore
    )

    image_metadata = {"Prompt": prompt, "Revised Prompt": prompt}
    if negative_prompt:
        image_metadata["Negative Prompt"] = negative_prompt
    if "seed" in response.headers:
        image_metadata["seed"] = response.headers["seed"]
    if response.status_code == 200:
        file_bytes = io.BytesIO(response.content)
        if upscale:
            response = upscale_stability_creative(file_bytes, prompt, stability_headers)
        saved_data = process_image_response(
            file_bytes, prompt, prompt, username, image_metadata
        )
        return GeneratedImageData(
            saved_data.local_image_path,
            prompt,
            prompt,
            saved_data.image_name,
            image_metadata,
        )
    else:
        body = response.json()
        error_message = f"SAI Generate Image {response.status_code}: {body['name']}: "
        for error in body["errors"]:
            error_message += f"{error}\n"
        raise Exception(error_message)


def _process_openai_prompt(
    prompt: str,
    username: str,
    seed: int = 0,
    strict_follow_prompt: bool = False,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> tuple[str, str]:
    """
    Process and moderate a prompt for OpenAI API calls.

    Args:
        prompt: Original prompt text
        username: Username for dynamic prompt processing
        seed: Random seed for prompt processing
        strict_follow_prompt: Whether to apply strict prompt following instructions

    Returns:
        Tuple of (original_processed_prompt, final_prompt)

    Raises:
        ValueError: If Flask static folder is not defined
        ModerationException: If prompt fails OpenAI moderation
    """
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    # Use provided follow-up state or initialize new state for this generation
    if followup_state is None:
        followup_state = init_followup_state()

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, None, followup_state
    )

    before_prompt = revised_prompt

    if strict_follow_prompt:
        if len(revised_prompt) < 800:
            revised_prompt = (
                "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:\n"
                + revised_prompt
            )
        else:
            revised_prompt = (
                "My prompt has full detail so no need to add more:\n" + revised_prompt
            )

    # Run the prompt through moderation first
    moderation = client.moderations.create(input=revised_prompt)
    for result in moderation.results:
        if result.flagged:
            flagged_categories = ""
            for category, flagged in result.categories.__dict__.items():
                if flagged:
                    flagged_categories = flagged_categories + category + ", "
            if len(flagged_categories) > 0:
                flagged_categories = flagged_categories[:-2]
            raise ModerationException(message=flagged_categories)

    return before_prompt, revised_prompt


def _handle_openai_api_errors(
    e: Exception, operation: str = "Image Generation"
) -> NoReturn:
    """
    Handle OpenAI API errors with consistent error messages.

    Args:
        e: The exception that was raised
        operation: The operation being performed (for error messages)

    Raises:
        Exception: Formatted exception with appropriate error message
    """
    if isinstance(e, openai.BadRequestError):
        error = json.loads(e.response.content)
        error_message = error["error"]["message"]
        error_code = error["error"]["code"]
        if error_code == "content_policy_violation":
            error_message = f"OpenAI {operation.lower()} has generated content that doesn't pass moderation filters. You may want to adjust your prompt slightly."
        raise Exception(f"OpenAI {operation} Error {error_code}: {error_message}")
    elif isinstance(e, openai.APIError):
        raise Exception(f"OpenAI {operation} API Error: {str(e)}")
    elif "OpenAI" in str(e):
        raise e
    else:
        raise Exception(f"OpenAI {operation} Error: {str(e)}")


def generate_openai_image(
    prompt: str,
    username: str,
    size: str = "1024x1024",
    quality: str = "standard",
    strict_follow_prompt: bool = False,
    seed: int = 0,
    followup_state: Optional[dict[str, FollowUpState]] = None,
) -> GeneratedImageData:
    """
    Generate an image using OpenAI's text-to-image model.

    Args:
        prompt: Text prompt for image generation
        username: Username for file organization
        size: Image size (1024x1024, 512x512, or 256x256)
        quality: Image quality (standard or hd)
        strict_follow_prompt: Whether to apply strict prompt following
        seed: Random seed for prompt processing

    Returns:
        GeneratedImageData object with image information

    Raises:
        ValueError: If Flask static folder is not defined
        ModerationException: If prompt fails OpenAI moderation
        Exception: If OpenAI API call fails
    """
    before_prompt, revised_prompt = _process_openai_prompt(
        prompt, username, seed, strict_follow_prompt, followup_state
    )

    try:
        # Call OpenAI Image Generation API
        response = client.images.generate(
            model="gpt-image-1",
            prompt=revised_prompt,
            moderation="low",
            size=size,  # type: ignore
            quality=quality,  # type: ignore
            n=1,
        )

        if not response.data or not response.data[0].b64_json:
            raise DownloadError("Was not able to get image url")

        decoded_data = base64.b64decode(response.data[0].b64_json)

        openai_metadata = {
            "Prompt": prompt,
            "Quality": quality,
            "Revised Prompt": revised_prompt,
            "Provider": "openai",
            "Operation": "generate",
            "Size": size,
        }

        saved_data = process_image_response(
            io.BytesIO(decoded_data),
            before_prompt,
            revised_prompt,
            username,
            openai_metadata,
        )

        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
            openai_metadata,
        )

    except Exception as e:
        _handle_openai_api_errors(e, "Image Generation")


def generate_openai_inpaint_image(
    base_image_path: str,
    mask_path: str,
    prompt: str,
    username: str,
    size: str = "1024x1024",
    seed: int = 0,
) -> GeneratedImageData:
    """
    Generate an inpainted image using OpenAI's images.edit API.

    Args:
        base_image_path: Path to the base image file (PNG format)
        mask_path: Path to the mask image file (PNG format, white = inpaint, black = keep)
        prompt: Text prompt for inpainting
        username: Username for file organization
        size: Image size (1024x1024, 512x512, or 256x256)
        seed: Random seed for prompt processing

    Returns:
        GeneratedImageData object with image information

    Raises:
        ValueError: If Flask static folder is not defined
        FileNotFoundError: If base image or mask files don't exist
        ModerationException: If prompt fails OpenAI moderation
        Exception: If OpenAI API call fails
    """
    # Verify files exist
    if not os.path.exists(base_image_path):
        raise FileNotFoundError(f"Base image file not found: {base_image_path}")
    if not os.path.exists(mask_path):
        raise FileNotFoundError(f"Mask image file not found: {mask_path}")

    # Process and moderate the prompt using shared utility
    before_prompt, revised_prompt = _process_openai_prompt(prompt, username, seed)

    try:
        # Call OpenAI Images Edit API for inpainting
        with (
            open(base_image_path, "rb") as base_image_file,
            open(mask_path, "rb") as mask_file,
        ):
            response = client.images.edit(
                image=base_image_file,
                mask=mask_file,
                prompt=revised_prompt,
                size=size,  # type: ignore
                n=1,
            )

        if not response.data or not response.data[0].b64_json:
            raise Exception("OpenAI inpainting API did not return image data")

        decoded_data = base64.b64decode(response.data[0].b64_json)

        inpaint_metadata = {
            "Prompt": prompt,
            "Revised Prompt": revised_prompt,
            "Operation": "inpaint",
            "Provider": "openai",
            "Base Image": os.path.basename(base_image_path),
            "Mask Image": os.path.basename(mask_path),
            "Size": size,
        }

        saved_data = process_image_response(
            io.BytesIO(decoded_data),
            before_prompt,
            revised_prompt,
            username,
            inpaint_metadata,
        )

        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
            inpaint_metadata,
        )

    except Exception as e:
        _handle_openai_api_errors(e, "Inpainting")


def get_file_count(username: str, static_folder: str) -> int:
    image_path = os.path.join(static_folder, "images", username)

    file_count = 0
    for path in os.listdir(image_path):
        file_path = os.path.join(image_path, path)
        if (
            file_path.endswith(".png")
            and not file_path.endswith(".thumb.png")
            and os.path.isfile(file_path)
        ):
            file_count += 1
    return file_count


def process_image_response(
    image_response_bytes: io.BytesIO,
    before_prompt: str,
    after_prompt: str,
    username: str,
    metadata_to_add: dict[str, str],
) -> SavedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    image_path_relative = "static/images/" + username
    image_path = os.path.join(app.static_folder, "images", username)
    # Make sure the path directory exists first
    os.makedirs(image_path, exist_ok=True)

    cleaned_prompt = after_prompt.strip().lower()
    cleaned_prompt = (
        utils.remove_stop_words(
            cleaned_prompt.replace(".", " ")
            .replace(",", " ")
            .replace(":", " ")
            .replace("{", " ")
            .replace("}", " ")
            .replace("[", " ")
            .replace("]", " ")
            .replace("/", " ")
            .replace("\\", " ")
            .replace(">", " ")
            .replace("<", " ")
        )
        .replace("  ", " ")
        .replace(" ", "_")[:30]
    )

    file_count = get_file_count(username, app.static_folder)

    image_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.png"
    image_thumb_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.thumb.jpg"
    image_filename = os.path.join(image_path, image_name)
    image_thumb_filename = os.path.join(image_path, image_thumb_name)

    # Create an in-memory image from the downloaded content
    image = PILImage.open(image_response_bytes)

    # Create a thumbnail
    thumb_image = image.copy()
    aspect_ratio = image.height / image.width
    new_height = int(256 * aspect_ratio)
    thumb_image.thumbnail((256, new_height), PILImage.Resampling.LANCZOS)
    thumb_image = thumb_image.convert("RGB")

    # Create metadata
    metadata = PngInfo()
    for key, value in metadata_to_add.items():
        metadata.add_text(key, value)
    # Save the image with metadata directly to disk
    with open(image_filename, "wb") as f:
        image.save(f, "PNG", pnginfo=metadata, optimize=True, compression_level=9)
    with open(image_thumb_filename, "wb") as f:
        thumb_image.save(f, "JPEG", quality=75)

    local_image_path = os.path.join(image_path_relative, image_name)
    # Convert Windows backslashes to forward slashes for web URLs
    local_image_path = local_image_path.replace("\\", "/")
    return SavedImageData(local_image_path, image_name)


def generate_seed_for_provider(provider: str) -> int | None:
    if provider == "stabilityai":
        return random.getrandbits(32)
    elif provider == "novelai":
        return random.getrandbits(64)
    elif provider == "openai":
        # We just use the seed for prompt generation for OpenAI, since the API doesn't allow passing in a seed
        return random.getrandbits(32)
    return None


def _extract_character_prompts_from_form(request: Request) -> List[Dict[str, str]]:
    """
    Extract character prompt data from form submission.
    Expected form format: character_prompts[0][positive], character_prompts[0][negative], etc.
    """
    character_prompts = []

    # Parse character prompt data from form
    char_index = 0
    while True:
        positive_key = f"character_prompts[{char_index}][positive]"
        negative_key = f"character_prompts[{char_index}][negative]"

        positive_prompt = request.form.get(positive_key, "").strip()
        negative_prompt = request.form.get(negative_key, "").strip()

        # If no positive prompt found, we've reached the end
        if positive_key not in request.form:
            break

        # Only add character if it has at least a positive prompt
        if positive_prompt:
            character_prompts.append(  # type: ignore
                {"positive": positive_prompt, "negative": negative_prompt}
            )

        char_index += 1

    return character_prompts  # type: ignore


def generate_image(
    provider: str,
    prompt: str,
    size: str | None,
    request: Request,
    seed: int | None,
    grid_dynamic_prompt: GridDynamicPromptInfo | None = None,
) -> GeneratedImageData:
    if not seed or seed <= 0:
        seed = generate_seed_for_provider(provider)

    if not seed:
        raise ValueError("Unable to get 'seed' field.")

    if provider == "openai":
        quality = request.form.get("quality")
        strict_follow_prompt = request.form.get("add-follow-prompt")

        if not size:
            raise ValueError("Unable to get 'size' field.")
        if not quality:
            raise ValueError("Unable to get 'quality' field.")

        return generate_openai_image(
            prompt,
            session["username"],
            size,
            quality,
            bool(strict_follow_prompt),
            seed,
        )
    elif provider == "stabilityai":
        negative_prompt = request.form.get("negative_prompt")
        aspect_ratio = request.form.get("aspect_ratio")
        upscale_str = request.form.get("upscale", "false")
        upscale = upscale_str.lower() == "true"

        if not aspect_ratio:
            raise ValueError("Unable to get 'aspect_ratio' field.")

        return generate_stability_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            username=session["username"],
            aspect_ratio=aspect_ratio,
            seed=seed,
            upscale=upscale,
        )

    elif provider == "novelai":
        negative_prompt = request.form.get("negative_prompt")
        aspect_ratio = request.form.get("aspect_ratio")
        upscale_str = request.form.get("upscale", "false")
        upscale = upscale_str.lower() == "true"
        variety_str = request.form.get("variety", "false")
        variety = variety_str.lower() == "true"

        if not size:
            raise ValueError("Unable to get 'size' field.")

        split_size = size.split("x")

        # Extract character prompt data from form
        character_prompts = _extract_character_prompts_from_form(request)

        return generate_novelai_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            username=session["username"],
            size=(int(split_size[0]), int(split_size[1])),
            seed=seed,
            upscale=upscale,
            variety=variety,
            grid_dynamic_prompt=grid_dynamic_prompt,
            character_prompts=character_prompts,
        )

    else:
        raise ValueError(f"Unsupported provider selected: '{provider}'")


def generate_image_grid(
    form_data: str,
    provider: str,
    prompt: str | None,
    seed: int | None,
    grid_prompt_file: str,
    request: Request,
) -> GeneratedImageData:
    """Generate a grid of images using the unified image generation system."""
    if not app.static_folder:
        raise ValueError("Static folder is undefined!")

    username = session["username"]
    dynamic_prompts = get_prompts_for_name(
        username, app.static_folder, grid_prompt_file
    )

    # Remove duplicates from list
    dynamic_prompts = list(dict.fromkeys(dynamic_prompts))

    if len(dynamic_prompts) == 0:
        raise ValueError("No prompts available in file!")

    if not seed or seed <= 0:
        seed = generate_seed_for_provider(provider)
        if not seed:
            raise ValueError("Unable to generate seed for provider")

    # Generate images using the unified image generation system
    image_data_list: Dict[str, GeneratedImageData] = dict()
    generation_errors: List[str] = []

    for dynamic_prompt in dynamic_prompts:
        # Create the image request using the unified system
        try:
            image_request = create_request_from_form_data(form_data)

            # Check if this is a follow-up row identifier
            if dynamic_prompt.startswith("__FOLLOWUP_ROW_") and dynamic_prompt.endswith(
                "__"
            ):
                # Extract row index from the identifier (format: __FOLLOWUP_ROW_0:display_name__)
                identifier_content = dynamic_prompt[len("__FOLLOWUP_ROW_") : -2]
                try:
                    if ":" in identifier_content:
                        row_index_str, display_name = identifier_content.split(":", 1)
                    else:
                        row_index_str = identifier_content
                        display_name = f"Row_{identifier_content}"

                    row_index = int(row_index_str)
                    image_request.grid_dynamic_prompt = GridDynamicPromptInfo(
                        str_to_replace_with="",  # Not used for follow-up files
                        prompt_file=grid_prompt_file,
                        followup_row_index=row_index,
                    )
                except ValueError:
                    # Fallback to regular handling if parsing fails
                    image_request.grid_dynamic_prompt = GridDynamicPromptInfo(
                        str_to_replace_with=dynamic_prompt, prompt_file=grid_prompt_file
                    )
            else:
                # Regular prompt file handling
                image_request.grid_dynamic_prompt = GridDynamicPromptInfo(
                    str_to_replace_with=dynamic_prompt, prompt_file=grid_prompt_file
                )
            # Override seed with the locked grid seed
            image_request.seed = seed
            # Generate the image using the unified handler
            if image_request.operation == Operation.INPAINT:
                response = _handle_inpainting_request(image_request)
            else:
                response = _handle_generation_request(image_request)

            if response.success:
                # Convert the response to GeneratedImageData format
                # Use display name for follow-up rows, otherwise use the original prompt
                result_key = dynamic_prompt
                if dynamic_prompt.startswith(
                    "__FOLLOWUP_ROW_"
                ) and dynamic_prompt.endswith("__"):
                    identifier_content = dynamic_prompt[len("__FOLLOWUP_ROW_") : -2]
                    if ":" in identifier_content:
                        _, display_name = identifier_content.split(":", 1)
                        result_key = display_name

                image_data_list[result_key] = GeneratedImageData(
                    local_image_path=response.image_path,
                    revised_prompt=response.revised_prompt or image_request.prompt,
                    prompt=image_request.prompt,
                    image_name=response.image_name,
                    metadata=response.metadata,
                )
                logging.info(
                    f"Grid generation: Image generated for prompt '{dynamic_prompt}'"
                )
            else:
                # Use display name for error messages too
                display_prompt = dynamic_prompt
                if dynamic_prompt.startswith(
                    "__FOLLOWUP_ROW_"
                ) and dynamic_prompt.endswith("__"):
                    identifier_content = dynamic_prompt[len("__FOLLOWUP_ROW_") : -2]
                    if ":" in identifier_content:
                        _, display_name = identifier_content.split(":", 1)
                        display_prompt = display_name

                error_msg = f"Prompt '{display_prompt}': {response.error_message or 'Unknown error'}"
                if response.error_type:
                    error_msg += f" ({response.error_type})"
                generation_errors.append(error_msg)
                logging.warning(
                    f"Grid generation: Failed to generate image - {error_msg}"
                )
                continue

        except Exception as e:
            # Use display name for error messages too
            display_prompt = dynamic_prompt
            if dynamic_prompt.startswith("__FOLLOWUP_ROW_") and dynamic_prompt.endswith(
                "__"
            ):
                identifier_content = dynamic_prompt[len("__FOLLOWUP_ROW_") : -2]
                if ":" in identifier_content:
                    _, display_name = identifier_content.split(":", 1)
                    display_prompt = display_name

            error_msg = f"Prompt '{display_prompt}': {str(e)}"
            generation_errors.append(error_msg)
            logging.error(
                f"Grid generation: Exception during image generation - {error_msg}"
            )
            continue

        # Don't hammer the API servers
        time.sleep(random.randrange(2, 8))

    if not image_data_list:
        if generation_errors:
            error_summary = (
                f"No images were successfully generated from {len(dynamic_prompts)} prompts. Errors encountered:\n"
                + "\n".join(f"- {error}" for error in generation_errors)
            )

            # Add helpful context based on common error patterns
            error_text = " ".join(generation_errors).lower()
            if "rate limit" in error_text or "quota" in error_text:
                error_summary += "\n\nTip: This appears to be a rate limiting issue. Try again in a few minutes or check your API quota."
            elif "api key" in error_text or "authentication" in error_text:
                error_summary += "\n\nTip: This appears to be an authentication issue. Check that your API keys are properly configured."
            elif "invalid" in error_text and "prompt" in error_text:
                error_summary += "\n\nTip: Some prompts may contain invalid content. Check your prompt file for problematic text."
            elif "timeout" in error_text or "connection" in error_text:
                error_summary += "\n\nTip: This appears to be a network connectivity issue. Check your internet connection and try again."
        else:
            error_summary = f"No images were successfully generated from {len(dynamic_prompts)} prompts. No specific errors recorded. This may indicate a configuration issue."
        raise ValueError(error_summary)

    # Create the grid image using ImageMagick
    file_count = get_file_count(username, app.static_folder)
    image_name = f"{str(file_count).zfill(10)}-grid_{grid_prompt_file}.png"
    image_thumb_name = f"{str(file_count).zfill(10)}-grid_{grid_prompt_file}.thumb.jpg"
    image_path = os.path.join(app.static_folder, "images", username)
    image_filename = os.path.join(image_path, image_name)
    image_thumb_filename = os.path.join(image_path, image_thumb_name)
    image_thumb_filename_apng = image_thumb_filename.replace(
        ".thumb.jpg", ".thumb.apng"
    )

    # Create the montage using ImageMagick
    with WandImage() as img:  # type: ignore
        for dynamic_prompt, image_data in image_data_list.items():
            # Extract the actual file path from the web path
            actual_image_path = image_data.local_image_path
            if actual_image_path.startswith("static/"):
                actual_image_path = os.path.join(
                    app.static_folder, actual_image_path[7:]
                )

            with WandImage() as wand_image:  # type: ignore
                wand_image.options["label"] = dynamic_prompt  # type: ignore
                wand_image.read(filename=actual_image_path)  # type: ignore
                img.image_add(wand_image)  # type: ignore

        # Create the montage with labels
        try:
            style = wand.font.Font("Roboto-Light.ttf", 65, "black")
        except:
            # Fallback if font is not available
            style = None

        img.montage(mode="concatenate", font=style)  # type: ignore
        img.save(filename=image_filename)  # type: ignore

    # Copy metadata from the first image
    first_image_data = list(image_data_list.values())[0]
    first_image_path = first_image_data.local_image_path
    if first_image_path.startswith("static/"):
        first_image_path = os.path.join(app.static_folder, first_image_path[7:])

    try:
        image_to_copy = PILImage.open(first_image_path)
        png_info = PngInfo()
        for key, value in image_to_copy.info.items():
            if isinstance(key, str):
                png_info.add_text(key, value)

        # Add grid-specific metadata
        png_info.add_text("Grid Prompt File", grid_prompt_file)
        png_info.add_text("Grid Prompts", ", ".join(dynamic_prompts))

        target_image = PILImage.open(image_filename)
        target_image.save(image_filename, pnginfo=png_info)
    except Exception as e:
        print(f"Warning: Could not copy metadata to grid image: {e}")

    # Create animated thumbnail
    try:
        with WandImage() as animated_img:  # type: ignore
            for dynamic_prompt, image_data in image_data_list.items():
                # Get the thumbnail path
                thumb_path = image_data.local_image_path.replace(".png", ".thumb.jpg")
                if thumb_path.startswith("static/"):
                    thumb_path = os.path.join(app.static_folder, thumb_path[7:])

                if os.path.exists(thumb_path):
                    with WandImage(filename=thumb_path) as frame_image:  # type: ignore
                        frame_image.delay = 100  # type: ignore
                        animated_img.sequence.append(frame_image)  # type: ignore

            if len(animated_img.sequence) > 0:
                animated_img.coalesce()  # type: ignore
                animated_img.optimize_layers()  # type: ignore
                animated_img.format = "apng"
                animated_img.save(filename=image_thumb_filename_apng)  # type: ignore

                # Rename to .thumb.jpg
                os.rename(image_thumb_filename_apng, image_thumb_filename)
    except Exception as e:
        print(f"Warning: Could not create animated thumbnail: {e}")
        # Create a static thumbnail from the grid image
        try:
            with WandImage(filename=image_filename) as thumb_img:  # type: ignore
                thumb_img.resize(300, 300)  # type: ignore
                thumb_img.save(filename=image_thumb_filename)  # type: ignore
        except Exception as e2:
            print(f"Warning: Could not create static thumbnail: {e2}")

    # Convert to web-relative path
    local_image_path = f"static/images/{username}/{image_name}"

    return GeneratedImageData(
        local_image_path=local_image_path,
        revised_prompt=f"Grid generated from {grid_prompt_file}: {', '.join(dynamic_prompts)}",
        prompt=prompt,
        image_name=image_name,
        metadata={
            "Grid Prompt File": grid_prompt_file,
            "Grid Prompts": ", ".join(dynamic_prompts),
            "Grid Image Count": str(len(image_data_list)),
        },
    )


@app.route("/", methods=["GET"])
def index():
    """Render main application interface with user authentication check."""
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


images_per_page = 6 * 3  # (6 wide * 3 tall)


#################################
########    CHAT API    #########
#################################


@app.route("/get-all-conversations")
def get_all_conversations() -> str:
    if "username" not in session:
        abort(404, description="Username not in session")

    username = session["username"]

    # Use ConversationManager to get all conversations
    conversations = conversation_manager.list_conversations(username)
    return json.dumps(conversations)


@app.route("/update-conversation-title", methods=["POST"])
def update_conversation_title():
    """Update conversation title and return updated conversation list."""
    if "username" not in session:
        return jsonify({"error": "Username not in session"}), 401

    username = session["username"]

    if not request.json:
        return jsonify({"error": "Invalid request format"}), 400

    conversation_id = request.json.get("conversation_id")
    new_title = request.json.get("title")

    if not conversation_id or not new_title:
        return jsonify({"error": "Missing conversation_id or title"}), 400

    try:
        # Update the conversation title
        success = conversation_manager.update_conversation_title(
            username, conversation_id, new_title
        )

        if success:
            # Return updated conversation list
            conversations = conversation_manager.list_conversations(username)
            return jsonify(
                {
                    "success": True,
                    "message": "Title updated successfully",
                    "conversations": conversations,
                }
            )
        else:
            return jsonify(
                {"success": False, "error": "Failed to update conversation title"}
            ), 400

    except Exception as e:
        logging.error(f"Error updating conversation title: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# Old get_message_list function removed - now using ConversationManager.get_message_list()


@app.route("/image", methods=["POST"])
def handle_image_request():
    """Unified endpoint for all image operations (generate, inpaint, img2img)."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        # Check if this is a grid generation request
        form_data = request.form.to_dict()
        if form_data.get("advanced-generate-grid") == "on" and form_data.get(
            "grid-prompt-file"
        ):
            # Handle grid generation using the legacy function but with unified backend
            grid_prompt_file = form_data.get("grid-prompt-file")
            provider = form_data.get("provider", "openai")
            prompt = form_data.get("prompt", "")
            seed = (
                int(form_data.get("seed", 0))
                if form_data.get("seed", "0").isdigit()
                else None
            )

            try:
                grid_result = generate_image_grid(
                    form_data=form_data,
                    provider=provider,
                    prompt=prompt,
                    seed=seed,
                    grid_prompt_file=grid_prompt_file,
                    request=request,
                )

                return jsonify(
                    {
                        "success": True,
                        "image_path": grid_result.local_image_path,
                        "image_name": grid_result.image_name,
                        "revised_prompt": grid_result.revised_prompt,
                        "provider": provider,
                        "operation": "grid_generate",
                        "timestamp": int(time.time()),
                        "metadata": grid_result.metadata,
                    }
                )

            except Exception as e:
                return jsonify(
                    {
                        "success": False,
                        "error_message": f"Grid generation failed: {str(e)}",
                        "error_type": "grid_generation_error",
                        "provider": provider,
                        "operation": "grid_generate",
                        "timestamp": int(time.time()),
                    }
                ), 400

        # Create request object from form data for regular operations
        image_request = create_request_from_form_data(form_data)

        # Route to appropriate handler based on operation
        if image_request.operation == Operation.GENERATE:
            response = _handle_generation_request(image_request)  # type: ignore
        elif image_request.operation == Operation.INPAINT:
            if not isinstance(image_request, InpaintingRequest):
                raise ValueError("Invalid request type for inpainting operation")
            response = _handle_inpainting_request(image_request)
        elif image_request.operation == Operation.IMG2IMG:
            if not isinstance(image_request, Img2ImgRequest):
                raise ValueError("Invalid request type for img2img operation")
            response = _handle_img2img_request(image_request)
        else:
            return jsonify(
                {"error": f"Unsupported operation: {image_request.operation}"}
            ), 400

        # Return JSON response
        if response.success:
            return jsonify(
                {
                    "success": True,
                    "image_path": response.image_path,
                    "image_name": response.image_name,
                    "revised_prompt": response.revised_prompt,
                    "provider": response.provider,
                    "operation": response.operation,
                    "timestamp": response.timestamp,
                    "metadata": response.metadata,
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error_message": response.error_message,
                    "error_type": response.error_type,
                    "provider": response.provider,
                    "operation": response.operation,
                    "timestamp": response.timestamp,
                }
            ), 400

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error in image request: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


def _handle_generation_request(
    image_request: ImageGenerationRequest,
) -> ImageOperationResponse:
    """Handle image generation requests."""
    try:
        # Use seed from request, or generate one if not provided (0 means random)
        seed = image_request.seed
        if not seed or seed <= 0:
            seed = generate_seed_for_provider(image_request.provider.value)
            if not seed:
                raise ValueError("Unable to generate seed for provider")

        # Initialize follow-up state for this generation
        followup_state = init_followup_state()

        # Route directly to the appropriate generation function based on provider
        if image_request.provider == Provider.OPENAI:
            generated_data = generate_openai_image(
                prompt=image_request.prompt,
                username=session["username"],
                size=f"{image_request.width}x{image_request.height}",
                quality=image_request.quality.value,
                strict_follow_prompt=False,  # Default to False for new endpoint
                seed=seed,
                followup_state=followup_state,
            )
        elif image_request.provider == Provider.STABILITY:
            generated_data = generate_stability_image(
                prompt=image_request.prompt,
                negative_prompt=image_request.negative_prompt,
                username=session["username"],
                aspect_ratio=_get_aspect_ratio_from_dimensions(
                    image_request.width, image_request.height
                ),
                seed=seed,
                upscale=False,  # Default to False for new endpoint
                followup_state=followup_state,
            )
        elif image_request.provider == Provider.NOVELAI:
            # Convert character prompts to the format expected by generate_novelai_image
            character_prompts = None
            if image_request.character_prompts:
                character_prompts = image_request.character_prompts

            generated_data = generate_novelai_image(
                prompt=image_request.prompt,
                negative_prompt=image_request.negative_prompt,
                username=session["username"],
                size=(image_request.width, image_request.height),
                seed=seed,
                upscale=False,  # Default to False for new endpoint
                variety=image_request.variety,
                grid_dynamic_prompt=image_request.grid_dynamic_prompt,
                character_prompts=character_prompts,
                followup_state=followup_state,
            )
        else:
            raise ValueError(f"Unsupported provider: {image_request.provider.value}")

        return create_success_response(
            image_path=generated_data.local_image_path,
            image_name=generated_data.image_name,
            provider=image_request.provider,
            operation=image_request.operation,
            revised_prompt=generated_data.revised_prompt,
            metadata=generated_data.metadata,
        )

    except Exception as e:
        return create_error_response(
            error=e, provider=image_request.provider, operation=image_request.operation
        )


def _handle_inpainting_request(
    image_request: InpaintingRequest,
) -> ImageOperationResponse:
    """Handle inpainting requests."""
    try:
        # Validate inpainting request parameters
        if not image_request.base_image_path:
            raise ValueError("Base image path is required for inpainting")

        if not image_request.mask_path:
            raise ValueError("Mask path is required for inpainting")

        if not image_request.prompt:
            raise ValueError("Prompt is required for inpainting")

        # Check if files exist and are readable
        if not os.path.exists(image_request.base_image_path):
            raise FileNotFoundError(
                f"Base image file not found: {image_request.base_image_path}"
            )

        if not os.path.exists(image_request.mask_path):
            raise FileNotFoundError(f"Mask file not found: {image_request.mask_path}")

        # Use seed from request, or generate one if not provided (0 means random)
        seed = image_request.seed

        # Initialize follow-up state for this generation
        followup_state = init_followup_state()
        if not seed or seed <= 0:
            seed = generate_seed_for_provider(image_request.provider.value)
            if not seed:
                raise ValueError("Unable to generate seed for provider")

        # Route to appropriate provider inpainting function
        if image_request.provider == Provider.OPENAI:
            # Use OpenAI inpainting
            generated_data = generate_openai_inpaint_image(
                base_image_path=image_request.base_image_path,
                mask_path=image_request.mask_path,
                prompt=image_request.prompt,
                username=session["username"],
                seed=seed,
            )
        elif image_request.provider == Provider.NOVELAI:
            # Use NovelAI inpainting
            try:
                # Read and encode images
                with open(image_request.base_image_path, "rb") as f:
                    base_image_data = f.read()
                with open(image_request.mask_path, "rb") as f:
                    mask_data = f.read()
            except IOError as e:
                raise IOError(f"Failed to read image files: {str(e)}")

            generated_data = generate_novelai_inpaint_image(
                base_image=base_image_data,
                mask=mask_data,
                prompt=image_request.prompt,
                negative_prompt=image_request.negative_prompt,
                username=session["username"],
                size=(image_request.width, image_request.height),
                seed=seed,
                variety=image_request.variety,
                character_prompts=image_request.character_prompts,
                grid_dynamic_prompt=image_request.grid_dynamic_prompt,
                followup_state=followup_state,
            )
        else:
            raise ValueError(
                f"Provider {image_request.provider.value} does not support inpainting"
            )

        revised_prompt = getattr(generated_data, "revised_prompt", None)
        # Ensure revised_prompt is a string or None, not a Mock object
        if hasattr(revised_prompt, "_mock_name"):
            revised_prompt = None

        return create_success_response(
            image_path=generated_data.local_image_path,
            image_name=generated_data.image_name,
            provider=image_request.provider,
            operation=image_request.operation,
            revised_prompt=revised_prompt,
        )

    except (ValueError, FileNotFoundError, IOError) as e:
        # These are user-facing errors that should be shown to the user
        return create_error_response(
            error=e,
            provider=image_request.provider,
            operation=image_request.operation,
            error_message=str(e),
        )
    except Exception as e:
        # Log unexpected errors for debugging
        logging.error(f"Unexpected error in inpainting request: {e}", exc_info=True)

        return create_error_response(
            error=e,
            provider=image_request.provider,
            operation=image_request.operation,
            error_message=f"Inpainting failed: {str(e)}",
        )


def _handle_img2img_request(image_request: Img2ImgRequest) -> ImageOperationResponse:
    """Handle img2img requests."""
    try:
        # Only NovelAI supports img2img currently
        if image_request.provider != Provider.NOVELAI:
            raise ValueError(
                f"Provider {image_request.provider.value} does not support img2img"
            )

        # Read and encode base image
        with open(image_request.base_image_path, "rb") as f:
            base_image_data = f.read()

        # Use seed from request, or generate one if not provided (0 means random)
        seed = image_request.seed
        if not seed or seed <= 0:
            seed = generate_seed_for_provider(image_request.provider.value)
            if not seed:
                raise ValueError("Unable to generate seed for provider")

        # Initialize follow-up state for this generation
        followup_state = init_followup_state()

        generated_data = generate_novelai_img2img_image(
            base_image=base_image_data,
            prompt=image_request.prompt,
            negative_prompt=image_request.negative_prompt,
            strength=image_request.strength,
            username=session["username"],
            size=(image_request.width, image_request.height),
            seed=seed,
            variety=image_request.variety,
            followup_state=followup_state,
        )

        revised_prompt = getattr(generated_data, "revised_prompt", None)
        # Ensure revised_prompt is a string or None, not a Mock object
        if hasattr(revised_prompt, "_mock_name"):
            revised_prompt = None

        return create_success_response(
            image_path=generated_data.local_image_path,
            image_name=generated_data.image_name,
            provider=image_request.provider,
            operation=image_request.operation,
            revised_prompt=revised_prompt,
        )

    except Exception as e:
        return create_error_response(
            error=e, provider=image_request.provider, operation=image_request.operation
        )


def _get_aspect_ratio_from_dimensions(width: int, height: int) -> str:
    """Convert width/height to aspect ratio string."""
    if width == height:
        return "1:1"
    elif width > height:
        if width / height == 16 / 9:
            return "16:9"
        elif width / height == 4 / 3:
            return "4:3"
        else:
            return "16:9"  # Default for landscape
    else:
        if height / width == 16 / 9:
            return "9:16"
        elif height / width == 4 / 3:
            return "3:4"
        else:
            return "9:16"  # Default for portrait


eos_str = "␆␄"


@app.route("/chat", methods=["GET", "POST"])  # type: ignore
def converse():
    """Handle chat conversations with streaming responses and conversation management."""
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    # Get conversation_id from request (replaces thread_id)
    conversation_id = (
        request.json.get("thread_id")  # Keep thread_id for frontend compatibility
        if request.method == "POST" and request.json
        else request.args.get("thread_id")
    )

    if request.method == "GET":
        if not conversation_id:
            raise ValueError("conversation_id was empty")

        # Use ConversationManager to get message list
        message_list = conversation_manager.get_message_list(username, conversation_id)
        return json.dumps({"threadId": conversation_id, "messages": message_list})

    elif request.method == "POST":
        if not request.json:
            raise ValueError("Expected valid request json in POST Request")

        user_input = request.json.get("user_input")
        if not user_input:
            return {"error": "No input provided"}, 400

        # Handle existing conversation or create new one
        if conversation_id:
            # Check if conversation exists
            conversation = conversation_manager.get_conversation(
                username, conversation_id
            )
            if not conversation:
                return {"error": "Conversation not found"}, 404

        else:
            # Create new conversation with temporary title
            chat_name = request.json.get("chat_name", "New Chat")
            conversation_id = conversation_manager.create_conversation(
                username, chat_name
            )

            # Generate title asynchronously for new conversations
            def generate_title_async():
                """Generate and update conversation title asynchronously."""
                try:
                    # Generate title using the user's first message
                    generated_title = responses_client.generate_conversation_title(
                        user_input
                    )

                    # Update the conversation with the generated title
                    success = conversation_manager.update_conversation_title(
                        username, conversation_id, generated_title
                    )

                    if success:
                        logging.info(
                            f"Successfully generated title '{generated_title}' for conversation {conversation_id}"
                        )
                    else:
                        logging.warning(
                            f"Failed to update title for conversation {conversation_id}"
                        )

                except Exception as e:
                    logging.error(
                        f"Error generating title for conversation {conversation_id}: {e}",
                        exc_info=True,
                    )

            generate_title_async()

        # Add user message to conversation
        conversation_manager.add_message(username, conversation_id, "user", user_input)

        # Get previous response ID for conversation continuity
        previous_response_id = conversation_manager.get_last_response_id(
            username, conversation_id
        )

        # Get current message list for frontend
        message_list = conversation_manager.get_message_list(username, conversation_id)

        def start_responses_stream_thread(
            event_queue: Queue[str],
            user_input: str,
            previous_response_id: str | None,
            username: str,
            conversation_id: str,
        ):
            """Start streaming thread using Responses API with comprehensive error handling."""
            event_processor = StreamEventProcessor(event_queue)

            try:
                # Create response using Responses API
                stream = responses_client.create_response(
                    input_text=user_input,
                    previous_response_id=previous_response_id,
                    stream=True,
                    username=username,
                )

                # Check if we got an error response
                if isinstance(stream, dict) and "error" in stream:
                    error_data = {
                        "type": "error",
                        "message": stream.get("message", "An error occurred"),
                        "error_code": stream.get("error", "unknown_error"),
                        "user_action": stream.get("user_action", "Please try again."),
                    }
                    event_queue.put(json.dumps(error_data))
                    return

                # Process the stream
                event_processor.process_stream(stream)

                # Get the response ID, final text, and reasoning data for storage
                response_id = event_processor.get_response_id()
                final_text = event_processor.accumulated_text

                # Get reasoning data with graceful degradation
                reasoning_data = None
                try:
                    reasoning_data = event_processor.get_reasoning_data()
                    if reasoning_data:
                        logging.debug(
                            f"Successfully retrieved reasoning data for response {response_id}"
                        )
                    else:
                        logging.debug(
                            f"No reasoning data available for response {response_id}"
                        )
                except Exception as e:
                    logging.warning(
                        f"Failed to retrieve reasoning data for response {response_id}: {e}"
                    )
                    # Continue without reasoning data - chat functionality should not be affected

                if final_text and response_id:
                    try:
                        # Store assistant response in conversation with reasoning data (if available)
                        conversation_manager.add_message(
                            username,
                            conversation_id,
                            "assistant",
                            final_text,
                            response_id,
                            reasoning_data,
                        )

                        # Log reasoning data status for debugging
                        if reasoning_data:
                            logging.info(
                                f"Saved assistant response with reasoning data for conversation {conversation_id}"
                            )
                        else:
                            logging.info(
                                f"Saved assistant response without reasoning data for conversation {conversation_id}"
                            )

                    except ConversationStorageError as e:
                        logging.error(f"Failed to save assistant response: {e}")
                        event_queue.put(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Response received but failed to save. Your conversation may be incomplete.",
                                    "error_code": "storage_error",
                                    "user_action": "Try refreshing the page or contact support if the issue persists.",
                                }
                            )
                        )
                    except Exception as e:
                        logging.error(
                            f"Unexpected error saving assistant response: {e}",
                            exc_info=True,
                        )
                        event_queue.put(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Failed to save the response. Please try again.",
                                    "error_code": "save_error",
                                    "user_action": "Try sending your message again.",
                                }
                            )
                        )
                elif not final_text:
                    logging.warning(
                        f"Empty response received for conversation {conversation_id}"
                    )
                    event_queue.put(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Received an empty response. Please try again.",
                                "error_code": "empty_response",
                                "user_action": "Try rephrasing your message or try again.",
                            }
                        )
                    )

            except ConnectionError as e:
                logging.error(f"Connection error in stream thread: {e}")
                event_queue.put(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "Connection lost while processing your request. Please check your internet connection.",
                            "error_code": "connection_error",
                            "user_action": "Check your internet connection and try again.",
                        }
                    )
                )
            except TimeoutError as e:
                logging.error(f"Timeout error in stream thread: {e}")
                event_queue.put(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "Request timed out. Please try again.",
                            "error_code": "timeout_error",
                            "user_action": "Try again or check your connection.",
                        }
                    )
                )
            except Exception as e:
                logging.error(
                    f"Unexpected error in responses stream thread: {e}", exc_info=True
                )
                event_queue.put(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "An unexpected error occurred while processing your request.",
                            "error_code": "stream_thread_error",
                            "user_action": "Try again or refresh the page if the problem continues.",
                        }
                    )
                )

        def stream_events(
            conversation_id: str,
            user_input: str,
            previous_response_id: str | None,
            message_list: list[dict[str, str]],
        ) -> Generator[Any | AnyStr]:
            """Stream events to frontend using new Responses API."""
            # Send initial message list
            yield f"{json.dumps(json.dumps({'type': 'message_list', 'threadId': conversation_id, 'messages': message_list}))}{eos_str}"

            event_queue: Queue[Any] = Queue()

            # Start the Responses API stream in a separate thread
            threading.Thread(
                target=start_responses_stream_thread,
                args=(
                    event_queue,
                    user_input,
                    previous_response_id,
                    username,
                    conversation_id,
                ),
            ).start()

            # Yield from queue as events come
            while True:
                event = event_queue.get()  # This will block until an item is available
                yield event + eos_str

        return Response(
            stream_with_context(
                stream_events(
                    conversation_id, user_input, previous_response_id, message_list
                )
            ),  # type: ignore
            mimetype="text/plain",
        )


@app.route("/chat/reasoning/<conversation_id>/<int:message_index>", methods=["GET"])
def get_message_reasoning(conversation_id: str, message_index: int):
    """API endpoint to retrieve reasoning data for a specific message."""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    username = session["username"]

    try:
        # Validate conversation ownership by attempting to retrieve it
        conversation = conversation_manager.get_conversation(username, conversation_id)
        if not conversation:
            return jsonify(
                {
                    "error": "Conversation not found",
                    "message": "The requested conversation does not exist or you don't have access to it.",
                }
            ), 404

        # Validate message index
        message_count = conversation_manager.get_conversation_message_count(
            username, conversation_id
        )
        if message_index < 0 or message_index >= message_count:
            return jsonify(
                {
                    "error": "Invalid message index",
                    "message": f"Message index {message_index} is out of range. Valid range: 0-{message_count - 1}.",
                }
            ), 400

        # Get the message to verify it exists and is an assistant message
        message = conversation_manager.get_message_by_index(
            username, conversation_id, message_index
        )
        if not message:
            return jsonify(
                {
                    "error": "Message not found",
                    "message": "The requested message could not be retrieved.",
                }
            ), 404

        # Only assistant messages can have reasoning data
        if message.role != "assistant":
            return jsonify(
                {
                    "error": "No reasoning available",
                    "message": "Reasoning data is only available for assistant messages.",
                }
            ), 400

        # Retrieve reasoning data
        reasoning_data = conversation_manager.get_message_reasoning_data(
            username, conversation_id, message_index
        )

        if reasoning_data is None:
            return jsonify(
                {
                    "error": "No reasoning data",
                    "message": "No reasoning data is available for this message.",
                }
            ), 404

        # Return structured reasoning data
        return jsonify(
            {
                "success": True,
                "conversation_id": conversation_id,
                "message_index": message_index,
                "message_role": message.role,
                "message_text": message.text,
                "response_id": message.response_id,
                "reasoning": {
                    "summary_parts": reasoning_data.get("summary_parts", []),
                    "complete_summary": reasoning_data.get("complete_summary", ""),
                    "timestamp": reasoning_data.get("timestamp", 0),
                    "response_id": reasoning_data.get("response_id", ""),
                },
            }
        )

    except ValueError as e:
        logging.warning(f"Validation error in get_message_reasoning: {e}")
        return jsonify({"error": "Invalid request", "message": str(e)}), 400

    except Exception as e:
        logging.error(f"Unexpected error in get_message_reasoning: {e}", exc_info=True)
        return jsonify(
            {
                "error": "Internal server error",
                "message": "An unexpected error occurred while retrieving reasoning data.",
            }
        ), 500


class StreamEventProcessor:
    """Process streaming responses from the Responses API to replace AssistantEventHandler."""

    def __init__(self, event_queue: Queue[Any]):
        self.event_queue = event_queue
        self.current_response_id: str | None = None
        self.accumulated_text = ""
        self.reasoning_data: Dict[str, Any] = {
            "summary_parts": [],
            "complete_summary": "",
            "timestamp": 0,
            "response_id": "",
        }

    def process_stream(self, stream: Any) -> None:
        """Process the entire stream of ResponseStreamEvent objects with comprehensive error handling."""
        try:
            for event in stream:
                self._handle_stream_event(event)
        except ConnectionError as e:
            logging.error(f"Connection error during stream processing: {e}")
            self.event_queue.put(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Connection lost during response. Please try again.",
                        "error_code": "connection_error",
                        "user_action": "Check your internet connection and try again.",
                    }
                )
            )
        except TimeoutError as e:
            logging.error(f"Timeout error during stream processing: {e}")
            self.event_queue.put(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Response timed out. Please try again.",
                        "error_code": "timeout_error",
                        "user_action": "Try again or check your connection.",
                    }
                )
            )
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error during stream processing: {e}")
            self.event_queue.put(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid response format received. Please try again.",
                        "error_code": "parsing_error",
                        "user_action": "Try again or refresh the page.",
                    }
                )
            )
        except Exception as e:
            logging.error(f"Unexpected error processing stream: {e}", exc_info=True)
            self.event_queue.put(
                json.dumps(
                    {
                        "type": "error",
                        "message": "An error occurred while processing the response. Please try again.",
                        "error_code": "stream_processing_error",
                        "user_action": "Try again or refresh the page if the problem continues.",
                    }
                )
            )

    def _handle_stream_event(self, event: Any) -> None:
        """Handle individual ResponseStreamEvent objects."""
        if not hasattr(event, "type"):
            return

        event_type = event.type

        # Handle actual Responses API event types
        if event_type == "response.created":
            self._handle_response_created(event)
        elif event_type == "response.in_progress":
            self._handle_response_in_progress(event)
        elif event_type == "response.output_item.added":
            self._handle_output_item_added(event)
        elif event_type == "response.content_part.added":
            self._handle_content_part_added(event)
        elif event_type == "response.output_text.delta":
            self._handle_output_text_delta(event)
        elif event_type == "response.output_text.done":
            self._handle_output_text_done(event)
        elif event_type == "response.content_part.done":
            self._handle_content_part_done(event)
        elif event_type == "response.output_item.done":
            self._handle_output_item_done(event)
        elif event_type == "response.completed":
            self._handle_response_completed(event)
        elif event_type == "response.reasoning_summary_part.added":
            self._handle_reasoning_summary_part_added(event)
        elif event_type == "response.reasoning_summary_text.delta":
            self._handle_reasoning_summary_text_delta(event)
        elif event_type == "response.reasoning_summary_text.done":
            self._handle_reasoning_summary_text_done(event)
        elif event_type == "response.reasoning_summary_part.done":
            self._handle_reasoning_summary_part_done(event)
        else:
            # Handle other event types if needed
            logging.warning(f"Unhandled event type {event_type}")

    def _handle_response_created(self, event: Any) -> None:
        """Handle response.created event - response has been created."""
        self.accumulated_text = ""
        # Reset reasoning data for new response
        self.reasoning_data = {
            "summary_parts": [],
            "complete_summary": "",
            "timestamp": 0,
            "response_id": "",
        }

        # Extract response ID if available
        if hasattr(event, "response") and hasattr(event.response, "id"):
            self.current_response_id = event.response.id
        elif hasattr(event, "id"):
            self.current_response_id = event.id

        self.event_queue.put(json.dumps({"type": "text_created", "text": ""}))

    def _handle_response_in_progress(self, event: Any) -> None:
        """Handle response.in_progress event - response is being generated."""
        # This event doesn't need specific handling, just indicates progress
        pass

    def _handle_output_item_added(self, event: Any) -> None:
        """Handle response.output_item.added event - new output item added."""
        # This event indicates a new output item (like text) has been added
        pass

    def _handle_content_part_added(self, event: Any) -> None:
        """Handle response.content_part.added event - new content part added."""
        # This event indicates a new content part has been added
        pass

    def _handle_output_text_delta(self, event: Any) -> None:
        """Handle response.output_text.delta event - equivalent to on_text_delta."""
        delta_text = ""

        # Extract delta text from the event - try multiple possible locations
        if hasattr(event, "delta"):
            if isinstance(event.delta, str):
                delta_text = event.delta
            elif hasattr(event.delta, "text"):
                delta_text = str(event.delta.text)
            else:
                delta_text = str(event.delta)
        elif hasattr(event, "text"):
            delta_text = str(event.text)
        elif hasattr(event, "content_part") and hasattr(event.content_part, "text"):
            delta_text = str(event.content_part.text)
        elif hasattr(event, "output_text") and hasattr(event.output_text, "delta"):
            delta_text = str(event.output_text.delta)

        self.accumulated_text += delta_text

        self.event_queue.put(json.dumps({"type": "text_delta", "delta": delta_text}))

    def _handle_output_text_done(self, event: Any) -> None:
        """Handle response.output_text.done event - text output is complete."""
        final_text = self.accumulated_text

        # Try to get final text from event if available
        if hasattr(event, "text"):
            final_text = str(event.text)
        elif hasattr(event, "content_part") and hasattr(event.content_part, "text"):
            final_text = str(event.content_part.text)

        self.event_queue.put(
            json.dumps(
                {
                    "type": "text_done",
                    "text": final_text,
                    "response_id": self.current_response_id,
                }
            )
        )

    def _handle_content_part_done(self, event: Any) -> None:
        """Handle response.content_part.done event - content part is complete."""
        # This event indicates a content part is complete
        pass

    def _handle_output_item_done(self, event: Any) -> None:
        """Handle response.output_item.done event - output item is complete."""
        # This event indicates an output item is complete
        pass

    def _handle_response_completed(self, event: Any) -> None:
        """Handle response.completed event - final event with complete response information."""
        # Extract response ID for conversation continuity
        if hasattr(event, "response") and hasattr(event.response, "id"):
            self.current_response_id = event.response.id
        elif hasattr(event, "response_id"):
            self.current_response_id = event.response_id
        elif hasattr(event, "id"):
            self.current_response_id = event.id

        self.event_queue.put(
            json.dumps(
                {"type": "response_done", "response_id": self.current_response_id}
            )
        )

    def get_response_id(self) -> str | None:
        """Get the response ID from the processed stream for conversation continuity."""
        return self.current_response_id

    def _handle_reasoning_summary_part_added(self, event: Any) -> None:
        """Handle response.reasoning_summary_part.added event - new reasoning part added."""
        try:
            # Extract reasoning part from the event
            part_text = ""
            if hasattr(event, "part") and event.part is not None:
                if isinstance(event.part, str):
                    part_text = event.part
                elif hasattr(event.part, "text") and event.part.text is not None:
                    part_text = str(event.part.text)
                elif event.part is not None:
                    part_text = str(event.part)
            elif hasattr(event, "text") and event.text is not None:
                part_text = str(event.text)

            if part_text and part_text != "None":
                self.reasoning_data["summary_parts"].append(part_text)

        except AttributeError as e:
            logging.debug(f"Reasoning part event missing expected attributes: {e}")
            # Continue processing - reasoning is optional
        except (TypeError, ValueError) as e:
            logging.warning(f"Error parsing reasoning summary part: {e}")
            # Continue processing - reasoning is optional
        except Exception as e:
            logging.warning(f"Unexpected error processing reasoning summary part: {e}")
            # Continue processing - reasoning failures should not block chat

    def _handle_reasoning_summary_text_delta(self, event: Any) -> None:
        """Handle response.reasoning_summary_text.delta event - reasoning text delta."""
        try:
            # Extract delta text from the event
            delta_text = ""
            if hasattr(event, "delta") and event.delta is not None:
                if isinstance(event.delta, str):
                    delta_text = event.delta
                elif hasattr(event.delta, "text") and event.delta.text is not None:
                    delta_text = str(event.delta.text)
                elif event.delta is not None:
                    delta_text = str(event.delta)
            elif hasattr(event, "text") and event.text is not None:
                delta_text = str(event.text)

            if delta_text and delta_text != "None":
                self.reasoning_data["complete_summary"] += delta_text

        except AttributeError as e:
            logging.debug(f"Reasoning delta event missing expected attributes: {e}")
            # Continue processing - reasoning is optional
        except (TypeError, ValueError) as e:
            logging.warning(f"Error parsing reasoning summary text delta: {e}")
            # Continue processing - reasoning is optional
        except Exception as e:
            logging.warning(
                f"Unexpected error processing reasoning summary text delta: {e}"
            )
            # Continue processing - reasoning failures should not block chat

    def _handle_reasoning_summary_text_done(self, event: Any) -> None:
        """Handle response.reasoning_summary_text.done event - reasoning text complete."""
        try:
            # Extract final reasoning text from event if available
            if hasattr(event, "text") and event.text is not None:
                final_text = str(event.text)
                # Use the final text from the event if it's more complete or if we have no accumulated text
                if (
                    len(final_text) > len(self.reasoning_data["complete_summary"])
                    or not self.reasoning_data["complete_summary"]
                ):
                    self.reasoning_data["complete_summary"] = final_text

            # Set timestamp and response ID
            self.reasoning_data["timestamp"] = int(time.time())
            if self.current_response_id:
                self.reasoning_data["response_id"] = self.current_response_id

        except AttributeError as e:
            logging.debug(f"Reasoning done event missing expected attributes: {e}")
            # Continue processing - reasoning is optional
        except (TypeError, ValueError) as e:
            logging.warning(f"Error parsing reasoning summary text done: {e}")
            # Continue processing - reasoning is optional
        except Exception as e:
            logging.warning(
                f"Unexpected error processing reasoning summary text done: {e}"
            )
            # Continue processing - reasoning failures should not block chat

    def _handle_reasoning_summary_part_done(self, event: Any) -> None:
        """Handle response.reasoning_summary_part.done event - reasoning part complete."""
        try:
            # This event indicates a reasoning part is complete
            # We can use this for validation or cleanup if needed
            pass
        except AttributeError as e:
            logging.debug(f"Reasoning part done event missing expected attributes: {e}")
            # Continue processing - reasoning is optional
        except Exception as e:
            logging.warning(
                f"Unexpected error processing reasoning summary part done: {e}"
            )
            # Continue processing - reasoning failures should not block chat

    def get_reasoning_data(self) -> Dict[str, Any] | None:
        """Get the reasoning data from the processed stream with comprehensive error handling."""
        try:
            # Only return reasoning data if we have meaningful content
            if self.reasoning_data.get("complete_summary") or self.reasoning_data.get(
                "summary_parts"
            ):
                # Validate the reasoning data before returning
                validated_data = validate_reasoning_data(self.reasoning_data.copy())
                if validated_data:
                    logging.debug(
                        f"Successfully retrieved reasoning data with {len(validated_data.get('complete_summary', ''))} characters"
                    )
                return validated_data
            else:
                logging.debug(
                    "No reasoning data available - summary and parts are empty"
                )
            return None
        except ValueError as e:
            logging.warning(f"Reasoning data validation failed: {e}")
            # Return None instead of raising - reasoning is optional
            return None
        except Exception as e:
            logging.warning(f"Unexpected error getting reasoning data: {e}")
            # Return None instead of raising - reasoning is optional
            return None


# StreamingEventHandler removed - now using StreamEventProcessor for Responses API


#################################
####### CHAT TOOL OUTPUT ########
#################################


# process_tool_output function removed - tool calling now handled by Responses API


#################################
########   IMAGE GRID   #########
#################################


@app.route("/get-total-pages")
def get_total_pages() -> str:
    if "username" not in session:
        abort(404, description="Username not in session")
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")
    image_directory: str = os.path.join(
        app.static_folder, "images", session["username"]
    )
    images = sorted(
        [
            os.path.join("images", file)
            for file in os.listdir(image_directory)
            if file.endswith(".png") and not file.endswith(".thumb.png")
        ]
    )

    return str(-(-len(images) // images_per_page))


@app.route("/get-images/<int:page>")
def get_images(page: int) -> str:
    if "username" not in session:
        abort(404, description="Username not in session")
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")
    image_directory: str = os.path.join(
        app.static_folder, "images", session["username"]
    )
    images = sorted(
        [
            os.path.join("static/images/", session["username"], file)
            for file in os.listdir(image_directory)
            if file.endswith(".thumb.jpg") or file.endswith(".thumb.png")
        ],
        reverse=True,
    )

    total_images = len(images)

    # Calculate how many images are on the final page (which is displayed first)
    images_on_first_page = total_images % images_per_page or images_per_page
    if page == 1:
        start = 0
        end = images_on_first_page
    else:
        # Adjust the start and end for pages after the first
        start = images_on_first_page + (page - 2) * images_per_page
        end = start + images_per_page
        if end > total_images:
            end = total_images

    paginated_images = images[start:end]

    return json.dumps(paginated_images)


@app.route("/get-image-metadata/<filename>")
def get_image_metadata(filename: str):
    """Retrieve metadata for a specific image file."""
    if "username" not in session:
        abort(404, description="Username not in session")
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")
    image_path = os.path.join(
        app.static_folder, "images", session["username"], filename
    )
    image = PILImage.open(image_path)
    image.load()  # type: ignore
    # Extract metadata
    metadata = image.info
    if metadata:
        metadata_dict = {key: metadata[key] for key in metadata}
    else:
        metadata_dict = {"error": "No metadata found"}

    width, height = image.size
    metadata_dict["Resolution"] = f"{width}x{height}"

    return json.dumps(metadata_dict)


def detect_followup_file(content_lines: list[str]) -> tuple[bool, int]:
    """
    Detect if a prompt file is a follow-up options file and return column count.

    Returns:
        tuple: (is_followup, total_columns)
    """
    if not content_lines:
        return False, 0

    # Look for header line
    header_line = None
    for line in content_lines:
        stripped = line.strip()
        if stripped.startswith("# columns:"):
            header_line = stripped
            break

    if not header_line:
        return False, 0

    # Find data lines to determine actual column count
    data_lines = [
        line.strip()
        for line in content_lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not data_lines:
        return True, 0  # Header found but no data

    # Count columns from first data line
    first_line_columns = len(data_lines[0].split("||"))

    # Verify it's actually a follow-up file (has || separators)
    if first_line_columns < 2:
        return False, 0

    return True, first_line_columns


@app.route("/prompt-files", methods=["GET"])
def get_prompt_files():
    """Get all prompt files for the current user."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if not app.static_folder:
        return jsonify({"error": "Static folder not configured"}), 500

    username = session["username"]
    prompt_files_dir = os.path.join(app.static_folder, "prompts", username)

    try:
        # Create directory if it doesn't exist
        os.makedirs(prompt_files_dir, exist_ok=True)

        files = []
        for filename in os.listdir(prompt_files_dir):
            if filename.endswith(".txt"):
                file_path = os.path.join(prompt_files_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_lines = f.read().splitlines()

                    file_stats = os.stat(file_path)
                    is_followup, total_columns = detect_followup_file(content_lines)

                    file_data = {
                        "name": os.path.splitext(filename)[0],
                        "content": content_lines,
                        "size": file_stats.st_size,
                        "isFollowUp": is_followup,
                    }

                    if is_followup:
                        file_data["totalColumns"] = total_columns

                    files.append(file_data)
                except Exception as e:
                    # Skip files that can't be read
                    print(f"Warning: Could not read file {filename}: {e}")
                    continue

        # Sort files by name
        files.sort(key=lambda x: x["name"])
        return jsonify(files)

    except Exception as e:
        return jsonify({"error": f"Failed to read prompt files: {str(e)}"}), 500


@app.route("/prompt-files", methods=["POST"])
def save_prompt_file():
    """Create or update a prompt file."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if not app.static_folder:
        return jsonify({"error": "Static folder not configured"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        filename = data.get("name", "").strip()
        content = data.get("content", "")

        if not filename:
            return jsonify({"error": "File name is required"}), 400

        # Validate filename
        if not re.match(r"^[a-zA-Z0-9_-]+$", filename):
            return jsonify(
                {
                    "error": "File name can only contain letters, numbers, underscores, and hyphens"
                }
            ), 400

        username = session["username"]
        prompt_files_dir = os.path.join(app.static_folder, "prompts", username)
        os.makedirs(prompt_files_dir, exist_ok=True)

        file_path = os.path.join(prompt_files_dir, f"{filename}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return jsonify({"success": True, "message": "File saved successfully"})

    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500


@app.route("/prompt-files/<filename>", methods=["GET"])
def get_prompt_file(filename: str):
    """Get a specific prompt file content."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if not app.static_folder:
        return jsonify({"error": "Static folder not configured"}), 500

    try:
        # Validate filename
        if not re.match(r"^[a-zA-Z0-9_-]+$", filename):
            return jsonify({"error": "Invalid filename"}), 400

        username = session["username"]
        prompts_dir = os.path.join(app.static_folder, "prompts", username)
        file_path = os.path.join(prompts_dir, f"{filename}.txt")

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        with open(file_path, "r", encoding="utf-8") as f:
            content_lines = f.read().splitlines()

        file_stats = os.stat(file_path)
        is_followup, total_columns = detect_followup_file(content_lines)

        file_data = {
            "name": filename,
            "content": content_lines,
            "size": file_stats.st_size,
            "isFollowUp": is_followup,
        }

        if is_followup:
            file_data["totalColumns"] = total_columns

        return jsonify(file_data)

    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


@app.route("/prompt-files/<filename>", methods=["DELETE"])
def delete_prompt_file(filename: str):
    """Delete a prompt file."""
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    if not app.static_folder:
        return jsonify({"error": "Static folder not configured"}), 500

    try:
        # Validate filename
        if not re.match(r"^[a-zA-Z0-9_-]+$", filename):
            return jsonify({"error": "Invalid file name"}), 400

        username = session["username"]
        file_path = os.path.join(
            app.static_folder, "prompts", username, f"{filename}.txt"
        )

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        os.remove(file_path)
        return jsonify({"success": True, "message": "File deleted successfully"})

    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
