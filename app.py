import utils
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    stream_with_context,
    Response,
)
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from pygments.formatters import HtmlFormatter
import markdown
from typing_extensions import override
import openai
from openai import AssistantEventHandler
import requests
import threading
from queue import Queue
from collections import deque
import sys, os, io, time, json, re, tempfile
import secrets

app = Flask(__name__)

# Initialize the OpenAI client
client = openai.OpenAI()

stability_api_key = os.environ.get("STABILITY_API_KEY")

secret_key_filename = "secret-key.txt"
if not os.path.isfile(secret_key_filename):
    with open(secret_key_filename, "a") as f:
        f.write(secrets.token_urlsafe(16))
with open(secret_key_filename, "r") as f:
    app.secret_key = f.read()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["username"] = request.form["username"]
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


class ModerationException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class DownloadError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class GeneratedImageData:
    image_url: str
    local_image_path: str
    revised_prompt: str
    prompt: str
    image_name: str

    def __init__(self, image_url, local_image_path, revised_prompt, prompt, image_name):
        self.image_url = image_url
        self.local_image_path = local_image_path
        self.revised_prompt = revised_prompt
        self.prompt = prompt
        self.image_name = image_name


class SavedImageData:
    local_image_path: str
    image_name: str

    def __init__(self, local_image_path, image_name):
        self.local_image_path = local_image_path
        self.image_name = image_name


def upscale_stability_creative(
    lowres_response: requests.Response, prompt: str, stability_headers: object
) -> requests.Response:
    lowres_image = Image.open(io.BytesIO(lowres_response.content))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        lowres_image.save(tmp_file.name, "PNG")

    upscale_response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/upscale/creative",
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


