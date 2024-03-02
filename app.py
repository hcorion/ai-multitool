from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from pygments.formatters import HtmlFormatter
import markdown
import markdown.extensions.fenced_code
import openai
import requests
from collections import deque
import os, io, secrets, time
import json
import re

app = Flask(__name__)

# Initialize the OpenAI client
client = openai.OpenAI()

secret_key_filename="secret-key.txt"
if not os.path.isfile(secret_key_filename):
    with open(secret_key_filename, 'a') as f: f.write(secrets.token_urlsafe(16))
with open(secret_key_filename, 'r') as f:
    app.secret_key = f.read()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

def remove_stop_words(input_string):
    # List of stop words
    stop_words = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
                      "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
                      "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
                      "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
                      "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about",
                      "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up",
                      "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when",
                      "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
                      "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
                      "photo", "artwork", "painting", "impressionist", "promotional", "marketing", "full", "shot", "pixel", "art", 
                      "product", "image", "showcasing", "high", "resolution", "lineart", "b&w", "illustration", "ink", "detail", "detailed",
                      "styled", "style", "hdr", "photoreal", "hyperreal", "photo-real", "hyper-real", "hyper-realistic", "realistic", 
                      "professional", "photography", "concept", "depicts", "depicted", "depiction", "create", "digital", "vector", 
                      "produce", "realistic", "depict", "depiction"])

    # Splitting the input string into words
    words = input_string.lower().split()

    # Filtering out the stop words
    filtered_words = [word for word in words if word not in stop_words]

    # Joining the remaining words back into a string
    return ' '.join(filtered_words)

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

def generate_dalle_image(prompt: str, username: str, size: str = "1024x1024", quality: str = "standard", style: str = "vivid", strict_follow_prompt: bool = False) -> GeneratedImageData:
    before_prompt = prompt
    if strict_follow_prompt:
        if len(prompt) < 800:
            prompt = "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:\n" + prompt
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
            raise ModerationException(message = flagged_categories)
        
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
        image_path = os.path.join(app.static_folder, "images", username)
        # Make sure the path directory exists first
        os.makedirs(image_path, exist_ok=True)

        file_count = 0
        for path in os.listdir(image_path):
            file_path = os.path.join(image_path, path)
            if file_path.endswith(".png") and os.path.isfile(file_path):
                file_count += 1
        cleaned_prompt = before_prompt.strip().lower()
        cleaned_prompt = remove_stop_words(cleaned_prompt.replace('.', ' ').replace(',', ' ')).replace('  ', ' ').replace(' ', '_')[:30]
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
        metadata.add_text("Prompt", prompt)
        metadata.add_text("Quality", quality)
        metadata.add_text("Style", style)
        metadata.add_text("Revised Prompt", revised_prompt)
        # Save the image with metadata directly to disk
        with open(image_filename, 'wb') as f:
            image.save(f, "PNG", pnginfo=metadata, optimize=True, compression_level=9)
        with open(image_thumb_filename, 'wb') as f:
            thumb_image.save(f, "JPEG", quality=75)

        local_image_path = image_filename
        return GeneratedImageData(image_url, local_image_path, revised_prompt, prompt, image_name)
    else:
        raise DownloadError(f"Error downloading image {image_response.status_code}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        image_url = None
        local_image_path = None
        image_name = None
        prompt = None
        revised_prompt = None
        error_message = None
        size = request.form.get('size')
        quality = request.form.get('quality')
        style = request.form.get('style')
        prompt = request.form.get('prompt')
        strict_follow_prompt = request.form.get('add-follow-prompt')
        print(f"Size: {size}, Quality: {quality}, Style: {style}, Prompt: {prompt}, strict_follow_prompt: {strict_follow_prompt}")
        if not prompt.strip():
            print("No prompt provided, not doing anything.")
            return render_template('index.html')
        try:
            generated_image_data = generate_dalle_image(prompt, session["username"], size, quality, style, strict_follow_prompt)
            image_url = generated_image_data.image_url
            local_image_path = generated_image_data.local_image_path
            image_name = generated_image_data.image_name
            prompt = generated_image_data.prompt
            revised_prompt = generated_image_data.revised_prompt
            return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, error_message=error_message)
        except ModerationException as e:
            error_message = f"Your prompt doesn't pass OpenAI moderation. It triggers the following flags: {e.message}."
            return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, error_message=error_message)
        except openai.BadRequestError as e:
            error = json.loads(e.response.content)
            error_message = error["error"]["message"]
            error_code = error["error"]["code"]
            if error_code == "content_policy_violation":
                error_message = "Your prompt has been blocked by the OpenAI content filters. Try adjusting your prompt."
            return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, error_message=error_message)
        
        return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, error_message=error_message)

    return render_template('index.html')

images_per_page = 6 * 3 # (6 wide * 3 tall)


