#!/usr/bin/env python
"""
Utilities for file management and organization.
"""

import os
import re
from typing import Dict, List, Tuple


def extract_date_from_filename(filename: str) -> Tuple[str, str]:
    """
    Extract date in YYMMDD format from filename and convert to YYYY-MM-DD format.
    
    Args:
        filename: Filename in format YYMMDD_####*.mp3
        
    Returns:
        Tuple of (raw_date_string, formatted_date_string)
    """
    # Use regex to extract the date part (YYMMDD)
    match = re.match(r'^(\d{6})_', os.path.basename(filename))
    if not match:
        raise ValueError(f"Could not extract date from filename: {filename}")
    
    raw_date = match.group(1)
    year = int(f"20{raw_date[0:2]}")  # Assuming 20xx for years
    month = int(raw_date[2:4])
    day = int(raw_date[4:6])
    
    formatted_date = f"{year}-{month:02d}-{day:02d}"
    return raw_date, formatted_date


def group_audio_files_by_date(audio_dir: str) -> Dict[str, List[str]]:
    """
    Group audio files in the directory by their date.
    
    Args:
        audio_dir: Path to directory containing audio files
        
    Returns:
        Dictionary mapping formatted dates (YYYY-MM-DD) to lists of audio file paths
    """
    audio_files_by_date = {}
    
    # Ensure the directory exists
    if not os.path.exists(audio_dir):
        print(f"Warning: Audio directory {audio_dir} does not exist")
        return audio_files_by_date
    
    # Get all MP3 files
    for filename in os.listdir(audio_dir):
        if filename.lower().endswith('.mp3') and re.match(r'^\d{6}_\d{4}', filename):
            file_path = os.path.join(audio_dir, filename)
            try:
                raw_date, formatted_date = extract_date_from_filename(filename)
                if formatted_date not in audio_files_by_date:
                    audio_files_by_date[formatted_date] = []
                audio_files_by_date[formatted_date].append(file_path)
            except ValueError as e:
                print(f"Warning: Skipping file {filename}: {str(e)}")
    
    # Sort files within each date group
    for date, files in audio_files_by_date.items():
        audio_files_by_date[date] = sorted(files)
    
    return audio_files_by_date


def find_unprocessed_sessions(audio_dir: str, transcripts_dir: str) -> Dict[str, List[str]]:
    """
    Find sessions that have audio files but no transcript.
    
    Args:
        audio_dir: Path to directory containing audio files
        transcripts_dir: Path to directory containing transcript files
        
    Returns:
        Dictionary mapping dates to lists of audio file paths for unprocessed sessions
    """
    # Group audio files by date
    audio_files_by_date = group_audio_files_by_date(audio_dir)
    
    # Get list of existing transcript files from Raw Transcripts directory only
    transcript_files = []
    raw_transcripts_dir = os.path.join(transcripts_dir, "Raw Transcripts")
    
    # Check Raw Transcripts directory
    if os.path.exists(raw_transcripts_dir):
        transcript_files.extend([f for f in os.listdir(raw_transcripts_dir) 
                              if f.endswith('.md') and re.match(r'\d{4}-\d{2}-\d{2}\.md', f)])
    
    # Extract dates from transcript filenames
    transcript_dates = set()
    for filename in transcript_files:
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})\.md', filename)
        if date_match:
            transcript_dates.add(date_match.group(1))
    
    # Find dates that have audio files but no transcript
    unprocessed_sessions = {}
    for date, files in audio_files_by_date.items():
        if date not in transcript_dates:
            unprocessed_sessions[date] = files
    
    return unprocessed_sessions
