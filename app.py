import base64
import io
import json
import math
import os
import random
import re
import secrets
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from queue import Queue
from typing import Any, AnyStr, Dict, Generator, Mapping

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
from pydantic import BaseModel, Field
from wand.image import Image as WandImage

import utils
from dynamic_prompts import (
    GridDynamicPromptInfo,
    get_prompts_for_name,
    make_prompt_dynamic,
)

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
    return jsonify(error=str(e)), 404


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["username"] = request.form["username"].strip()
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/share")
def share():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("share.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


class ModerationException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DownloadError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConversationStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class GeneratedImageData:
    local_image_path: str
    revised_prompt: str
    prompt: str
    image_name: str

    def __init__(
        self,
        local_image_path: str,
        revised_prompt: str,
        prompt: str,
        image_name: str,
    ):
        self.local_image_path = local_image_path
        self.revised_prompt = revised_prompt
        self.prompt = prompt
        self.image_name = image_name


class SavedImageData:
    local_image_path: str
    image_name: str

    def __init__(self, local_image_path: str, image_name: str):
        self.local_image_path = local_image_path
        self.image_name = image_name


# Pydantic models for conversation data structures
class ConversationData(BaseModel):
    """Pydantic model for conversation metadata."""

    id: str
    created_at: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    object: str = "conversation"


class ChatMessage(BaseModel):
    """Pydantic model for individual chat messages."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    text: str = Field(..., description="Message content")
    timestamp: int = Field(..., description="Unix timestamp when message was created")
    response_id: str | None = Field(
        None, description="OpenAI response ID for assistant messages"
    )


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
        self, role: str, content: str, response_id: str | None = None
    ) -> None:
        """Add a message to the conversation."""
        message = ChatMessage(
            role=role, text=content, timestamp=int(time.time()), response_id=response_id
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
        self._user_locks = {}
        self._locks_lock = threading.Lock()

        # Add conversation cache for performance optimization
        self._conversation_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes cache TTL

    def _get_user_lock(self, username: str) -> threading.Lock:
        """Get or create a thread lock for a specific user."""
        with self._locks_lock:
            if username not in self._user_locks:
                self._user_locks[username] = threading.Lock()
            return self._user_locks[username]

    def _get_user_file_path(self, username: str) -> str:
        """Get the file path for a user's conversation data."""
        return os.path.join(self.chats_dir, f"{username}.json")

    def _is_cache_valid(self, username: str) -> bool:
        """Check if cached data is still valid."""
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
                    import logging

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
                    import logging

                    logging.error(f"IO error loading conversations for {username}: {e}")
                    return UserConversations()
                except ValueError as e:
                    import logging

                    logging.error(
                        f"Validation error loading conversations for {username}: {e}"
                    )
                    return UserConversations()
                except Exception as e:
                    import logging

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
                import logging

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
            except json.JSONEncodeError as e:
                import logging

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
                import logging

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
    ) -> None:
        """Add a message to a conversation."""
        user_conversations = self._load_user_conversations(username)

        conversation = user_conversations.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {username}"
            )

        # Use the Pydantic model's add_message method
        conversation.add_message(role, content, response_id)

        self._save_user_conversations(username, user_conversations)

    def get_last_response_id(self, username: str, conversation_id: str) -> str | None:
        """Get the last response ID for conversation continuity."""
        conversation = self.get_conversation(username, conversation_id)
        if conversation:
            return conversation.last_response_id
        return None

    def update_conversation_metadata(
        self, username: str, conversation_id: str, **kwargs
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
                import logging

                logging.warning(
                    f"Conversation {conversation_id} not found for user {username}"
                )
                return False

            # Validate and sanitize the title
            if not title or not isinstance(title, str):
                import logging

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

            import logging

            logging.info(
                f"Updated title for conversation {conversation_id} to '{clean_title}'"
            )
            return True

        except ConversationStorageError as e:
            import logging

            logging.error(
                f"Storage error updating title for conversation {conversation_id}: {e}"
            )
            return False
        except Exception as e:
            import logging

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


class ResponsesAPIClient:
    """Client wrapper for OpenAI Responses API with o4-mini model."""

    def __init__(self, openai_client: openai.OpenAI):
        self.client = openai_client
        self.model = "o4-mini"

    def create_response(
        self,
        input_text: str,
        previous_response_id: str | None = None,
        stream: bool = True,
        username: str | None = None,
    ) -> Any:
        """Create a response using the Responses API with o4-mini model."""
        try:
            params = {
                "model": self.model,
                "input": input_text,
                "stream": stream,
                "store": True,  # Store responses for conversation continuity
                "reasoning": {"effort": "high"},
                "instructions": """You are CodeGPT, a large language model trained by OpenAI, based on the o4 architecture. Knowledge cutoff: 2023-10. Current year: 2025.
You are trained to act and respond like a professional software engineer would, with vast knowledge of every programming language and excellent reasoning skills. You write industry-standard clean, elegant code. You output code in Markdown format like so:
```lang
code
```""",
            }

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
        import logging

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
            "retry_after": retry_after,
            "user_action": "Please wait before sending another message.",
        }

    def _handle_api_error(self, error: openai.APIError) -> dict[str, str]:
        """Handle OpenAI API errors with comprehensive error mapping."""
        import logging

        logging.error(f"OpenAI API error: {error}")

        # Handle specific error types with user-friendly messages
        if hasattr(error, "code"):
            if error.code == "model_not_found" or error.code == "model_unavailable":
                return {
                    "error": "model_unavailable",
                    "message": "The o4-mini model is currently unavailable. Please try again in a few minutes.",
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
            if error.status_code == 503:
                return {
                    "error": "service_unavailable",
                    "message": "The AI service is temporarily unavailable. Please try again in a few minutes.",
                    "user_action": "Wait a few minutes and try again.",
                }
            elif error.status_code == 502 or error.status_code == 504:
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
        import logging

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
            print(f"Error in process_stream_with_processor: {e}")
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
            print(f"Error processing stream events: {e}")
            yield {"type": "error", "message": "Error processing response stream"}

    def generate_conversation_title(self, user_message: str) -> str:
        """Generate a conversation title using o3-mini with minimal reasoning."""
        try:
            # Truncate very long messages to avoid excessive API costs
            truncated_message = (
                user_message[:500] if len(user_message) > 500 else user_message
            )

            # Call OpenAI API with o3-mini and minimal reasoning for cost efficiency
            response = self.client.responses.create(
                model="o3-mini",  # Use o3-mini for cost efficiency
                input=f"Generate a title for this conversation:\n\nUser message: {truncated_message}",
                instructions=self._get_title_generation_instructions(),
                stream=False,
                reasoning={"effort": "low"}, # Minimal reasoning for cost efficiency
            )

            # Extract title from response
            if hasattr(response, 'output_text') and response.output_text:
                return self._sanitize_title(response.output_text)
            else:
                import logging
                logging.warning("Empty response from o3-mini for title generation")
                return self._generate_fallback_title()

        except openai.RateLimitError as e:
            import logging

            logging.warning(f"Rate limit exceeded for title generation: {e}")
            return self._generate_fallback_title()

        except openai.APIError as e:
            import logging

            logging.error(f"OpenAI API error during title generation: {e}")
            return self._generate_fallback_title()

        except Exception as e:
            import logging

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
            import logging
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
            import logging
            logging.error(f"Title \"{title.strip()}\" too generic!")
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


def upscale_novelai(
    lowres_response_bytes: io.BytesIO,
    starting_width: int,
    starting_height: int,
    novelai_headers: Mapping[str, str | bytes | None],
) -> io.BytesIO:
    # 640x640 images cost 0 Anlas with Opus, so resize down to that res before sending it to upscale
    max_resolution = 640 * 640
    if starting_width * starting_height > max_resolution:
        resized_image = PILImage.open(lowres_response_bytes)
        resized_width = int(
            math.floor(math.sqrt(max_resolution * (starting_width / starting_height)))
        )
        resized_height = int(
            math.floor(math.sqrt(max_resolution * (starting_height / starting_width)))
        )

        resized_image.thumbnail(
            (resized_width, resized_height), PILImage.Resampling.LANCZOS
        )
        image_bytes = io.BytesIO()
        resized_image.save(image_bytes, format="PNG")
    else:
        image_bytes = lowres_response_bytes
        resized_height = starting_height
        resized_width = starting_width

    data: dict[str, int | str] = {
        "scale": 4,
        "width": resized_width,
        "height": resized_height,
        "image": base64.b64encode(image_bytes.getbuffer()).decode("ascii"),
    }
    # print(json.dumps(data))
    upscale_response = requests.post(
        "https://api.novelai.net/ai/upscale",
        headers=novelai_headers,
        json=data,
    )
    if upscale_response.status_code == 200:
        zipped_file = zipfile.ZipFile(io.BytesIO(upscale_response.content))
        file_bytes = io.BytesIO(zipped_file.read(zipped_file.infolist()[0]))
        return file_bytes
    else:
        body = upscale_response.json()
        error_message = (
            f"NovelAI Upscale {upscale_response.status_code}: {body['message']}"
        )
        raise Exception(error_message)


def generate_novelai_image(
    prompt: str,
    negative_prompt: str | None,
    username: str,
    size: tuple[int, int],
    seed: int = 0,
    upscale: bool = False,
    grid_dynamic_prompt: GridDynamicPromptInfo | None = None,
) -> GeneratedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    revised_prompt = make_prompt_dynamic(
        prompt, username, app.static_folder, seed, grid_dynamic_prompt
    )

    width = size[0]
    height = size[1]

    data = {  # type: ignore
        "action": "generate",
        "model": "nai-diffusion-4-5-full",
        "parameters": {
            "add_original_image": False,
            "cfg_rescale": 0.2,
            "deliberate_euler_ancestral_bug": False,
            "dynamic_thresholding": True,
            "width": width,
            "height": height,
            "legacy": False,
            "legacy_v3_extend": False,
            "n_samples": 1,
            "noise": 0.2,  # Does nothing if no base image
            "noise_schedule": "karras",
            "extra_noise_seed": 0,
            "params_version": 3,
            "prefer_brownian": True,
            "qualityToggle": True,
            "sampler": "k_euler_ancestral",
            "sm": False,
            "sm_dyn": False,
            "steps": 28,  # Max steps before Opus users have to pay money
            "strength": 0.4,
            "scale": 6,
            "ucPreset": 4,
            "seed": seed,
            "v4_prompt": {
                "caption": {
                    "base_caption": revised_prompt,
                    "char_captions": [
                        {
                            "centers": [{"x": 0, "y": 0}],
                            # TODO: Add char_captions
                            "char_caption": "",
                        }
                    ],
                },
                "use_coords": False,
                "use_order": True,
            },
            "v4_negative_prompt": {
                "caption": {
                    "base_caption": negative_prompt,
                    "char_captions": [
                        {"centers": [{"x": 0, "y": 0}], "char_caption": ""}
                    ],
                },
                "use_coords": False,
                "use_order": True,
            },
        },
    }

    novelai_headers = {"authorization": f"Bearer {novelai_api_key}"}

    image_metadata: dict[str, str] = {
        "Prompt": prompt,
        "Revised Prompt": revised_prompt,
        "seed": str(seed),
    }
    if negative_prompt:
        image_metadata["Negative Prompt"] = negative_prompt

    response = requests.post(
        "https://image.novelai.net/ai/generate-image",
        headers=novelai_headers,
        data=json.dumps(data),
    )
    if response.status_code == 200:
        zipped_file = zipfile.ZipFile(io.BytesIO(response.content))
        file_bytes = io.BytesIO(zipped_file.read(zipped_file.infolist()[0]))

        if upscale:
            file_bytes = upscale_novelai(file_bytes, width, height, novelai_headers)

        saved_data = process_image_response(
            file_bytes, prompt, revised_prompt, username, image_metadata
        )
        return GeneratedImageData(
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
        )
    else:
        body = response.json()
        error_message = (
            f"NovelAI Generate Image {response.status_code}: {body['message']}: "
        )
        raise Exception(error_message)


def generate_stability_image(
    prompt: str,
    negative_prompt: str | None,
    username: str,
    aspect_ratio: str = "1:1",
    seed: int = 0,
    upscale: bool = False,
) -> GeneratedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    revised_prompt = make_prompt_dynamic(prompt, username, app.static_folder, seed)

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
        )
    else:
        body = response.json()
        error_message = f"SAI Generate Image {response.status_code}: {body['name']}: "
        for error in body["errors"]:
            error_message += f"{error}\n"
        raise Exception(error_message)


