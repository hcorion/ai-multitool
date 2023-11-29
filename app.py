from flask import Flask, render_template, request
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import openai
import requests
import os, io
import json

app = Flask(__name__)

# Initialize the OpenAI client
client = openai.OpenAI()

@app.route('/', methods=['GET', 'POST'])
def index():
    image_url = None
    local_image_path = None

    if request.method == 'POST':
        size = request.form.get('size')
        quality = request.form.get('quality')
        style = request.form.get('style')
        prompt = request.form.get('prompt')
        print(f"Size: {size}, Quality: {quality}, Style: {style}, Prompt: {prompt}")

        try:
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
                image_path = os.path.join(app.static_folder, "images")
                file_count = 0
                for path in os.listdir(image_path):
                    if os.path.isfile(os.path.join(image_path, path)):
                        file_count += 1

                cleaned_prompt = prompt.strip().replace(' ', '_').replace('.', '')[:30]
                image_name = f"{str(file_count).zfill(10)}-{cleaned_prompt}.png"
                image_filename = os.path.join(image_path, image_name)

                # Create an in-memory image from the downloaded content
                image = Image.open(io.BytesIO(image_response.content))
                
                # Create metadata
                metadata = PngInfo()
                metadata.add_text("Prompt", prompt)
                metadata.add_text("Quality", quality)
                metadata.add_text("Style", style)
                metadata.add_text("Revised Prompt", revised_prompt)

                # Save the image with metadata directly to disk
                with open(image_filename, 'wb') as f:
                    image.save(f, "PNG", pnginfo=metadata)

                local_image_path = image_filename
            else:
                local_image_path = "Error downloading image"
                print(local_image_path)

        except Exception as e:
            local_image_path = f"Error: {e}"
            print(local_image_path)

        return render_template('result-section.html', image_url=image_url, local_image_path=local_image_path, revised_prompt=revised_prompt, prompt=prompt, image_name=image_name)

    return render_template('index.html')

images_per_page = 6 * 3 # (6 wide * 3 tall)

@app.route('/get-total-pages')
def get_total_pages():
    image_directory = os.path.join(app.static_folder, "images")
    images = sorted([os.path.join("images", file) for file in os.listdir(image_directory) if file.endswith('.png')])
    print(len(images))

    return str(len(images) // (images_per_page - 1))

@app.route('/get-images/<int:page>')
def get_images(page):
    image_directory = os.path.join(app.static_folder, "images")
    images = sorted([os.path.join("static/images/", file) for file in os.listdir(image_directory) if file.endswith('.png')], reverse=True)

    start = (page) * images_per_page
    end = start + images_per_page
    paginated_images = images[start:end]

    return json.dumps(paginated_images)

@app.route('/get-image-metadata/<filename>')
def get_image_metadata(filename):
    image_path = os.path.join(app.static_folder, "images", filename)
    image = Image.open(image_path)

    # Extract metadata
    metadata = image.info.get("pnginfo", None)
    if metadata:
        metadata_dict = {key: metadata[key] for key in metadata}
    else:
        metadata_dict = {"error": "No metadata found"}

    return json.dumps(metadata_dict)

if __name__ == '__main__':
    app.run(debug=True)
