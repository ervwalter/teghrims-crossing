#!/usr/bin/env python
"""
Functions for combining transcript slices using OpenAI's Agent SDK to create a session digest.
"""

import os
import glob
import re
from typing import List, Dict, Optional
from pathlib import Path
import asyncio
from datetime import date

from agents import Agent, Runner
from .reference_utils import get_player_roster, list_reference_files, retrieve_reference_files
from .memory_tools import list_articles, get_articles, update_article, list_articles_meta, latest_revision_for_date

def get_slice_content(slice_path: str) -> str:
    """
    Read the content of a slice file.
    
    Args:
        slice_path: Path to the slice file
        
    Returns:
        str: Content of the slice file
    """
    try:
        with open(slice_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading slice file {slice_path}: {str(e)}")
        return f"ERROR: Could not read slice file {os.path.basename(slice_path)}"


def get_session_slices(session_date: str) -> List[Dict]:
    """
    Get all slices for a specific session date.
    
    Args:
        session_date: The date of the session in YYYY-MM-DD format
        
    Returns:
        List of dictionaries containing slice info (path and slice number)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    slices_dir = os.path.join(base_dir, "transcripts", "slices", session_date)
    
    if not os.path.exists(slices_dir):
        print(f"No slices directory found for session {session_date}")
        return []
    
    # Get all slice files and sort them numerically by the slice number in the filename
    slice_files = glob.glob(os.path.join(slices_dir, "slice_*.md"))
    
    # Extract slice number and use it for sorting
    def get_slice_number(file_path):
        match = re.search(r'slice_(\d+)_', os.path.basename(file_path))
        if match:
            return int(match.group(1))
        return 0
    
    slice_files.sort(key=get_slice_number)
    
    return [{"path": file_path, "number": get_slice_number(file_path)} for file_path in slice_files]


def combine_slice_contents(slices: List[Dict]) -> str:
    """
    Combine contents of all slices into a single string with proper formatting.
    
    Args:
        slices: List of dictionaries containing slice info
        
    Returns:
        str: Combined contents of all slices
    """
    combined_text = "--- BEGIN SLICES ---\n"
    
    for slice_info in slices:
        slice_content = get_slice_content(slice_info["path"])
        combined_text += slice_content + "\n--- SLICE END ---\n"
    
    combined_text += "--- END SLICES ---"
    
    return combined_text


async def process_combined_slices(combined_slices: str, openai_api_key: str, session_date: str) -> str:
    """
    Process combined slices using OpenAI's Agent SDK.
    
    Args:
        combined_slices: Combined text of all slices
        openai_api_key: OpenAI API key
        model: The OpenAI model to use
        
    Returns:
        str: Processed session digest
    """
    # The API key is already set and verified in the main script
    
    # No need to explicitly get player roster as it will be accessible via reference tools
    
    # Define the tools for the agent
    tools = [
        list_reference_files,
        retrieve_reference_files,
        list_articles,
        get_articles
    ]
    
    agent = Agent(
        name="SessionDigestAgent",
        instructions=f"You are THE EDITOR, an expert continuity wrangler for tabletop RPG session transcripts. IMPORTANT: You are processing a session from {session_date}. Always begin by using list_reference_files to see what reference documents are available, and use retrieve_reference_files to access the player-roster.md and any other relevant references. These references are critical for correctly identifying and normalizing character names and other entities. Use list_articles and get_article to read the campaign memory as it existed before this session.",
        model="gpt-4.1",
        tools=tools
    )
    
    prompt = f"""You are **THE EDITOR**, an expert continuity wrangler for a D&D campaign called "Teghrim's Crossing".

IMPORTANT: You are processing a session from {session_date}.

BEGIN BY:
1. Using list_articles to see all available campaign-memory articles
2. Using get_articles with a list of slugs and the cutoff_date="{session_date}" to read the current state of multiple articles at once
3. Using list_reference_files to see all available reference documents
4. Using retrieve_reference_files tool to read the player-roster.md and any other relevant references
5. Studying these references carefully to understand character names, locations, and important entities

INPUT  
• A series of slice summaries produced by THE RECORDER.  
• Each slice covers several minutes of audio and overlaps the next by several minutes, so some events appear twice.  
• Slices are separated by the exact line:  
  --- SLICE END ---

Each slice contains:
  ## Chronological Events (numbered list; tags **SCENE**, **RP**, **ROLL**, **COMBAT**)  
  ## Entities (NPC / LOCATION / ITEM bullets)  
  ## Questions for GM (optional)  

---

### TASK  
Create one **Session Digest** that:

1. **Consolidates** all slices into a single, perfectly ordered event log.  
2. **Removes duplicates** created by the overlap between slices.  
3. **Merges multi-slice threads** (e.g., a clue introduced in one slice and resolved in another).  
4. **Normalises entity spellings** and merges duplicates by consulting the campaign's reference materials.  
5. Tags brand-new names with "(?)".  
6. Retains every event tag (**SCENE**, **RP**, **ROLL**, **COMBAT**).  

---

### RULES  
- **Do NOT invent new facts.** Only rearrange, merge, deduplicate, and correct.  
- All events from individual slices should be included in the final digest so do not remove or merge events unless they are duplicates or clearly irrelevant.
- If two events are identical or one is a shorter version of the other, keep the more complete line.  
- If a **COMBAT** line has an associated **ROLL**, keep both.  
- Number the **Chronological Log** starting at 1 with no gaps.  
- After the log, compile a deduplicated **Entities** section.  
- Append unresolved or unclear items to **Ambiguities & Uncertainties**.  
- **IMPORTANT: Before beginning:**
  1. Use list_articles to see all available campaign memory articles
  2. Use get_articles to retrieve relevant articles with cutoff_date="{session_date}"
  3. Use list_reference_files to see what reference documents are available
  4. Use retrieve_reference_files to access player-roster.md and other files containing information from the GM about the campaign world
- **You MUST use these tools to normalize entity names and ensure consistency with existing campaign information.**

---

### OUTPUT FORMAT (exactly)

## Chronological Log
1. TAG – …
2. TAG – …
(continue sequential numbering; use only the tags SCENE / ROLL / COMBAT / RP)

## Entities
### NPCs
- "Name" (role) *(first appearance)*
### Locations
- …
### Items
- …

## Ambiguities & Uncertainties
- …

<END OF SESSION DIGEST>

"""
    
    # Combine prompt with slices
    user_input = prompt + "\n\n" + combined_slices
    
    # Run the agent
    result = await Runner.run(agent, user_input)
    
    return result.final_output



def update_articles_from_digest(session_date: str, openai_api_key: str, digest_content: str) -> None:
    """
    Use an agent to process the session digest and update campaign memory articles accordingly.
    Args:
        session_date: The date of the session in YYYY-MM-DD format
        openai_api_key: OpenAI API key
        digest_path: Path to the session digest file
    """
    import asyncio
    from agents import Agent, Runner


    # Tools for updating articles
    tools = [list_articles, get_articles, update_article, list_reference_files, retrieve_reference_files]

    agent = Agent(
        name="ArticleUpdaterAgent",
        instructions=(
            f"You are the CAMPAIGN MEMORY UPDATER. Your job is to read the session digest for a given session "
            f"and update the campaign memory articles to reflect any new or changed information.\n"
            f"Rules:\n"
            f"- Use list_articles and get_articles to review the current state of the memory.\n"
            f"- Use update_article to add new information or revise details as needed.\n"
            f"- Be careful not to overwrite important existing information.\n"
            f"- Reference the digest and existing memory to ensure continuity and accuracy.\n"
            f"- Only update articles if there is clear, new, or corrected information from the digest.\n"
            f"- Do NOT remove or overwrite important information that is not contradicted by the digest.\n"
            f"- If uncertain, make your best effort to update the article using reasonable inference from the digest and prior memory.\n"
            f"- Document all changes in the article body, maintaining good formatting.\n"
            f"- You may use list_reference_files and retrieve_reference_files to access reference documents provided by the GM. These may help you understand the general campaign world and ensure your updates are accurate and consistent.\n"
        ),
        model="gpt-4.1",
        tools=tools
    )

    prompt = (
        """
        Please retrieve and update every campaign memory article based on the session digest below.
        \n---\n
        SESSION DIGEST for {session_date}:\n\n"""
        f"""{digest_content}"""
    )

    async def run_update():
        result = await Runner.run(agent, prompt)
        print("Article update agent output:\n", result.final_output)

    asyncio.run(run_update())

def combine_session_slices(session_date: str, openai_api_key: str) -> Optional[str]:

    """
    Combine all slices for a session and process them using the Agent SDK.
    
    Args:
        session_date: The date of the session in YYYY-MM-DD format
        openai_api_key: OpenAI API key
        
    Returns:
        Optional[str]: Path to the session bible file, or None if an error occurred
    """
    # Get all slices for the session
    slices = get_session_slices(session_date)
    
    if not slices:
        print(f"No slices found for session {session_date}")
        return None
    
    print(f"Found {len(slices)} slices for session {session_date}")
    
    # Combine slice contents
    combined_slices = combine_slice_contents(slices)
    
    # Set up output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "transcripts", "digests")
    os.makedirs(output_dir, exist_ok=True)
    
    # Output file path
    output_file = os.path.join(output_dir, f"{session_date}.md")
    
    try:
        # Process combined slices
        print(f"Processing combined slices for session {session_date}...")
        session_digest = asyncio.run(process_combined_slices(combined_slices, openai_api_key, session_date))
        
        # Save the result
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(session_digest)
        
        print(f"Session digest created successfully: {output_file}")
        # After digest creation, update articles based on the digest
        update_articles_from_digest(session_date, openai_api_key, session_digest)
        return output_file

    
    except Exception as e:
        print(f"Error creating session digest: {str(e)}")
        return None


def process_all_sessions_to_digests(openai_api_key: str) -> None:
    """
    Process all sessions with slices into session digests.
    
    Args:
        openai_api_key: OpenAI API key
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    slices_dir = os.path.join(base_dir, "transcripts", "slices")
    
    if not os.path.exists(slices_dir):
        print(f"No slices directory found at {slices_dir}")
        return
    
    # Get all session directories (dates)
    session_dates = [d for d in os.listdir(slices_dir) if os.path.isdir(os.path.join(slices_dir, d))]
    
    if not session_dates:
        print("No session dates found.")
        return
    
    print(f"Found {len(session_dates)} sessions to process.\n")
    
    # Process each session
    for session_date in session_dates:
        # Check if digest already exists
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "transcripts", "digests")
        
        # Check if this session already has a digest
        if os.path.exists(output_dir):
            digest_file = os.path.join(output_dir, f"{session_date}.md")
            if os.path.exists(digest_file):
                print(f"Session {session_date} already has a digest, skipping")
                continue
        
        print(f"Processing session {session_date}...")
        try:
            combine_session_slices(session_date, openai_api_key)
            print(f"Digest creation complete for {session_date}!\n")
        except Exception as e:
            print(f"Error processing session {session_date}: {str(e)}\n")
            continue
    
    # After processing all sessions, export the latest version of each article to markdown files
    print("\nExporting the latest version of each article to markdown files...")
    export_articles_to_markdown()





