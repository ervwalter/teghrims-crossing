#!/usr/bin/env python
"""
Utilities for file management and organization.
"""

import os
import re
import sys
from typing import Dict, List, Tuple
import shutil
from pydub import AudioSegment


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
        print(f"Warning: audio directory {audio_dir} does not exist")
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


def split_long_audio_file(audio_path: str, max_duration_sec: int = 6900) -> List[str]:
    """
    Split a long audio file into segments of at most max_duration_sec.
    Default is 6900 seconds (1 hour 55 minutes) to stay under Eleven Labs 2-hour limit.
    
    Args:
        audio_path: Path to the audio file
        max_duration_sec: Maximum duration of each segment in seconds
        
    Returns:
        List of paths to the generated segment files
    """
    # Load the audio file
    try:
        audio = AudioSegment.from_mp3(audio_path)
    except Exception as e:
        print(f"Error loading audio file {audio_path}: {str(e)}", file=sys.stderr)
        return [audio_path]  # Return the original file if there's an error
    
    # If the file is already short enough, return the original path
    duration_sec = len(audio) / 1000  # pydub duration is in milliseconds
    if duration_sec <= max_duration_sec:
        return [audio_path]
    
    # Get directory and filename parts
    base_dir = os.path.dirname(audio_path)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    file_ext = os.path.splitext(os.path.basename(audio_path))[1]
    
    # Create a backups directory
    backups_dir = os.path.join(base_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    backup_path = os.path.join(backups_dir, f"{base_name}{file_ext}")
    
    # Calculate how many segments we need
    segment_count = int(duration_sec / max_duration_sec) + 1
    segment_paths = []
    
    # Split the audio into segments
    all_segments_successful = True
    for i in range(segment_count):
        start_time = i * max_duration_sec * 1000  # Convert to milliseconds
        end_time = min((i + 1) * max_duration_sec * 1000, len(audio))
        segment = audio[start_time:end_time]
        
        # Create a filename for the segment directly in the audio folder
        # Format: original_name_partXX.mp3
        segment_file = os.path.join(base_dir, f"{base_name}_part{i+1:02d}.mp3")
        
        try:
            segment.export(segment_file, format="mp3")
            segment_paths.append(segment_file)
            print(f"Created segment {i+1}/{segment_count}: {segment_file}")
        except Exception as e:
            print(f"Error creating segment {i+1}: {str(e)}", file=sys.stderr)
            all_segments_successful = False
    
    # If all segments were created successfully, move the original file to backups
    if all_segments_successful:
        try:
            shutil.move(audio_path, backup_path)
            print(f"Moved original file to: {backup_path}")
        except Exception as e:
            print(f"Warning: Could not move original file to {backup_path}: {str(e)}", file=sys.stderr)
    
    return segment_paths


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
    raw_transcripts_dir = os.path.join(transcripts_dir, "raw-transcripts")
    
    # Check raw-transcripts directory
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
            # Process long files to ensure they're under the 2-hour limit
            processed_files = []
            for file_path in files:
                # Check and split files if they're too long
                segment_paths = split_long_audio_file(file_path)
                processed_files.extend(segment_paths)
            
            unprocessed_sessions[date] = processed_files
    
    return unprocessed_sessions