def generate_dalle_image(
    prompt: str,
    username: str,
    size: str = "1024x1024",
    quality: str = "standard",
    strict_follow_prompt: bool = False,
    seed: int = 0,
) -> GeneratedImageData:
    if not app.static_folder:
        raise ValueError("Flask static folder not defined")

    revised_prompt = make_prompt_dynamic(prompt, username, app.static_folder, seed)
    before_prompt = revised_prompt

    if strict_follow_prompt:
        if len(revised_prompt) < 800:
            revised_prompt = (
                "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:\n"
                + revised_prompt
            )
        else:
            revised_prompt = "My prompt has full detail so no need to add more:\n" + revised_prompt

    # Run the prompt through moderation first, I don't want to get my account banned.
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

    saved_data = process_image_response(
        io.BytesIO(decoded_data),
        before_prompt,
        revised_prompt,
        username,
        {
            "Prompt": prompt,
            "Quality": quality,
            "Revised Prompt": revised_prompt,
        },
    )
    return GeneratedImageData(
        saved_data.local_image_path,
        revised_prompt,
        prompt,
        saved_data.image_name,
    )


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

    local_image_path = image_filename
    return SavedImageData(local_image_path, image_name)


def generate_seed_for_provider(provider: str) -> int | None:
    if provider == "stabilityai":
        return random.getrandbits(32)
    elif provider == "novelai":
        return random.getrandbits(64)
    elif provider == "openai":
        # We just use the seed for prompt generation for OpenAI, since the API doesn't allow passing in a seed
        return random.getrandbits(32)
    return


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

        return generate_dalle_image(
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
        upscale = bool(request.form.get("upscale"))

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
        upscale = bool(request.form.get("upscale"))

        if not size:
            raise ValueError("Unable to get 'size' field.")

        split_size = size.split("x")

        return generate_novelai_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            username=session["username"],
            size=(int(split_size[0]), int(split_size[1])),
            seed=seed,
            upscale=upscale,
            grid_dynamic_prompt=grid_dynamic_prompt,
        )

    else:
        raise ValueError(f"Unsupported provider selected: '{provider}'")