def export_articles_to_markdown() -> None:
    """
    Export the latest version of each article to markdown files in the output/codex folder.
    Sets file modification times to match the last update time of each article in the database.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "output", "codex")
    os.makedirs(output_dir, exist_ok=True)
    
    # Get current date for retrieving the latest versions
    current_date = date.today()
    
    # Get all article metadata
    articles = list_articles_meta()
    
    if not articles:
        print("No articles found in the campaign memory database.")
        return
    
    print(f"Found {len(articles)} articles to export.")
    
    for article in articles:
        slug = article['slug']
        title = article['title']
        
        # Get the latest content and timestamp of the article
        content, last_modified = latest_revision_for_date(slug, current_date)
        content = content or ""
        
        if not content:
            print(f"Warning: No content found for article '{title}' ({slug})")
            continue
        
        # Create the output file (use the slug for the filename)
        output_file = os.path.join(output_dir, f"{slug}.md")
        
        try:
            # Write the content to the file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Set the modification time of the file to match the article's last modification
            if last_modified:
                os.utime(output_file, (last_modified, last_modified))
            
            print(f"Exported '{title}' to {output_file} with timestamp from database")
        except Exception as e:
            print(f"Error exporting article '{title}': {str(e)}")
    
    print("Export of articles to markdown files completed with preserved timestamps.")
