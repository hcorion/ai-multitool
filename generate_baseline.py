"""
One-time script to generate the baseline image for vibe comparison.
Uses the same prompt/settings as VibePreviewGenerator but without any vibe applied.
"""

import os
from novelai_client import NovelAIClient
from vibe_preview_generator import VibePreviewGenerator
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv(".env.local")

def main():
    api_key = os.environ.get("NOVELAI_API_KEY")
    if not api_key:
        print("Error: NOVELAI_API_KEY not set")
        return
    
    client = NovelAIClient(api_key)
    
    print("Generating baseline image...")
    print(f"Prompt: {VibePreviewGenerator.PREVIEW_PROMPT[:80]}...")
    print(f"Size: {VibePreviewGenerator.PREVIEW_WIDTH}x{VibePreviewGenerator.PREVIEW_HEIGHT}")
    print(f"Seed: {VibePreviewGenerator.PREVIEW_SEED}")
    
    # Generate without vibes
    image_bytes = client.generate_image(
        prompt=VibePreviewGenerator.PREVIEW_PROMPT,
        negative_prompt=VibePreviewGenerator.PREVIEW_PROMPT_NEGATIVE,
        width=VibePreviewGenerator.PREVIEW_WIDTH,
        height=VibePreviewGenerator.PREVIEW_HEIGHT,
        seed=VibePreviewGenerator.PREVIEW_SEED,
        # vibes=None is default - no vibe applied for baseline
    )
    
    # Save full image
    output_path = "static/vibes/baseline_preview.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'wb') as f:
        f.write(image_bytes)
    print(f"Saved: {output_path}")
    
    # Create thumbnail
    thumb_path = "static/vibes/baseline_preview.thumb.jpg"
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.thumbnail((256, 384), Image.Resampling.LANCZOS)
    image.save(thumb_path, 'JPEG', quality=85, optimize=True)
    print(f"Saved: {thumb_path}")
    
    print("Done!")

if __name__ == "__main__":
    main()