def generate_stability_image(
    prompt: str,
    negative_prompt: str,
    username: str,
    aspect_ratio: str = "1:1",
    seed: int = 0,
    upscale: bool = False,
) -> GeneratedImageData:
    data = {
        "prompt": prompt,
        "output_format": "png",
        # These have been removed from ultra and core APIs
        # "mode": "text-to-image",
        # "model": model,
        "seed": seed,
        "aspect_ratio": aspect_ratio,
    }
    print(f"using seed: {seed}")
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
        f"https://api.stability.ai/v2beta/stable-image/generate/ultra",
        headers=stability_headers,
        files={"none": ""},
        data=data,
    )

    image_metadata = {"Prompt": prompt}
    if negative_prompt:
        image_metadata["Negative Prompt"] = negative_prompt
    if "seed" in response.headers:
        image_metadata["seed"] = response.headers["seed"]
    if response.status_code == 200:
        if upscale:
            response = upscale_stability_creative(response, prompt, stability_headers)
        saved_data = process_image_response(response, prompt, username, image_metadata)
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
        size=size,
        style=style,
        quality=quality,
        n=1,
    )
    image_url = response.data[0].url
    print(f"url: {image_url}")
    revised_prompt = response.data[0].revised_prompt

    # Download the image
    image_response = requests.get(image_url)
    if image_response.status_code == 200:
        saved_data = process_image_response(
            image_response,
            before_prompt,
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


def process_image_response(
    image_response, before_prompt: str, username: str, metadata_to_add: dict[str, str]
) -> SavedImageData:
    image_path = os.path.join(app.static_folder, "images", username)
    # Make sure the path directory exists first
    os.makedirs(image_path, exist_ok=True)

    file_count = 0
    for path in os.listdir(image_path):
        file_path = os.path.join(image_path, path)
        if file_path.endswith(".png") and os.path.isfile(file_path):
            file_count += 1
    cleaned_prompt = before_prompt.strip().lower()
    cleaned_prompt = (
        utils.remove_stop_words(cleaned_prompt.replace(".", " ").replace(",", " "))
        .replace("  ", " ")
        .replace(" ", "_")[:30]
    )
    image_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.png"
    image_thumb_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.thumb.jpg"
    image_filename = os.path.join(image_path, image_name)
    image_thumb_filename = os.path.join(image_path, image_thumb_name)

    # Create an in-memory image from the downloaded content
    image = Image.open(io.BytesIO(image_response.content))

    # Create a thumbnail
    thumb_image = image.copy()
    aspect_ratio = image.height / image.width
    new_height = int(256 * aspect_ratio)
    thumb_image.thumbnail((256, new_height))

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
        quality = request.form.get("quality")
        style = request.form.get("style")
        prompt = request.form.get("prompt")
        strict_follow_prompt = request.form.get("add-follow-prompt")
        print(
            f"Provider: {provider}, Size: {size}, Quality: {quality}, Style: {style}, Prompt: {prompt}, strict_follow_prompt: {strict_follow_prompt}"
        )
        if not prompt.strip():
            print("No prompt provided, not doing anything.")
            return render_template("index.html")
        try:
            if provider == "openai":
                generated_image_data = generate_dalle_image(
                    prompt,
                    session["username"],
                    size,
                    quality,
                    style,
                    strict_follow_prompt,
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
            elif provider == "stabilityai":
                negative_prompt = request.form.get("negative_prompt")
                aspect_ratio = request.form.get("aspect_ratio")
                model = request.form.get("model")
                seed = request.form.get("seed")
                upscale = request.form.get("upscale")
                generated_image_data = generate_stability_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    username=session["username"],
                    aspect_ratio=aspect_ratio,
                    seed=seed,
                    upscale=upscale,
                )
                image_url = generated_image_data.image_url
                local_image_path = generated_image_data.local_image_path
                image_name = generated_image_data.image_name
                prompt = generated_image_data.prompt
                # This is identical to prompt with Stability AI
                revised_prompt = generated_image_data.revised_prompt
                return render_template(
                    "result-section.html",
                    image_url=image_url,
                    local_image_path=local_image_path,
                    revised_prompt=prompt,
                    prompt=prompt,
                    image_name=image_name,
                    error_message=error_message,
                )
            else:
                raise ValueError(f"Unsupported provider selected: '{provider}'")
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
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
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
def get_all_conversations():
    if "username" not in session:
        return None

    user_file = os.path.join(app.static_folder, "chats", f'{session["username"]}.json')
    if os.path.exists(user_file):
        with open(user_file, "r") as file:
            chat = json.load(file)
    else:
        with open(user_file, "a") as file:
            chat = dict()
            file.write(json.dumps(chat))
    return json.dumps(chat)


def get_message_list(thread_id: str):
    message_list = client.beta.threads.messages.list(thread_id, limit=100)
    all_messages = deque()
    for message in message_list.data:
        if message.content:
            for msg_content in message.content:
                all_messages.appendleft(
                    {
                        "role": message.role,
                        "text": msg_content.text.value,
                    }
                )
    return list(all_messages)


eos_str = "␆␄"


@app.route("/chat", methods=["GET", "POST"])
def converse():
    if "username" not in session:
        return redirect(url_for("login"))

    # Need to change how we fetch the thread_id depending on if POST or GET.
    thread_id = (
        request.json.get("thread_id")
        if request.method == "POST"
        else request.args.get("thread_id")
    )
    user_file = os.path.join(app.static_folder, "chats", f'{session["username"]}.json')

    # Load existing conversation or start a new one
    if os.path.exists(user_file):
        with open(user_file, "r") as file:
            chat = json.load(file)
    else:
        with open(user_file, "a") as file:
            chat = dict()
            file.write(json.dumps(chat))
    if request.method == "GET":
        return json.dumps(
            {"threadId": thread_id, "messages": get_message_list(thread_id)}
        )
    elif request.method == "POST":
        user_input = request.json.get("user_input")
        if not user_input:
            return {"error": "No input provided"}, 400

        if thread_id and thread_id in chat:
            print("Have thread")
            thread = client.beta.threads.retrieve(thread_id)
        else:
            print("Need to create thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            chat_name = re.sub(r"[^\w_. -]", "_", request.json.get("chat_name"))
            thread_data = {
                "id": thread.id,
                "created_at": thread.created_at,
                "metadata": thread.metadata,
                "object": thread.object,
            }
            chat[thread_id] = {"data": thread_data, "chat_name": chat_name}

        # TODO: Allow listing assistants
        # Regular ChatGPT-like ID
        # assistant_id = "asst_nYZeL982wB4AgoX4M7lfq7Qv"
        # CodeGPT
        assistant_id = "asst_FX4sCfRsD6G3Vvc84ozABA8N"
        # StoryGPT
        # assistant_id = "asst_aGGDp8e82QjnbkLk4kgXzBT1"
        assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)

        thread_message = client.beta.threads.messages.create(
            thread_id, role="user", content=user_input
        )
        message_list = get_message_list(thread_id)

        event_queue = Queue()

        def start_stream_thread(event_queue, thread_id, assistant_id):
            event_handler = StreamingEventHandler(event_queue)
            with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=event_handler,
            ) as stream:
                stream.until_done()

        def stream_events(thread_id, assistant_id, message_list):
            yield f"{json.dumps(json.dumps({ 'type': 'message_list', 'threadId': thread_id, 'messages': message_list}))}{eos_str}"
            event_queue = Queue()
            # Start the stream in a separate thread
            threading.Thread(
                target=start_stream_thread, args=(event_queue, thread_id, assistant_id)
            ).start()

            # Yield from queue as events come
            while True:
                event = event_queue.get()  # This will block until an item is available
                yield event + eos_str

        chat[thread_id]["last_update"] = time.time()
        chat[thread_id]["assistant_id"] = assistant_id
        with open(user_file, "w") as file:
            json.dump(chat, file)

        return Response(
            stream_with_context(stream_events(thread_id, assistant_id, message_list)),
            mimetype="text/plain",
        )


