import base64
from importlib import metadata
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
from collections import deque
from queue import Queue
from typing import Any, AnyStr, Dict, Generator, Mapping

import openai
import requests
from pydantic import BaseModel, Field
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
from openai import AssistantEventHandler
from openai.types.beta.threads import Text, TextContentBlock, TextDelta
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
from openai.types.beta.threads.runs import FunctionToolCall, ToolCall, ToolCallDelta
from openai.types.shared.metadata import Metadata
from openai.types.responses.response_stream_event import ResponseStreamEvent
from PIL import Image as PILImage
from PIL.PngImagePlugin import PngInfo
import wand
import wand.font
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


class GeneratedImageData:
    image_url: str
    local_image_path: str
    revised_prompt: str
    prompt: str
    image_name: str

    def __init__(
        self,
        image_url: str,
        local_image_path: str,
        revised_prompt: str,
        prompt: str,
        image_name: str,
    ):
        self.image_url = image_url
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

    def _get_user_file_path(self, username: str) -> str:
        """Get the file path for a user's conversation data."""
        return os.path.join(self.chats_dir, f"{username}.json")

    def _load_user_conversations(self, username: str) -> UserConversations:
        """Load all conversations for a user from their JSON file using Pydantic models."""
        user_file = self._get_user_file_path(username)
        if os.path.exists(user_file):
            try:
                with open(user_file, "r") as file:
                    data = json.load(file)
                    # Use Pydantic's parse_obj to create UserConversations directly
                    return UserConversations.model_validate({"conversations": data})
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"Error loading conversations for {username}: {e}")
                return UserConversations()
        return UserConversations()

    def _save_user_conversations(
        self, username: str, user_conversations: UserConversations
    ) -> None:
        """Save all conversations for a user to their JSON file using Pydantic models."""
        user_file = self._get_user_file_path(username)
        try:
            with open(user_file, "w") as file:
                # Convert Pydantic models to JSON-serializable format
                data = {}
                for conv_id, conversation in user_conversations.conversations.items():
                    data[conv_id] = conversation.model_dump()
                json.dump(data, file, indent=2)
        except IOError as e:
            print(f"Error saving conversations for {username}: {e}")
            raise

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
```"""
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
        """Handle rate limiting errors."""
        print(f"Rate limit exceeded: {error}")
        return {
            "error": "rate_limit",
            "message": "Too many requests. Please wait a moment before trying again.",
        }

    def _handle_api_error(self, error: openai.APIError) -> dict[str, str]:
        """Handle OpenAI API errors."""
        print(f"OpenAI API error: {error}")

        # Handle specific error types
        if hasattr(error, "code"):
            if error.code == "model_not_found":
                return {
                    "error": "model_unavailable",
                    "message": "The o4-mini model is currently unavailable. Please try again later.",
                }
            elif error.code == "insufficient_quota":
                return {
                    "error": "quota_exceeded",
                    "message": "API quota exceeded. Please check your OpenAI account.",
                }

        return {
            "error": "api_error",
            "message": "An error occurred while processing your request. Please try again.",
        }

    def _handle_general_error(self, error: Exception) -> dict[str, str]:
        """Handle general errors."""
        print(f"General error in ResponsesAPIClient: {error}")
        return {
            "error": "general_error",
            "message": "An unexpected error occurred. Please try again.",
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
            # TODO: We need to remove this field, we don't actually get a URL from Stability AI so just stub it
            "https://image.novelai.net",
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
            # TODO: We need to remove this field, we don't actually get a URL from Stability AI so just stub it
            "https://platform.stability.ai/",
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
    style: str = "vivid",
    strict_follow_prompt: bool = False,
) -> GeneratedImageData:
    before_prompt = prompt
    if strict_follow_prompt:
        if len(prompt) < 800:
            prompt = (
                "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:\n"
                + prompt
            )
        else:
            prompt = "My prompt has full detail so no need to add more:\n" + prompt

    # Run the prompt through moderation first, I don't want to get my account banned.
    moderation = client.moderations.create(input=prompt)
    for result in moderation.results:
        if result.flagged:
            flagged_categories = ""
            for category, flagged in result.categories.__dict__.items():
                if flagged:
                    flagged_categories = flagged_categories + category + ", "
            if len(flagged_categories) > 0:
                flagged_categories = flagged_categories[:-2]
            raise ModerationException(message=flagged_categories)

    # Call DALL-E 3 API
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,  # type: ignore
        style=style,  # type: ignore
        quality=quality,  # type: ignore
        n=1,
    )
    if not response.data or not response.data[0].url:
        raise DownloadError("Was not able to get image url")
    image_url = response.data[0].url
    print(f"url: {image_url}")
    revised_prompt = response.data[0].revised_prompt

    # Download the image
    image_response = requests.get(image_url)
    if image_response.status_code == 200 and revised_prompt:
        saved_data = process_image_response(
            io.BytesIO(image_response.content),
            before_prompt,
            revised_prompt,
            username,
            {
                "Prompt": prompt,
                "Quality": quality,
                "Style": style,
                "Revised Prompt": revised_prompt,
            },
        )
        return GeneratedImageData(
            image_url,
            saved_data.local_image_path,
            revised_prompt,
            prompt,
            saved_data.image_name,
        )
    else:
        raise DownloadError(f"Error downloading image {image_response.status_code}")


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
    if provider == "openai":
        quality = request.form.get("quality")
        style = request.form.get("style")
        strict_follow_prompt = request.form.get("add-follow-prompt")

        if not size:
            raise ValueError("Unable to get 'size' field.")
        if not quality:
            raise ValueError("Unable to get 'quality' field.")
        if not style:
            raise ValueError("Unable to get 'style' field.")

        return generate_dalle_image(
            prompt,
            session["username"],
            size,
            quality,
            style,
            bool(strict_follow_prompt),
        )
    elif provider == "stabilityai":
        negative_prompt = request.form.get("negative_prompt")
        aspect_ratio = request.form.get("aspect_ratio")
        upscale = bool(request.form.get("upscale"))

        if not seed:
            raise ValueError("Unable to get 'seed' field.")
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

        if not seed:
            raise ValueError("Unable to get 'seed' field.")
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
        image_url="none",
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
        image_url = None
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
                image_url = generated_image_data.image_url
                local_image_path = generated_image_data.local_image_path
                image_name = generated_image_data.image_name
                prompt = generated_image_data.prompt
                revised_prompt = generated_image_data.revised_prompt
                return render_template(
                    "result-section.html",
                    image_url=image_url,
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
                image_url = generated_image_data.image_url
                local_image_path = generated_image_data.local_image_path
                image_name = generated_image_data.image_name
                prompt = generated_image_data.prompt
                revised_prompt = generated_image_data.revised_prompt
                return render_template(
                    "result-section.html",
                    image_url=image_url,
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
                image_url=image_url,
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
                error_message = "DALL-E 3 has generated an image that doesn't pass it's own moderation filters. You may want to adjust your prompt slightly."
            return render_template(
                "result-section.html",
                image_url=image_url,
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
                image_url=image_url,
                local_image_path=local_image_path,
                revised_prompt=revised_prompt,
                prompt=prompt,
                image_name=image_name,
                error_message=error_message,
            )

        return render_template(
            "result-section.html",
            image_url=image_url,
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
            # Create new conversation
            chat_name = request.json.get("chat_name", "New Chat")
            conversation_id = conversation_manager.create_conversation(
                username, chat_name
            )
            print(f"Created new conversation: {conversation_id}")

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
            """Start streaming thread using Responses API."""
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
                    event_queue.put(
                        json.dumps({"type": "error", "message": stream["message"]})
                    )
                    return

                # Process the stream
                event_processor.process_stream(stream)

                # Get the response ID and final text for storage
                response_id = event_processor.get_response_id()
                final_text = event_processor.accumulated_text

                if final_text and response_id:
                    # Store assistant response in conversation
                    conversation_manager.add_message(
                        username, conversation_id, "assistant", final_text, response_id
                    )

            except Exception as e:
                print(f"Error in responses stream thread: {e}")
                event_queue.put(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "An error occurred while processing your request.",
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
        """Process the entire stream of ResponseStreamEvent objects."""
        try:
            for event in stream:
                self._handle_stream_event(event)
        except Exception as e:
            print(f"Error processing stream: {e}")
            self.event_queue.put(
                json.dumps(
                    {"type": "error", "message": "Error processing response stream"}
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


# Keep the old StreamingEventHandler for backward compatibility during migration
class StreamingEventHandler(AssistantEventHandler):
    def __init__(self, event_queue: Queue[Any]):
        self.event_queue = event_queue
        super().__init__()

    def on_text_created(self, text: Text) -> None:
        self.event_queue.put(json.dumps({"type": "text_created", "text": text.value}))

    def on_text_delta(
        self,
        delta: TextDelta,
        snapshot: Text,
    ):
        self.event_queue.put(json.dumps({"type": "text_delta", "delta": delta.value}))

    def on_text_done(self, text: Text) -> None:
        self.event_queue.put(json.dumps({"type": "text_done", "text": text.value}))

    def on_tool_call_created(self, tool_call: ToolCall):
        # TODO: Need to hook this up properly
        self.event_queue.put(
            json.dumps({"type": "tool_call_created", "tool_call": tool_call})
        )

    def on_tool_call_delta(self, delta: ToolCallDelta, snapshot: ToolCall):
        self.event_queue.put(
            json.dumps(
                {"type": "tool_call_delta", "delta": delta, "snapshot": snapshot}
            )
        )


#################################
####### CHAT TOOL OUTPUT ########
#################################


def process_tool_output(
    username: str, run_id: str, thread_id: str, tool_calls: list[ToolCall]
):  # type: ignore
    tool_outputs: list[ToolOutput] = []
    for call in tool_calls:
        tool_output = ToolOutput(tool_call_id=call.id)
        if not isinstance(call, FunctionToolCall):
            continue
        output_result: dict[str, str] = dict()
        if call.function.name == "generate_dalle_image":
            print(call.function.name)
            arguments = json.loads(call.function.arguments)
            if "prompt" not in arguments:
                raise Exception(
                    "'prompt' has not been passed to the generate_dalle_image argument!"
                )
            try:
                generated_image_data = generate_dalle_image(
                    arguments["prompt"], username, strict_follow_prompt=True
                )
                output_result["image_url"] = url_for(
                    "static",
                    filename="images/"
                    + username
                    + "/"
                    + generated_image_data.image_name,
                )
                print(output_result["image_url"])
                output_result["revised_prompt"] = generated_image_data.revised_prompt
            except ModerationException as e:
                output_result["error_message"] = (
                    f"Your prompt doesn't pass OpenAI moderation. It triggers the following flags: {e.message}. Please adjust your prompt."
                )
            except openai.BadRequestError as e:
                error = json.loads(e.response.content)
                error_message = error["error"]["message"]
                error_code = error["error"]["code"]
                if error_code == "content_policy_violation":
                    error_message = "DALL-E 3 has generated an image that doesn't pass it's own moderation filters. You may want to adjust your prompt slightly."
                output_result["error_message"] = error_message
        tool_output["output"] = json.dumps(output_result)
        tool_outputs.append(tool_output)
    client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id, thread_id=thread_id, tool_outputs=tool_outputs
    )


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