#################################
########    CHAT API    #########
#################################

@app.route('/get-all-conversations')
def get_all_conversations():
    if 'username' not in session:
        return None
    
    user_file = os.path.join(app.static_folder, 'chats', f'{session["username"]}.json')
    if os.path.exists(user_file):
        with open(user_file, 'r') as file:
            chat = json.load(file)
    else:
        with open(user_file, 'a') as file:
            chat = dict()
            file.write(json.dumps(chat))
    return json.dumps(chat)

@app.route('/chat', methods=['GET', 'POST'])
def converse():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Need to change how we fetch the thread_id depending on if POST or GET.
    thread_id = request.json.get('thread_id') if request.method == 'POST' else request.args.get('thread_id')
    user_file = os.path.join(app.static_folder, 'chats', f'{session["username"]}.json')

    # Load existing conversation or start a new one
    if os.path.exists(user_file):
        with open(user_file, 'r') as file:
            chat = json.load(file)
    else:
        with open(user_file, 'a') as file:
            chat = dict()
            file.write(json.dumps(chat))

    if request.method == 'POST':
        user_input = request.json.get('user_input')
        if not user_input:
            return {'error': 'No input provided'}, 400
        
        if thread_id and thread_id in chat:
            print("Have thread")
            thread = client.beta.threads.retrieve(thread_id)
        else:
            print("Need to create thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            chat_name = re.sub(r'[^\w_. -]', '_', request.json.get('chat_name'))
            chat[thread_id] = { "data": thread.__dict__, "chat_name": chat_name }

        # TODO: Allow listing assistants
        # Regular ChatGPT-like ID
        assistant_id = "asst_nYZeL982wB4AgoX4M7lfq7Qv"
        # CodeGPT
        #assistant_id = "asst_FX4sCfRsD6G3Vvc84ozABA8N"
        assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)
        
        thread_message = client.beta.threads.messages.create(thread_id, role="user", content=user_input)
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)

        run_retrieved = False
        while not run_retrieved:
            run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread_id)
            if run.status == "failed" or run.status == "completed" or run.status == "expired":
                run_retrieved = True
                print(f"Run retrieved! {run.status}")
                thread_id = run.thread_id
            if run.status == "requires_action":
                if run.required_action.type != "submit_tool_outputs":
                    raise Exception(f"Unsupported action type in requires_action: {run.required_action.type}.")
                process_tool_output(session["username"], run.id, run.thread_id, run.required_action.submit_tool_outputs.tool_calls)
                
        
        chat[thread_id]["last_update"] = time.time()
        chat[thread_id]["assistant_id"] = assistant_id
        with open(user_file, 'w') as file:
            json.dump(chat, file)

    # POST or GET return all thread messages
    message_list = client.beta.threads.messages.list(thread_id)
    all_messages = deque()
    for message in message_list.data:
        if message.content:
            for msg_content in message.content:
                all_messages.appendleft({
                    "role": message.role,
                    "text": msg_content.text.value,
                })
    return json.dumps({ "threadId": thread_id, "messages": list(all_messages)})

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
                raise Exception("'prompt' has not been passed to the generate_dalle_image argument!")
            try:
                generated_image_data = generate_dalle_image(arguments["prompt"], username, strict_follow_prompt=True)
                output_result["image_url"] = url_for('static', filename='images/' + username + '/' + generated_image_data.image_name)
                print(output_result["image_url"])
                output_result["revised_prompt"] = generated_image_data.revised_prompt
            except ModerationException as e:
                output_result["error_message"] = f"Your prompt doesn't pass OpenAI moderation. It triggers the following flags: {e.message}. Please adjust your prompt."
            except openai.BadRequestError as e:
                error = json.loads(e.response.content)
                error_message = error["error"]["message"]
                error_code = error["error"]["code"]
                if error_code == "content_policy_violation":
                    error_message = "Your prompt has been blocked by the OpenAI content filters. Try adjusting your prompt."
                output_result["error_message"] = error_message
        tool_output["output"] = json.dumps(output_result)
        tool_outputs.append(tool_output)
    run = client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id,
        thread_id=thread_id,
        tool_outputs=tool_outputs
    )


#################################
########   IMAGE GRID   #########
#################################

@app.route('/get-total-pages')
def get_total_pages():
    if 'username' not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted([os.path.join("images", file) for file in os.listdir(image_directory) if file.endswith('.png')])

    return str(-(-len(images) // images_per_page))

@app.route('/get-images/<int:page>')
def get_images(page):
    if 'username' not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted([os.path.join("static/images/", session["username"], file) for file in os.listdir(image_directory) if file.endswith('.jpg')], reverse=True)
    
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

@app.route('/get-image-metadata/<filename>')
def get_image_metadata(filename):
    if 'username' not in session:
        return None
    image_path = os.path.join(app.static_folder, "images", session["username"], filename)
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')