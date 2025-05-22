#!/usr/bin/env python
"""
Functions for processing session digests with various prompts using the OpenAI Agent SDK.
"""

import os
import glob
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import asyncio

from agents import Agent, Runner
from .reference_utils import list_reference_files, retrieve_reference_files
from .memory_tools import list_articles, get_articles
from .notion_tools import get_all_entities
from .context import SessionContext


def get_session_digests() -> List[Dict]:
    """
    Get all available session digests.
    
    Returns:
        List of dictionaries containing session date and path to the digest file
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    digests_dir = os.path.join(base_dir, "transcripts", "digests")
    
    if not os.path.exists(digests_dir):
        print(f"No digests directory found at {digests_dir}")
        return []
    
    # Get all digest files
    digest_files = glob.glob(os.path.join(digests_dir, "*.md"))
    
    session_digests = []
    for digest_path in digest_files:
        # Extract session date from filename
        filename = os.path.basename(digest_path)
        session_date = filename.split('.')[0]  # Remove file extension
        
        # Validate session date format (YYYY-MM-DD)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', session_date):
            session_digests.append({
                "date": session_date,
                "path": digest_path
            })
        else:
            print(f"Warning: Skipping file with invalid date format: {filename}")
    
    # Sort by date
    session_digests.sort(key=lambda x: x["date"])
    
    return session_digests


def get_prompt_content(prompt_name: str) -> Optional[str]:
    """
    Get the content of a prompt file.
    
    Args:
        prompt_name: Name of the prompt file without extension
        
    Returns:
        str: Content of the prompt file, or None if not found
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", f"{prompt_name}.md")
    
    if not os.path.exists(prompt_path):
        print(f"Error: Prompt file not found: {prompt_path}")
        return None
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading prompt file {prompt_path}: {str(e)}")
        return None


def get_digest_content(digest_path: str) -> Optional[str]:
    """
    Get the content of a digest file.
    
    Args:
        digest_path: Path to the digest file
        
    Returns:
        str: Content of the digest file, or None if there was an error
    """
    try:
        with open(digest_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading digest file {digest_path}: {str(e)}")
        return None


def get_previous_output(session_date: str, prompt_name: str) -> Optional[Tuple[str, str]]:
    """
    Get the most recent previous output for a specific prompt.
    
    Args:
        session_date: Date of the current session (YYYY-MM-DD)
        prompt_name: Name of the prompt file without extension
        
    Returns:
        Tuple[str, str]: Tuple containing the date and content of the previous output,
                         or (None, None) if not found
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "output", "summaries")
    
    if not os.path.exists(output_dir):
        return None, None
    
    # Pattern for this prompt type's output files
    prompt_pattern = f"{prompt_name}.*.md"
    
    # Get all output files for this prompt
    output_files = glob.glob(os.path.join(output_dir, prompt_pattern))
    
    # Filter to files with valid date format
    dated_files = []
    for file_path in output_files:
        filename = os.path.basename(file_path)
        # Extract date from filename (prompt.YYYY-MM-DD.md)
        match = re.search(r'(\d{4}-\d{2}-\d{2})\.md$', filename)
        if match:
            file_date = match.group(1)
            # Only consider files with dates before the current session
            if file_date < session_date:
                dated_files.append((file_date, file_path))
    
    if not dated_files:
        return None, None
    
    # Sort by date and get the most recent
    dated_files.sort(key=lambda x: x[0], reverse=True)
    prev_date, prev_file = dated_files[0]
    
    # Read the content
    try:
        with open(prev_file, "r", encoding="utf-8") as f:
            prev_content = f.read()
        return prev_date, prev_content
    except Exception as e:
        print(f"Error reading previous output file {prev_file}: {str(e)}")
        return prev_date, None


def output_exists(session_date: str, prompt_name: str) -> bool:
    """
    Check if an output file already exists for a session and prompt.
    
    Args:
        session_date: Date of the session (YYYY-MM-DD)
        prompt_name: Name of the prompt file without extension
        
    Returns:
        bool: True if the output file exists, False otherwise
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "output", "summaries")
    output_file = os.path.join(output_dir, f"{prompt_name}.{session_date}.md")
    
    return os.path.exists(output_file)


def save_output(content: str, session_date: str, prompt_name: str) -> Optional[str]:
    """
    Save generated content to the summaries output directory.
    
    Args:
        content: Generated content to save
        session_date: Date of the session (YYYY-MM-DD)
        prompt_name: Name of the prompt file without extension
        
    Returns:
        str: Path to the saved file, or None if there was an error
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "output", "summaries")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{prompt_name}.{session_date}.md")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        return output_file
    except Exception as e:
        print(f"Error saving output to {output_file}: {str(e)}")
        return None


async def process_digest_with_prompt(digest_content: str, session_date: str, prompt_name: str, 
                                    prompt_content: str, openai_api_key: str, 
                                    previous_output: Optional[Tuple[str, str]] = None) -> Optional[str]:
    """
    Process a digest with a specific prompt using the agent SDK.
    
    Args:
        digest_content: Content of the digest
        session_date: Date of the session (YYYY-MM-DD)
        prompt_name: Name of the prompt file without extension
        openai_api_key: OpenAI API key
        previous_output: Tuple containing the date and content of previous output (optional)
        
    Returns:
        str: Generated content from the agent, or None if there was an error
    """
    # Prompt content is now passed as a parameter
    if not prompt_content:
        print(f"Error: Empty prompt content for {prompt_name}")
        return None
    
    # Define tools for the agent
    tools = [
        list_reference_files,
        retrieve_reference_files,
        list_articles,
        get_articles,
        get_all_entities
    ]
    
    # Create session context
    session_context = SessionContext(session_date=session_date)
    
    # Create the agent
    agent = Agent[SessionContext](
        name=f"{prompt_name.capitalize()}Agent",
        instructions="You are a skilled tabletop RPG content creator. You have tools to access campaign reference materials and memory articles. You can also use get_all_entities to see all known entities in the campaign world, which will help you normalize entity names. Use these tools wisely to ensure continuity and accuracy.",
        model="gpt-4.1",
        tools=tools
    )
    
    # Prepare the user prompt
    user_prompt = f"""IMPORTANT: You are processing a session from {session_date}.