def generate_image_grid(
    provider: str,
    prompt: str,
    size: str | None,
    seed: int | None,
    grid_prompt_file: str,
    request: Request,
) -> GeneratedImageData:
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

    if not seed:
        seed = generate_seed_for_provider(provider)

    image_data_list: Dict[str, GeneratedImageData] = dict()
    for dynamic_prompt in dynamic_prompts:
        image_data_list[dynamic_prompt] = generate_image(
            provider,
            prompt,
            size,
            request,
            seed,
            GridDynamicPromptInfo(
                str_to_replace_with=dynamic_prompt, prompt_file=grid_prompt_file
            ),
        )
        print("Image generated!")
        # Don't hammer the API servers
        time.sleep(random.randrange(5, 15))

    file_count = get_file_count(username, app.static_folder)

    image_name = f"{str(file_count).zfill(10)}-grid_{grid_prompt_file}.png"
    image_thumb_name = f"{str(file_count).zfill(10)}-grid_{grid_prompt_file}.thumb.png"
    image_path = os.path.join(app.static_folder, "images", username)
    image_filename = os.path.join(image_path, image_name)
    image_thumb_filename = os.path.join(image_path, image_thumb_name)
    image_thumb_filename_apng = image_thumb_filename.replace(
        ".thumb.png", ".thumb.apng"
    )

    with WandImage() as img:
        for dynamic_prompt, image_data in image_data_list.items():
            with WandImage() as wand_image:  # type: ignore
                wand_image.options["label"] = dynamic_prompt  # type: ignore
                wand_image.read(filename=image_data.local_image_path)  # type: ignore
                img.image_add(wand_image)  # type: ignore
        style = wand.font.Font("Roboto-Light.ttf", 65, "black")
        img.montage(mode="concatenate", font=style)  # type: ignore
        img.save(filename=image_filename)  # type: ignore

    image_to_copy = PILImage.open(image_data_list[dynamic_prompts[0]].local_image_path)
    png_info = PngInfo()
    for key, value in image_to_copy.info.items():
        if isinstance(key, str):
            png_info.add_text(key, value)
    target_image = PILImage.open(image_filename)
    target_image.save(image_filename, pnginfo=png_info)

    with WandImage() as animated_img:
        for dynamic_prompt, image_data in image_data_list.items():
            with WandImage(
                filename=image_data.local_image_path.replace(".png", ".thumb.jpg")
            ) as frame_image:  # type: ignore
                frame_image.delay = 100
                animated_img.sequence.append(frame_image)  # type: ignore
        animated_img.coalesce()
        animated_img.optimize_layers()
        animated_img.format = "apng"
        animated_img.save(filename=image_thumb_filename_apng)  # type: ignore
    # This is really weird but ImageMagick refuses to write an animated apng if it doesn't end in .apng
    # So we have to do this song and dance to get our animated .thumb.png
    os.rename(image_thumb_filename_apng, image_thumb_filename)

    return GeneratedImageData(
        local_image_path=image_filename,
        revised_prompt=image_data_list[dynamic_prompts[0]].revised_prompt,
        prompt=prompt,
        image_name=image_name,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        local_image_path = None
        image_name = None
        prompt = None
        revised_prompt = None
        error_message = None
        provider = request.form.get("provider")
        size = request.form.get("size")
        prompt = request.form.get("prompt")
        seed = request.form.get("seed")
        if seed and seed.strip():
            seed = int(seed)
        else:
            seed = None

        try:
            if not prompt or not prompt.strip():
                raise ValueError("Please provide a prompt!")
            if not provider:
                raise ValueError("Unable to get provider filed from form!")
            advanced_generate_grid = bool(request.form.get("advanced-generate-grid"))
            if advanced_generate_grid:
                grid_prompt_file = request.form.get("grid-prompt-file")
                if not grid_prompt_file:
                    raise ValueError(
                        f"Generate grid enabled, but no prompt file provided! {grid_prompt_file}"
                    )
                generated_image_data = generate_image_grid(
                    provider, prompt, size, seed, grid_prompt_file, request
                )
                local_image_path = generated_image_data.local_image_path
                image_name = generated_image_data.image_name
                prompt = generated_image_data.prompt
                revised_prompt = generated_image_data.revised_prompt
                return render_template(
                    "result-section.html",
                    local_image_path=local_image_path,
                    revised_prompt=revised_prompt,
                    prompt=prompt,
                    image_name=image_name,
                    error_message=error_message,
                )
            else:
                generated_image_data = generate_image(
                    provider, prompt, size, request, seed
                )
                local_image_path = generated_image_data.local_image_path
                image_name = generated_image_data.image_name
                prompt = generated_image_data.prompt
                revised_prompt = generated_image_data.revised_prompt
                return render_template(
                    "result-section.html",
                    local_image_path=local_image_path,
                    revised_prompt=revised_prompt,
                    prompt=prompt,
                    image_name=image_name,
                    error_message=error_message,
                )
        except ModerationException as e:
            error_message = f"Your prompt doesn't pass OpenAI moderation. It triggers the following flags: {e.message}. Please adjust your prompt."
            return render_template(
                "result-section.html",
                local_image_path=local_image_path,
                revised_prompt=revised_prompt,
                prompt=prompt,
                image_name=image_name,
                error_message=error_message,
            )
        except openai.BadRequestError as e:
            error = json.loads(e.response.content)
            error_message = error["error"]["message"]
            error_code = error["error"]["code"]
            if error_code == "content_policy_violation":
                error_message = "OpenAI Image Generation has generated an image that doesn't pass it's own moderation filters. You may want to adjust your prompt slightly."
            return render_template(
                "result-section.html",
                local_image_path=local_image_path,
                revised_prompt=revised_prompt,
                prompt=prompt,
                image_name=image_name,
                error_message=error_message,
            )
        except Exception as e:
            error = str(e)
            exc_type, _, exc_tb = sys.exc_info()
            fname = (
                os.path.split(exc_tb.tb_frame.f_code.co_filename)[1] if exc_tb else ""
            )
            error_message = f"Error processing request: {exc_type} {error}: {fname}"
            return render_template(
                "result-section.html",
                local_image_path=local_image_path,
                revised_prompt=revised_prompt,
                prompt=prompt,
                image_name=image_name,
                error_message=error_message,
            )

        return render_template(
            "result-section.html",
            local_image_path=local_image_path,
            revised_prompt=revised_prompt,
            prompt=prompt,
            image_name=image_name,
            error_message=error_message,
        )

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
        success = conversation_manager.update_conversation_title(username, conversation_id, new_title)
        
        if success:
            # Return updated conversation list
            conversations = conversation_manager.list_conversations(username)
            return jsonify({
                "success": True,
                "message": "Title updated successfully",
                "conversations": conversations
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update conversation title"
            }), 400
            
    except Exception as e:
        import logging
        logging.error(f"Error updating conversation title: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


# Old get_message_list function removed - now using ConversationManager.get_message_list()


eos_str = "␆␄"


@app.route("/chat", methods=["GET", "POST"])  # type: ignore
def converse():
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
            print(f"Using existing conversation: {conversation_id}")
        else:
            # Create new conversation with temporary title
            chat_name = request.json.get("chat_name", "New Chat")
            conversation_id = conversation_manager.create_conversation(
                username, chat_name
            )
            print(f"Created new conversation: {conversation_id}")

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
                        import logging

                        logging.info(
                            f"Successfully generated title '{generated_title}' for conversation {conversation_id}"
                        )
                    else:
                        import logging

                        logging.warning(
                            f"Failed to update title for conversation {conversation_id}"
                        )

                except Exception as e:
                    import logging

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

                # Get the response ID and final text for storage
                response_id = event_processor.get_response_id()
                final_text = event_processor.accumulated_text

                if final_text and response_id:
                    try:
                        # Store assistant response in conversation
                        conversation_manager.add_message(
                            username,
                            conversation_id,
                            "assistant",
                            final_text,
                            response_id,
                        )
                    except ConversationStorageError as e:
                        import logging

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
                elif not final_text:
                    import logging

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
                import logging

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
                import logging

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
                import logging

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


class StreamEventProcessor:
    """Process streaming responses from the Responses API to replace AssistantEventHandler."""

    def __init__(self, event_queue: Queue[Any]):
        self.event_queue = event_queue
        self.current_response_id: str | None = None
        self.accumulated_text = ""

    def process_stream(self, stream: Any) -> None:
        """Process the entire stream of ResponseStreamEvent objects with comprehensive error handling."""
        try:
            for event in stream:
                self._handle_stream_event(event)
        except ConnectionError as e:
            import logging

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
            import logging

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
            import logging

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
            import logging

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
        else:
            # Handle other event types if needed
            print(f"Unhandled event type: {event_type}")

    def _handle_response_created(self, event: Any) -> None:
        """Handle response.created event - response has been created."""
        self.accumulated_text = ""
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