class StreamingEventHandler(AssistantEventHandler):
    def __init__(self, event_queue):
        self.event_queue = event_queue
        super().__init__()

    def on_text_created(self, text) -> None:
        self.event_queue.put(json.dumps({"type": "text_created", "text": text.value}))

    def on_text_delta(
        self,
        delta: openai.types.beta.threads.TextDelta,
        snapshot: openai.types.beta.threads.Text,
    ):
        self.event_queue.put(json.dumps({"type": "text_delta", "delta": delta.value}))

    def on_text_done(self, text) -> None:
        self.event_queue.put(json.dumps({"type": "text_done", "text": text.value}))

    def on_tool_call_created(self, tool_call):
        # TODO: Need to hook this up properly
        self.event_queue.put(
            json.dumps({"type": "tool_call_created", "tool_call": tool_call})
        )

    def on_tool_call_delta(self, delta, snapshot):
        self.event_queue.put(
            json.dumps(
                {"type": "tool_call_delta", "delta": delta, "snapshot": snapshot}
            )
        )


#################################
####### CHAT TOOL OUTPUT ########
#################################


def process_tool_output(username: str, run_id: str, thread_id: str, tool_calls):
    tool_outputs = []
    for call in tool_calls:
        tool_output = {"tool_call_id": call.id}
        output_result = dict()
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
    run = client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id, thread_id=thread_id, tool_outputs=tool_outputs
    )


#################################
########   IMAGE GRID   #########
#################################


@app.route("/get-total-pages")
def get_total_pages():
    if "username" not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted(
        [
            os.path.join("images", file)
            for file in os.listdir(image_directory)
            if file.endswith(".png")
        ]
    )

    return str(-(-len(images) // images_per_page))


@app.route("/get-images/<int:page>")
def get_images(page):
    if "username" not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted(
        [
            os.path.join("static/images/", session["username"], file)
            for file in os.listdir(image_directory)
            if file.endswith(".jpg")
        ],
        reverse=True,
    )

    total_images = len(images)
    total_pages = (total_images + images_per_page - 1) // images_per_page

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
def get_image_metadata(filename):
    if "username" not in session:
        return None
    image_path = os.path.join(
        app.static_folder, "images", session["username"], filename
    )
    image = Image.open(image_path)
    image.load()
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
