#!/usr/bin/env python3

"""
Scaffold for an OpenAI Agents SDK-based transcript agent.
"""

# Import statements for future use
import os
import json
import asyncio
import re
import yaml
import base64
from typing import List, Dict, Any, Optional, Union
from agents import Agent, Runner, function_tool
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

@function_tool
def list_reference_files() -> List[Dict[str, str]]:
    """
    List all available reference files in the References directory with descriptions.
    Returns a list of dictionaries containing filename and description for each markdown file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    references_dir = os.path.join(base_dir, "References")
    if not os.path.exists(references_dir):
        return [{"filename": "error", "description": "References directory not found"}]
    result = []
    def extract_yaml_frontmatter(content: str) -> dict:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            try:
                return yaml.safe_load(frontmatter)
            except Exception:
                return {}
        return {}
    for filename in [f for f in os.listdir(references_dir) if f.endswith(".md")]:
        file_path = os.path.join(references_dir, filename)
        description = "No description available"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                meta = extract_yaml_frontmatter(content)
                if meta and isinstance(meta, dict) and 'description' in meta:
                    description = meta['description']
                else:
                    heading_match = re.search(r'^#+\s+(.+?)\n', content)
                    if heading_match:
                        description = heading_match.group(1).strip()
                    else:
                        first_para = re.split(r'\n\s*\n', content)[0].strip()
                        description = first_para[:150]
                        if len(first_para) > 150:
                            description += "..."
        except Exception as e:
            description = f"Error reading file: {str(e)}"
        result.append({"filename": filename, "description": description})
    return result

@function_tool
def retrieve_reference_files(filenames: List[str]) -> dict:
    """
    Retrieve the contents of one or more reference files.
    
    Args:
        filenames: A list of filenames to retrieve from the References directory.
                   Do not include paths, just the filename with extension.
    
    Returns:
        A dictionary mapping filenames to their contents.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    references_dir = os.path.join(base_dir, "References")
    
    if not os.path.exists(references_dir):
        return {"error": "References directory not found"}
    
    result = {}
    for filename in filenames:
        file_path = os.path.join(references_dir, filename)
        if os.path.exists(file_path) and filename.endswith(".md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    result[filename] = f.read()
            except Exception as e:
                result[filename] = f"Error reading file: {str(e)}"
        else:
            result[filename] = f"File not found: {filename}"
    
    return result

@function_tool
def list_memory_categories() -> List[Dict[str, str]]:
    """
    List all available memory categories with their descriptions.
    Returns a list of dictionaries containing category name and description for each memory file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    memory_dir = os.path.join(base_dir, "Memory")
    
    if not os.path.exists(memory_dir):
        return [{"category": "error", "description": "Memory directory not found"}]
    
    result = []
    for filename in [f for f in os.listdir(memory_dir) if f.endswith(".md")]:
        file_path = os.path.join(memory_dir, filename)
        category = os.path.splitext(filename)[0]  # Remove .md extension
        description = "No description available"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Extract frontmatter
                match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if match:
                    frontmatter = match.group(1)
                    try:
                        meta = yaml.safe_load(frontmatter)
                        if meta and isinstance(meta, dict):
                            if 'description' in meta:
                                description = meta['description']
                            elif 'title' in meta:
                                description = f"Memory category for {meta['title']}"
                    except Exception:
                        pass
        except Exception as e:
            description = f"Error reading file: {str(e)}"
            
        result.append({"category": category, "description": description})
    
    return result


@function_tool
def retrieve_memory_categories(categories: List[str]) -> Dict[str, str]:
    """
    Retrieve the contents of one or more memory categories.
    
    Args:
        categories: A list of category names to retrieve from the Memory directory.
                   Do not include paths or extensions, just the base name (e.g., 'characters', 'locations').
    
    Returns:
        A dictionary mapping category names to their contents (excluding frontmatter).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    memory_dir = os.path.join(base_dir, "Memory")
    
    if not os.path.exists(memory_dir):
        return {"error": "Memory directory not found"}
    
    result = {}
    for category in categories:
        filename = f"{category}.md"
        file_path = os.path.join(memory_dir, filename)
        
        if os.path.exists(file_path) and filename.endswith(".md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Remove frontmatter
                    content_without_frontmatter = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
                    result[category] = content_without_frontmatter.strip()
            except Exception as e:
                result[category] = f"Error reading file: {str(e)}"
        else:
            result[category] = f"Memory category not found: {category}"
    
    return result


@function_tool
def update_memory_categories(updates: Dict[str, str]) -> Dict[str, str]:
    """
    Update the contents of one or more memory categories.
    
    Args:
        updates: A dictionary mapping category names to their new contents.
                The keys should be category names without extensions (e.g., 'characters', 'locations').
                The values should be the new content for each category (excluding frontmatter).
    
    Returns:
        A dictionary with status messages for each updated category.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    memory_dir = os.path.join(base_dir, "Memory")
    
    if not os.path.exists(memory_dir):
        return {"error": "Memory directory not found"}
    
    result = {}
    for category, new_content in updates.items():
        filename = f"{category}.md"
        file_path = os.path.join(memory_dir, filename)
        
        if os.path.exists(file_path) and filename.endswith(".md"):
            try:
                # Read existing file to preserve frontmatter
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                
                # Extract frontmatter
                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', existing_content, re.DOTALL)
                if frontmatter_match:
                    frontmatter = f"---\n{frontmatter_match.group(1)}\n---\n\n"
                    # Combine frontmatter with new content
                    updated_content = frontmatter + new_content
                    
                    # Write updated content back to file
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(updated_content)
                    
                    result[category] = "Successfully updated"
                else:
                    result[category] = "Error: Could not find frontmatter in existing file"
            except Exception as e:
                result[category] = f"Error updating file: {str(e)}"
        else:
            result[category] = f"Memory category not found: {category}"
    
    return result


def get_previous_summaries(prompt_base: str, transcript_date: str, max_previous: int = 2) -> List[dict]:
    """
    Retrieve previous summaries for a given prompt type up to the specified transcript date.
    
    Args:
        prompt_base: The base name of the prompt (without extension)
        transcript_date: The current transcript date being processed
        max_previous: Maximum number of previous summaries to retrieve
        
    Returns:
        A list of dictionaries containing previous summary information, ordered from oldest to newest
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summaries_dir = os.path.join(base_dir, "Summaries")
    
    # Get all summary files for this prompt type
    all_summaries = [f for f in os.listdir(summaries_dir) 
                    if f.startswith(f"{prompt_base}-") and f.endswith(".md")]
    
    # Extract dates and filter to only include summaries before the current date
    dated_summaries = []
    for summary in all_summaries:
        # Extract date from filename (format: prompt_base-date.md)
        try:
            summary_date = summary[len(prompt_base)+1:-3]  # Remove prompt_base- prefix and .md suffix
            if summary_date < transcript_date:  # Only include earlier dates
                dated_summaries.append((summary_date, summary))
        except Exception:
            continue
    
    # Sort by date (oldest first)
    dated_summaries.sort()
    
    # Get the most recent summaries up to max_previous
    recent_summaries = dated_summaries[-max_previous:] if dated_summaries else []
    
    # Load the content of each summary
    result = []
    for date, filename in recent_summaries:
        summary_path = os.path.join(summaries_dir, filename)
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()
                result.append({
                    "date": date,
                    "filename": filename,
                    "content": content
                })
        except Exception as e:
            print(f"Error reading previous summary {filename}: {str(e)}")
    
    return result

# ---
# After all summaries, generate missing images from image*.md files in Summaries
# ---
def generate_missing_images_for_summaries():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summaries_dir = os.path.join(base_dir, "Summaries")
    images_dir = os.path.join(base_dir, "Images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    image_md_files = [f for f in os.listdir(summaries_dir) if f.startswith("image") and f.endswith(".md")]
    if not image_md_files:
        print("No image*.md files found in Summaries.")
        return
    if OpenAI is None:
        print("OpenAI SDK not installed. Cannot generate images.")
        return
    
    # Get organization ID from environment variable
    org_id = os.getenv("OPENAI_ORG_ID")
    if not org_id:
        print("OPENAI_ORG_ID environment variable not set.")
        return
        
    client = OpenAI(organization=org_id)
    for md_file in image_md_files:
        md_path = os.path.join(summaries_dir, md_file)
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Split prompts by ---
        prompts = [p.strip() for p in content.split("---") if p.strip()]
        for idx, prompt in enumerate(prompts, 1):
            # Generate two versions (a and b) for each prompt
            for version in ['a']:
                image_filename = f"{os.path.splitext(md_file)[0]}-{idx}{version}.png"
                image_path = os.path.join(images_dir, image_filename)
                if os.path.exists(image_path):
                    continue  # Image already exists
                print(f"Generating image {version} for {md_file} prompt {idx}...")
                try:
                    result = client.images.generate(
                        model="gpt-image-1",
                        prompt=prompt
                    )
                    image_base64 = result.data[0].b64_json
                    image_bytes = base64.b64decode(image_base64)
                    with open(image_path, "wb") as imgf:
                        imgf.write(image_bytes)
                    print(f"Saved image: {image_path}")
                except Exception as e:
                    print(f"Failed to generate image {version} for {md_file} prompt {idx}: {e}")


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    transcripts_dir = os.path.join(base_dir, "Transcripts")
    prompts_dir = os.path.join(base_dir, "Prompts")
    summaries_dir = os.path.join(base_dir, "Summaries")

    # Ensure Summaries directory exists
    os.makedirs(summaries_dir, exist_ok=True)

    # Get all transcript files
    transcript_files = [f for f in os.listdir(transcripts_dir) if f.endswith(".md")]
    if not transcript_files:
        print("No transcript files found.")
        return
    
    # Sort transcripts by name (typically date-based)
    transcript_files.sort()
    
    # Get all prompt files
    prompt_files = [f for f in os.listdir(prompts_dir) if f.endswith(".md")]
    if not prompt_files:
        print("No prompt files found.")
        return
        
    # Process each transcript
    for transcript_file in transcript_files:
        transcript_date = os.path.splitext(transcript_file)[0]
        transcript_path = os.path.join(transcripts_dir, transcript_file)
        
        print(f"Processing transcript: {transcript_file}")
        
        # Read transcript content
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_content = f.read()
            
        # Sort prompt files to ensure session-summary.md is processed last
        sorted_prompt_files = sorted(prompt_files, key=lambda x: x == "session-summary.md")
        
        # Process each prompt for this transcript
        for prompt_file in sorted_prompt_files:
            # Generate the expected output filename
            prompt_base = os.path.splitext(prompt_file)[0]
            summary_filename = f"{prompt_base}-{transcript_date}.md"
            summary_path = os.path.join(summaries_dir, summary_filename)
            
            # Skip if output file already exists
            if os.path.exists(summary_path):
                print(f"Skipping {summary_filename} - already exists")
                continue
                
            print(f"Processing {transcript_file} with {prompt_file}...")
            
            # Read prompt content
            prompt_path = os.path.join(prompts_dir, prompt_file)
            with open(prompt_path, "r", encoding="utf-8") as pf:
                prompt_content = pf.read()
                
            # Get previous summaries for context
            previous_summaries = get_previous_summaries(prompt_base, transcript_date)
            previous_context = ""
            if previous_summaries:
                previous_context = "\n\n## Previous Summaries (for context)\n\n"
                for idx, summary in enumerate(previous_summaries):
                    previous_context += f"### Summary from {summary['date']}\n\n{summary['content']}\n\n"
                previous_context += "## End of Previous Summaries\n\n"

            # Determine which tools to include based on the prompt file
            tools = [list_reference_files, retrieve_reference_files, list_memory_categories, retrieve_memory_categories]
            
            # Only include update_memory_categories for session-summary.md
            if prompt_file == "session-summary.md":
                tools.append(update_memory_categories)
            
            agent = Agent(
                name=f"{prompt_file}",
                instructions=prompt_content,
                model="gpt-4.1",
                tools=tools
            )

            async def run_agent():
                # Create a prompt that includes previous summaries as context
                # Base prompt for all summaries
                user_input = (
                    "Please use the provided tools to access reference materials and memory categories before processing this transcript. "
                    "First list all available reference files and memory categories, then retrieve and review relevant ones to ensure accurate "
                    "information in your output. After you've reviewed the references and memories, create a clean final output "
                    "without mentioning your tool usage steps."
                )
                
                # Add special instructions for session-summary.md
                if prompt_file == "session-summary.md":
                    user_input = (
                        "Please use the provided tools to access reference materials and memory categories before processing this transcript. "
                        "First list all available reference files and memory categories, then retrieve and review relevant ones to ensure accurate "
                        "information in your output. After creating your summary, you MUST use the update_memory_categories tool to update the memory "
                        "files with new information discovered in this transcript. Specifically: "
                        "1) Use retrieve_memory_categories to first get the current content of each memory category "
                        "2) Then use update_memory_categories to update each relevant category with new information while preserving existing content "
                        "3) Update characters.md with new characters or character development "
                        "4) Update locations.md with new locations or location details "
                        "5) Update plot_elements.md with quest progress and story developments "
                        "6) Update player_decisions.md with significant choices and their consequences "
                        "7) Update world_state.md with changes to the political or environmental situation "
                        "8) Update items_resources.md with new items or resources acquired "
                        "9) Update knowledge_lore.md with new lore or discovered secrets "
                        "Ensure your final output does not mention your tool usage steps."
                    )
                
                # Add previous summaries context if available
                if previous_context:
                    user_input += (
                    "\n\nFor continuity, I'm providing previous summaries you've generated for earlier sessions. "
                    "Use these to inform your understanding of the ongoing storyline and reference previous events "
                    "when appropriate. For narratives, continue story elements naturally; for summaries or podcasts, "
                    "refer back to previous sessions when relevant:\n" + previous_context
                    )
                
                # Add the transcript content
                user_input += f"\nHere's the transcript to process:\n\n{transcript_content}"
                
                result = await Runner.run(agent, user_input)
                
                # Extract just the final summary, removing tool usage steps
                output = result.final_output
                
                # Check if the output contains tool usage steps and filter them out
                if "## Step 1:" in output and "## Next Steps" in output:
                    # Find where the actual summary starts (after the tool usage sections)
                    lines = output.split('\n')
                    start_idx = None
                    
                    # Look for patterns that indicate the end of tool usage steps
                    for i, line in enumerate(lines):
                        if "## Next Steps" in line and i < len(lines) - 2:
                            # Skip the "Next Steps" section and start from the actual summary
                            start_idx = i + 3
                            break
                    
                    if start_idx is not None and start_idx < len(lines):
                        # Return only the actual summary part
                        return '\n'.join(lines[start_idx:])
                
                # If we couldn't identify the tool usage sections, return the full output
                return output

            summary = asyncio.run(run_agent())
            with open(summary_path, "w", encoding="utf-8") as sf:
                sf.write(summary)
            print(f"Wrote summary to {summary_path}")
    
    # After all summaries are processed, generate any missing images
    generate_missing_images_for_summaries()


if __name__ == "__main__":
    main()
