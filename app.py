from flask import Flask, render_template, request, session, redirect, url_for
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import pngquant
import openai
import requests
import os, io, secrets
import json
import re

app = Flask(__name__)

# Initialize the OpenAI client
client = openai.OpenAI()

# Configure the quality settings
pngquant.config(min_quality=65, max_quality=80)

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
                      "photo", "artwork", "painting", "impressionist", "promotional", "full", "shot"])

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
                    if os.path.isfile(os.path.join(image_path, path)):
                        file_count += 1
                cleaned_prompt = before_prompt.strip().lower()
                cleaned_prompt = remove_stop_words(cleaned_prompt).replace('  ', ' ').replace(' ', '_').replace('.', '')[:30]
                image_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.png"
                image_filename = os.path.join(image_path, image_name)

                with open(image_filename, 'wb') as f:
                    f.write(image_response.content)
                
                # Compress the image
                pngquant.quant_image(image=image_filename, override=True)
                # Create metadata

                image = Image.open(image_filename)

                metadata = PngInfo()
                metadata.add_text("Prompt", prompt)
                metadata.add_text("Quality", quality)
                metadata.add_text("Style", style)
                metadata.add_text("Revised Prompt", revised_prompt)

                # Save the image with metadata directly to disk
                image.save(image_filename, "PNG", pnginfo=metadata)

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

@app.route('/get-total-pages')
def get_total_pages():
    if 'username' not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted([os.path.join("images", file) for file in os.listdir(image_directory) if file.endswith('.png')])
    print(len(images))

    return str(len(images) // (images_per_page - 1))

@app.route('/get-images/<int:page>')
def get_images(page):
    if 'username' not in session:
        return None
    image_directory = os.path.join(app.static_folder, "images", session["username"])
    images = sorted([os.path.join("static/images/", session["username"], file) for file in os.listdir(image_directory) if file.endswith('.png')], reverse=True)

    start = (page) * images_per_page
    end = start + images_per_page
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