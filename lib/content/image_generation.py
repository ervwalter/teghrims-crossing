#!/usr/bin/env python3
"""
Image generation module for processing image prompt files.
Generates images from markdown files with title/prompt format and saves metadata.
"""

import os
import json
import base64
import re
from typing import List, Dict, Optional
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..config import SUMMARIES_DIR, IMAGES_DIR


def parse_image_prompts(content: str) -> List[Dict[str, str]]:
    """
    Parse image prompt markdown content into title/prompt pairs.
    
    Args:
        content: Raw markdown content with Title/Prompt sections separated by ---
        
    Returns:
        List of dictionaries with 'title' and 'prompt' keys
    """
    prompts = []
    sections = [section.strip() for section in content.split("---") if section.strip()]
    
    for section in sections:
        lines = section.strip().split('\n')
        title = ""
        prompt = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("Title:"):
                title = line[6:].strip()
            elif line.startswith("Prompt:"):
                prompt = line[7:].strip()
        
        if title and prompt:
            prompts.append({"title": title, "prompt": prompt})
    
    return prompts


def generate_image_from_prompt(client: OpenAI, prompt: str) -> Optional[bytes]:
    """
    Generate an image using OpenAI's image generation API.
    
    Args:
        client: OpenAI client instance
        prompt: Text prompt for image generation
        
    Returns:
        Image bytes if successful, None if failed
    """
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt
        )
        
        image_base64 = result.data[0].b64_json
        return base64.b64decode(image_base64)
        
    except Exception as e:
        print(f"Error generating image: {e}")
        return None


def process_image_file(openai_api_key: str, md_file_path: str, images_dir: str) -> None:
    """
    Process a single image markdown file to generate images with metadata.
    
    Args:
        openai_api_key: OpenAI API key
        md_file_path: Path to the markdown file
        images_dir: Directory to save images
    """
    if OpenAI is None:
        print("OpenAI SDK not installed. Cannot generate images.")
        return
    
    # Get organization ID from environment variable (like the old code)
    org_id = os.getenv("OPENAI_ORG_ID")
    if not org_id:
        print("OPENAI_ORG_ID environment variable not set.")
        return
        
    client = OpenAI(api_key=openai_api_key, organization=org_id)
    
    # Read the markdown file
    try:
        with open(md_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {md_file_path}: {e}")
        return
    
    # Parse prompts
    prompts = parse_image_prompts(content)
    if not prompts:
        print(f"No valid prompts found in {md_file_path}")
        return
    
    # Extract base filename (remove extension)
    base_filename = os.path.splitext(os.path.basename(md_file_path))[0]
    
    # Process each prompt
    for idx, prompt_data in enumerate(prompts, 1):
        title = prompt_data["title"]
        prompt = prompt_data["prompt"]
        
        # Generate filename: base-{index}a.png (following old pattern)
        image_filename = f"{base_filename}-{idx}a.png"
        image_path = os.path.join(images_dir, image_filename)
        
        # Generate metadata filename
        metadata_filename = f"{base_filename}-{idx}a.json"
        metadata_path = os.path.join(images_dir, metadata_filename)
        
        # Skip if image already exists
        if os.path.exists(image_path):
            print(f"Image already exists: {image_filename}")
            continue
        
        print(f"Generating image {idx} for {base_filename}: {title}")
        
        # Generate the image
        image_bytes = generate_image_from_prompt(client, prompt)
        
        if image_bytes:
            # Save the image
            try:
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                print(f"Saved image: {image_path}")
                
                # Save metadata
                metadata = {
                    "title": title,
                    "prompt": prompt,
                    "filename": image_filename,
                    "source_file": os.path.basename(md_file_path)
                }
                
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                print(f"Saved metadata: {metadata_path}")
                
            except Exception as e:
                print(f"Error saving image or metadata: {e}")
        else:
            print(f"Failed to generate image {idx} for {base_filename}")


def process_all_images(openai_api_key: str) -> None:
    """
    Process all image prompt files in the output/summaries directory.
    
    Args:
        openai_api_key: OpenAI API key
    """
    summaries_dir = SUMMARIES_DIR
    images_dir = IMAGES_DIR
    
    # Ensure images directory exists
    os.makedirs(images_dir, exist_ok=True)
    
    # Find all image-*.md files
    if not os.path.exists(summaries_dir):
        print(f"Summaries directory not found: {summaries_dir}")
        return
    
    image_files = [f for f in os.listdir(summaries_dir) 
                  if f.startswith("image-") and f.endswith(".md")]
    
    if not image_files:
        print("No image prompt files found in summaries directory.")
        return
    
    print(f"Found {len(image_files)} image prompt files to process")
    
    for image_file in sorted(image_files):
        md_file_path = os.path.join(summaries_dir, image_file)
        print(f"\nProcessing: {image_file}")
        process_image_file(openai_api_key, md_file_path, images_dir)
    
    print("\nImage generation complete!")


if __name__ == "__main__":
    # For testing
    import sys
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    process_all_images(api_key)