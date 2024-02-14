from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from pygments.formatters import HtmlFormatter
import markdown
import markdown.extensions.fenced_code
import openai
import requests
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
            print("No prompt providing, not doing anything.")
            return render_template('index.html')
        try:
            before_prompt = prompt
            if strict_follow_prompt:
                prompt = "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:\n" + prompt
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
                image_path = os.path.join(app.static_folder, "images", session["username"])
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

                return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, errmr_message=error_message)
            else:
                local_image_path = "Error downloading image"
                print(local_image_path)

        except openai.BadRequestError as e:
            error = json.loads(e.response.content)
            error_message = error["error"]["message"]
            error_code = error["error"]["code"]
            if error_code == "content_policy_violation":
                error_message = "Your prompt has been blocked by the OpenAI content filters. Try adjusting your prompt."
            return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, error_message=error_message)
        
        return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name, errmr_message=error_message)

    return render_template('index.html')

images_per_page = 6 * 3 # (6 wide * 3 tall)


#################################
########    CHAT API    #########
#################################

@app.route('/chat', methods=['GET', 'POST'])
def converse():
    if 'username' not in session:
        return redirect(url_for('login'))

    thread_id = request.json.get('thread_id')
    chat_name = re.sub(r'[^\w_. -]', '_', request.json.get('chat_name'))
    user_file = os.path.join(app.static_folder, 'chats', f'{session["username"]}.json')

    if request.method == 'POST':
        user_input = request.json.get('user_input')
        if not user_input:
            return {'error': 'No input provided'}, 400
        
        # Load existing conversation or start a new one
        if os.path.exists(user_file):
            with open(user_file, 'r') as file:
                chat = json.load(file)
        else:
            with open(user_file, 'a') as file:
                chat = {"threads": []}
                file.write(json.dumps(chat))

        # TODO: Allow listing assistants
        assistant = client.beta.assistants.retrieve("asst_nYZeL982wB4AgoX4M7lfq7Qv")
        if thread_id and chat.threads[thread_id]:
            print("Have thread")
            thread = client.beta.threads.retrieve(thread_id)
        else:
            print("Need to create thread")
            thread = client.beta.threads.create()
            thread_id = thread.id
            chat[thread_id] = { "data": thread.__dict__, "chat_name": chat_name }
        thread_message = client.beta.threads.messages.create(thread_id, role="user", content=user_input)
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)

        run_retrieved = False
        while not run_retrieved:
            run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread_id)
            if run.status == "failed" or run.status == "completed" or run.status == "expired":
                run_retrieved = True
                print(f"Run retrieved! {run.status}")
        
        chat[thread_id]["last_update"] = time.time()
        with open(user_file, 'w') as file:
            json.dump(chat, file)
        
        message_list = client.beta.threads.messages.list(run.thread_id)
        all_messages = { "data": [] }
        for message in message_list.data:
            if message.content:
                for msg_content in message.content:
                    all_messages["data"].append({
                        "role": message.role,
                        "text": markdown.markdown(msg_content.text.value, extensions=["fenced_code", "codehilite"])
                    })
        return json.dumps(all_messages)
    else:
        # GET request to retrieve conversation history
        if os.path.exists(user_file):
            with open(user_file, 'r') as file:
                chat = json.load(file)
            return jsonify(chat)
        else:
            return jsonify([])

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