BEGIN BY:
1. Using list_articles to see all available campaign-memory articles
2. Using get_articles with a list of slugs to read the current state of multiple articles at once
3. Using list_reference_files to see all available reference documents
4. Using retrieve_reference_files tool to read the player-roster.md and any other relevant references
5. Using get_all_entities to see all known entities in the campaign world to help normalize entity names

After gathering this information, FOLLOW THESE SPECIFIC INSTRUCTIONS EXACTLY:

{prompt_content}

"""
    
    # Add previous output context if available
    if previous_output and previous_output[0] and previous_output[1]:
        prev_date, prev_content = previous_output
        user_prompt += f"\n\nFor continuity, here is the output from the previous session ({prev_date}):\n\n{prev_content}\n\n"
    
    # Add the digest content
    user_prompt += f"\n\nHere's the session digest to process:\n\n{digest_content}"
    
    try:
        # Run the agent with session context
        result = await Runner.run(agent, user_prompt, context=session_context)
        return result.final_output
    except Exception as e:
        print(f"Error running agent for {prompt_name} on session {session_date}: {str(e)}")
        return None


def get_available_prompts() -> List[Dict[str, str]]:
    """
    Get all available prompts from the prompts directory.
    
    Returns:
        List of dictionaries containing prompt name and path
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_dir = os.path.join(base_dir, "prompts")
    
    if not os.path.exists(prompts_dir):
        print(f"Error: Prompts directory not found at {prompts_dir}")
        return []
    
    # Get all prompt files
    prompt_files = glob.glob(os.path.join(prompts_dir, "*.md"))
    
    prompts = []
    for prompt_path in prompt_files:
        # Extract prompt name from filename (without extension)
        filename = os.path.basename(prompt_path)
        prompt_name = os.path.splitext(filename)[0]
        
        prompts.append({
            "name": prompt_name,
            "path": prompt_path
        })
    
    return prompts


def process_digest(digest_path: str, session_date: str, openai_api_key: str) -> Dict[str, Optional[str]]:
    """
    Process a digest with all available prompts.
    
    Args:
        digest_path: Path to the digest file
        session_date: Date of the session (YYYY-MM-DD)
        openai_api_key: OpenAI API key
        
    Returns:
        Dictionary mapping prompt names to their saved file paths (or None if error)
    """
    # Get the digest content
    digest_content = get_digest_content(digest_path)
    if not digest_content:
        return {}
    
    # Get all available prompts
    prompts = get_available_prompts()
    if not prompts:
        print("No prompts found.")
        return {}
    
    results = {}
    
    # Process each prompt
    for prompt_info in prompts:
        prompt_name = prompt_info["name"]
        prompt_path = prompt_info["path"]
        
        # Skip if output already exists
        if output_exists(session_date, prompt_name):
            print(f"Output for prompt '{prompt_name}' already exists for session {session_date}, skipping")
            continue
        
        # Get the prompt content
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_content = f.read()
        except Exception as e:
            print(f"Error reading prompt file {prompt_path}: {str(e)}")
            continue
        
        # Get previous output if available
        previous_output = get_previous_output(session_date, prompt_name)
        
        # Process the digest with this prompt
        print(f"Processing {session_date} digest with '{prompt_name}' prompt...")
        output = asyncio.run(process_digest_with_prompt(
            digest_content, 
            session_date, 
            prompt_name,
            prompt_content,
            openai_api_key, 
            previous_output
        ))
        
        if output:
            # Save the output
            output_path = save_output(output, session_date, prompt_name)
            results[prompt_name] = output_path
        else:
            results[prompt_name] = None
    
    return results


def process_all_digests(openai_api_key: str) -> None:
    """
    Process all available session digests with all prompts.
    
    Args:
        openai_api_key: OpenAI API key
    """
    # Get all session digests
    session_digests = get_session_digests()
    
    if not session_digests:
        print("No session digests found.")
        return
    
    print(f"Found {len(session_digests)} session digests to process.\n")
    
    # Process each digest
    for session_info in session_digests:
        session_date = session_info["date"]
        digest_path = session_info["path"]
        
        print(f"Processing session {session_date}...")
        
        try:
            results = process_digest(digest_path, session_date, openai_api_key)
            if results:
                print(f"Processing complete for session {session_date}:")
                for output_type, output_path in results.items():
                    if output_path:
                        print(f"  - {output_type}: {output_path}")
                    else:
                        print(f"  - {output_type}: Failed")
            else:
                print(f"No outputs were generated for session {session_date}")
            
            print()
        except Exception as e:
            print(f"Error processing session {session_date}: {str(e)}\n")
            continue
