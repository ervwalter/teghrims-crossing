#!/usr/bin/env python
"""
Functions for summarizing transcript slices using OpenAI's LLM.
"""

import os
import time
import re
from typing import List, Dict
import openai
from openai import OpenAI

from .transcript_slicing import slice_transcript
from .reference_utils import get_player_roster


def process_transcript_slice(transcript_chunk: str, openai_api_key: str, model: str = "gpt-4.1-mini") -> str:
    """
    Process a slice of transcript using OpenAI's LLM.
    
    Args:
        transcript_chunk: A chunk of transcript text to process
        openai_api_key: OpenAI API key
        model: The OpenAI model to use
        
    Returns:
        str: Processed transcript slice
    """
    client = OpenAI(api_key=openai_api_key)
    
    # Get player roster information
    player_roster = get_player_roster()
    
    prompt = f"""You are **THE RECORDER**, a ruthless but narrative-aware stenographer.

CONTEXT
• Each input chunk covers some amount of raw audio.
• Speaker tags like "Speaker 1" mark dialogue turns but do not identify real people.

PLAYER ROSTER INFORMATION:
{player_roster}

GOAL
Convert the slice into the EXACT structure below, preserving plot-critical detail including flavor that adds the the emotional beats and imagery while stripping filler discussion.

==========  RULES  ==========
1. Keep every meaningful roll and its purpose.
2. Paraphrase dialogue; ≤ 2 sentences per speaker.
3. Tag first appearances with **(first appearance)**.
4. Do NOT invent facts; stay within the slice.
5. Ignore speaker IDs except for detecting dialogue boundaries and interactions between players.

==========  OUTPUT FORMAT  ==========
## Chronological Events
1. SCENE  – …                ← narrative or GM description
2. ROLL   – **Check:** <char> rolls <skill> to <intent/target> → <result vs DC> – <outcome>
3. ROLL   – **Attack:** <char> rolls Strike (weapon) vs <target> → <result vs AC> – <outcome>
4. COMBAT – …                ← combat event description
5. RP     – …                ← emotional beat, clue, debate, etc.
(continue numbering; use only the tags SCENE / ROLL / COMBAT / RP)

## Entities
- NPC: "Name" (role) *(first appearance)*
- LOCATION: "Name" (context note)
- ITEM: "Name" (obtained / used / lost)

## Ambiguities & Uncertainties
- Are Marc and Mark one individual (with multiple spellings) or distinct?
- Who is Anar and what is his role?
(Max 3 bullets; skip if none.)

<BEGIN_SLICE>
{transcript_chunk}
<END_SLICE>
"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are THE RECORDER, a ruthless but narrative-aware stenographer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2  # Lower temperature for more consistent output
        )
        
        # Extract the content from the response
        processed_text = response.choices[0].message.content
        return processed_text
    
    except Exception as e:
        print(f"Error processing transcript slice: {str(e)}")
        return f"ERROR: {str(e)}"


def process_transcript_slices(transcript_path: str, openai_api_key: str, model: str = "gpt-4.1", 
                             slice_minutes: int = 15, overlap_minutes: int = 5) -> List[Dict]:
    """
    Process a transcript by slicing it and sending each slice to OpenAI for processing.
    
    Args:
        transcript_path: Path to the transcript file
        openai_api_key: OpenAI API key
        model: The OpenAI model to use
        slice_minutes: Size of each slice in minutes
        overlap_minutes: Overlap between slices in minutes
        
    Returns:
        List of dictionaries containing processed slices
    """
    # Read the transcript file
    with open(transcript_path, "r") as f:
        transcript_text = f.read()
    
    # Slice the transcript
    slices = slice_transcript(transcript_text, slice_minutes, overlap_minutes)
    
    # Create directory for processed slices
    base_dir = os.path.dirname(os.path.dirname(transcript_path))  # Go up to the data directory
    date = os.path.basename(transcript_path).replace(".md", "")
    slices_dir = os.path.join(base_dir, "slices", date)
    os.makedirs(slices_dir, exist_ok=True)
    
    processed_slices = []
    
    # Process each slice
    for i, slice_info in enumerate(slices):
        slice_filename = f"slice_{i+1:03d}_{slice_info['start_time'].replace(':', '')}_to_{slice_info['end_time'].replace(':', '')}.md"
        slice_path = os.path.join(slices_dir, slice_filename)
        
        # Check if this slice has already been processed
        if os.path.exists(slice_path):
            print(f"Slice {i+1}/{len(slices)} already processed, skipping")
            with open(slice_path, "r") as f:
                processed_text = f.read()
        else:
            print(f"Processing slice {i+1}/{len(slices)} ({slice_info['start_time']} to {slice_info['end_time']})...")
            processed_text = process_transcript_slice(slice_info['text'], openai_api_key, model)
            
            # Save the processed slice
            with open(slice_path, "w") as f:
                f.write(processed_text)
            
            # Add a small delay to avoid rate limits
            time.sleep(1)
        
        processed_slices.append({
            "start_time": slice_info['start_time'],
            "end_time": slice_info['end_time'],
            "processed_text": processed_text,
            "file_path": slice_path
        })
    
    return processed_slices


def process_all_transcripts_to_slices(openai_api_key: str) -> None:
    """
    Process all existing transcripts into slices.
    
    Args:
        openai_api_key: OpenAI API key
    """
    # Use a fixed model
    model = "gpt-4.1"
    # Set up paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_transcripts_dir = os.path.join(base_dir, "data", "raw-transcripts")
    
    if not os.path.exists(raw_transcripts_dir):
        print(f"No transcripts directory found at {raw_transcripts_dir}")
        return
    
    # Find all transcript files (excluding the segments and slices directories)
    transcript_files = []
    for file in os.listdir(raw_transcripts_dir):
        file_path = os.path.join(raw_transcripts_dir, file)
        if os.path.isfile(file_path) and file.endswith(".md") and file != "README.md":
            transcript_files.append(file_path)
    
    if not transcript_files:
        print("No transcript files found.")
        return
    
    print(f"Found {len(transcript_files)} transcript files to process.\n")
    
    # Process each transcript
    for transcript_path in transcript_files:
        date = os.path.basename(transcript_path).replace(".md", "")
        slices_dir = os.path.join(raw_transcripts_dir, "slices", date)
        
        # Check if slices directory already exists and has files
        if os.path.exists(slices_dir) and os.listdir(slices_dir):
            print(f"Transcript {date} already has slices, skipping")
            continue
        
        print(f"Processing transcript from {date}...")
        try:
            process_transcript_slices(transcript_path, openai_api_key)
            print(f"Slice processing complete for {date}!\n")
        except Exception as e:
            print(f"Error processing transcript {date}: {str(e)}\n")
            continue
