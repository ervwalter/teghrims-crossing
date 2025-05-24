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
from ..memory.references import get_player_roster, list_reference_files, retrieve_reference_files
from ..memory.tools import list_articles, get_articles
from ..notion.tools import get_all_entities
from ..memory.context import SessionContext

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
    from ..config import SLICES_DIR
    slices_dir = os.path.join(SLICES_DIR, session_date)
    
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
        session_date: Session date for context
        
    Returns:
        str: Processed session digest
    """
    # The API key is already set and verified in the main script
    
    # Define the tools for the agent
    tools = [
        list_reference_files,
        retrieve_reference_files,
        list_articles,
        get_articles,
        get_all_entities
    ]
    
    # Create session context
    session_context = SessionContext(session_date=session_date)
    
    agent = Agent[SessionContext](
        name="SessionDigestAgent",
        instructions="You are THE EDITOR, an expert continuity wrangler for tabletop RPG session transcripts. Always begin by using list_reference_files to see what reference documents are available, and use retrieve_reference_files to access the player-roster.md and any other relevant references. These references are critical for correctly identifying and normalizing character names and other entities. Use list_articles and get_articles to read the campaign memory. You can also use get_all_entities to see all known entities in the campaign world, which will help you normalize entity names in the transcript.",
        model="gpt-4.1",
        tools=tools
    )
    
    prompt = """You are **THE EDITOR**, an expert continuity wrangler for a D&D campaign called "Teghrim's Crossing".

BEGIN BY:
1. Using list_articles to see all available campaign-memory articles
2. Using get_articles with a list of slugs to read the current state of multiple articles at once (the session date is automatically used from context)
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
  2. Use get_articles to retrieve relevant articles (the session date is automatically used from context)
  3. Use list_reference_files to see what reference documents are available
  4. Use retrieve_reference_files to access player-roster.md and other files containing information from the GM about the campaign world
  5. Use get_all_entities to see all known entities in the campaign world to help normalize entity names
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
    
    # Run the agent with session context
    result = await Runner.run(agent, user_input, context=session_context)
    
    return result.final_output


def combine_session_slices(session_date: str, openai_api_key: str) -> Optional[str]:
    """
    Combine all slices for a session and process them using the Agent SDK.
    
    Args:
        session_date: The date of the session in YYYY-MM-DD format
        openai_api_key: OpenAI API key
        
    Returns:
        Optional[str]: Path to the session digest file, or None if an error occurred
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
    from ..config import DIGESTS_DIR
    output_dir = DIGESTS_DIR
    
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
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    slices_dir = os.path.join(base_dir, "data", "slices")
    
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
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(base_dir, "data", "digests")
        
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
    
    print("Session digest processing complete!\n")