#!/usr/bin/env python3
"""
Transcribe audio files using the ElevenLabs Speech-to-Text API with speaker diarization.
Outputs a nicely formatted markdown file with speaker turns.

Usage:
    python transcribe_audio.py          # Auto mode: processes all unprocessed sessions
    python transcribe_audio.py --single <path_to_audio_file>  # Process a single file

Environment Variables:
    ELEVEN_API_KEY: Your ElevenLabs API key
"""

import os
import sys
import json
import argparse
import re
import datetime
from pathlib import Path
from elevenlabs.client import ElevenLabs
from io import BytesIO
from typing import Any, List, Dict, Tuple, Optional

def transcribe_audio(file_path: str, api_key: str, num_speakers: int = 6, debug: bool = False, output_file: Optional[str] = None) -> Tuple[Any, str]:
    """
    Transcribe an audio file using the ElevenLabs API with speaker diarization.
    
    Args:
        file_path: Path to the audio file to transcribe
        api_key: ElevenLabs API key
        num_speakers: Maximum number of speakers to detect (default: 6)
        
    Returns:
        The raw response object from the API
    """
    client = ElevenLabs(api_key=api_key)
    
    # Not using additional formats as requested by user
    
    # Open the audio file in binary mode
    with open(file_path, "rb") as audio_file:
        audio_data = audio_file.read()
    
    # Make the API request with all parameters directly
    transcription = client.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v1",
        language_code="eng",
        diarize=True,
        num_speakers=num_speakers,
        tag_audio_events=True
    )
    
    # Get the base name for output files
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Save the raw response only if debug mode is enabled
    if debug:
        with open(f"{base_name}_raw_response.json", "w") as f:
            if hasattr(transcription, 'dict'):
                response_dict = transcription.dict()
            else:
                # Create a dict from available attributes
                response_dict = {
                    "text": transcription.text if hasattr(transcription, 'text') else "",
                    "words": transcription.words if hasattr(transcription, 'words') else [],
                    "language_code": transcription.language_code if hasattr(transcription, 'language_code') else ""
                }
            json.dump(response_dict, f, indent=2, ensure_ascii=False)
            print(f"Saved raw response for debugging to: {base_name}_raw_response.json")

    # Format the transcript
    formatted_transcript = format_transcript(transcription)
    
    # Determine output file name
    output_filename = output_file or f"{base_name}_transcript.md"
    
    # Save the transcript only if not part of a batch process
    if output_file is None:
        with open(output_filename, "w") as f:
            f.write(formatted_transcript)
        print(f"\nTranscription complete! File saved as: {output_filename}")
    else:
        print(f"\nTranscription of {os.path.basename(file_path)} complete!")

    # Return the raw response object and the formatted transcript
    return transcription, formatted_transcript

# Custom formatting function removed - using API's native formatting options instead

def format_transcript(transcription_data) -> str:
    """
    Format the transcription with speaker labels (Speaker 1, Speaker 2, etc.)
    and preserve the original spacing and word types.
    
    Args:
        transcription_data: The raw transcription response from ElevenLabs API
        
    Returns:
        str: Formatted markdown transcript with speaker labels
    """
    if not transcription_data:
        return "*No transcription data available*"
    
    # Initialize markdown output with no heading
    markdown = []
    
    # Check if we have text data as a fallback
    if not hasattr(transcription_data, 'words') or not transcription_data.words:
        # Fallback to simple text if no word-level data
        if hasattr(transcription_data, 'text'):
            text = transcription_data.text
        else:
            text = "No transcription text available"
        return f"{''.join(markdown)}\n{text}"
    
    current_speaker = None
    speaker_map = {}  # Maps speaker_id to Speaker 1, 2, 3...
    next_speaker_number = 1
    current_paragraph = []
    last_end_time = 0
    
    for word_info in transcription_data.words:
        # Skip if not a valid word info object
        if not hasattr(word_info, 'text'):
            continue
            
        text = word_info.text if hasattr(word_info, 'text') else ''
        word_type = word_info.type if hasattr(word_info, 'type') else 'word'
        speaker_id = word_info.speaker_id if hasattr(word_info, 'speaker_id') else 'unknown'
        start_time = word_info.start if hasattr(word_info, 'start') else 0
        end_time = word_info.end if hasattr(word_info, 'end') else 0
        
        # Skip empty entries
        if not text:
            continue
        
        # Map speaker_id to Speaker 1, 2, 3...
        if speaker_id not in speaker_map and speaker_id != 'unknown':
            speaker_map[speaker_id] = f"Speaker {next_speaker_number}"
            next_speaker_number += 1
        
        speaker_label = speaker_map.get(speaker_id, 'Unknown Speaker')
        
        # Check for speaker change or long pause (more than 1.5 seconds)
        if (current_speaker != speaker_id or 
            (current_speaker and start_time - last_end_time > 1.5)):
            # Add the current paragraph if it exists
            if current_paragraph:
                markdown.append(''.join(current_paragraph).strip() + '\n\n')
                current_paragraph = []
            
            # Add speaker label if speaker changed
            if current_speaker != speaker_id:
                current_paragraph.append(f"{speaker_label}: ")
                current_speaker = speaker_id
        
        # Add the text to current paragraph
        current_paragraph.append(text)
        last_end_time = end_time
    
    # Add the last paragraph if it exists
    if current_paragraph:
        markdown.append(''.join(current_paragraph).strip() + '\n\n')
    
    # Join everything and clean up
    content = ''.join(markdown)
    
    # Clean up common formatting issues
    clean_content = content.replace('  ', ' ').strip()
    
    return clean_content

def save_json(data, filename):
    """Save data to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        if hasattr(data, 'dict'):
            json.dump(data.dict(), f, indent=2, ensure_ascii=False)
        elif isinstance(data, dict):
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump({"response": str(data)}, f, indent=2, ensure_ascii=False)

def analyze_response(response):
    """Analyze the structure of the API response."""
    print("\n=== Response Analysis ===")
    
    if hasattr(response, '__dict__'):
        print(f"Response object has attributes: {list(response.__dict__.keys())}")
    
    if hasattr(response, 'dict'):
        data = response.dict()
        print(f"Response as dict has keys: {list(data.keys())}")
        return data
    
    if isinstance(response, dict):
        print(f"Response is a dict with keys: {list(response.keys())}")
        return response
    
    print(f"Response is of type: {type(response)}")
    return {"response": str(response)}

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
    
    # Create transcripts directory if it doesn't exist
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Get existing transcripts
    existing_transcripts = set()
    for filename in os.listdir(transcripts_dir):
        if filename.lower().endswith('.md') and re.match(r'^\d{4}-\d{2}-\d{2}\.md$', filename):
            existing_transcripts.add(filename[:-3])  # Remove .md extension
    
    # Find unprocessed sessions
    unprocessed_sessions = {}
    for date, files in audio_files_by_date.items():
        if date not in existing_transcripts:
            unprocessed_sessions[date] = files
    
    return unprocessed_sessions

def create_session_transcript(date: str, audio_files: List[str], api_key: str, transcripts_dir: str, debug: bool = False) -> None:
    """
    Create a single transcript from multiple audio files for a session.
    
    Args:
        date: Formatted date (YYYY-MM-DD)
        audio_files: List of audio file paths for the session
        api_key: ElevenLabs API key
        transcripts_dir: Directory to save transcript files
        debug: Enable debug mode
    """
    # Ensure output directory exists
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Prepare output file path
    output_path = os.path.join(transcripts_dir, f"{date}.md")
    
    # Start with a header
    transcript_content = [f"# Session Transcript: {date}\n\n"]
    
    # Process each audio file
    total_files = len(audio_files)
    for i, audio_file in enumerate(audio_files):
        file_basename = os.path.basename(audio_file)
        print(f"Processing file {i+1}/{total_files}: {file_basename}")
        
        # Add a section preamble if there are multiple files
        if total_files > 1:
            transcript_content.append(f"## Section {i+1} - {file_basename}\n\n")
            transcript_content.append("*Note: Speaker designations (Speaker 1, 2, etc.) in this section ")
            transcript_content.append("may not correspond to the same speakers in other sections.*\n\n")
        
        # Transcribe the audio file
        try:
            _, formatted_transcript = transcribe_audio(
                audio_file, 
                api_key, 
                debug=debug,
                output_file="skip_file_output"  # Skip individual file output
            )
            transcript_content.append(formatted_transcript)
            
            # Add separation between sections
            if i < total_files - 1:
                transcript_content.append("\n---\n\n")
                
        except Exception as e:
            error_msg = f"Error transcribing {file_basename}: {str(e)}\n\n"
            transcript_content.append(f"*{error_msg}*")
            print(error_msg, file=sys.stderr)
    
    # Write the combined transcript to a file
    with open(output_path, "w") as f:
        f.write("".join(transcript_content))
    
    print(f"\nSession transcript complete! Saved to: {output_path}")

def auto_process_sessions(api_key: str, debug: bool = False) -> None:
    """
    Automatically process all unprocessed sessions.
    
    Args:
        api_key: ElevenLabs API key
        debug: Enable debug mode
    """
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "Audio")
    transcripts_dir = os.path.join(base_dir, "Transcripts")
    
    print(f"Looking for unprocessed sessions in {audio_dir}...\n")
    
    # Find unprocessed sessions
    unprocessed_sessions = find_unprocessed_sessions(audio_dir, transcripts_dir)
    
    if not unprocessed_sessions:
        print("No unprocessed sessions found.")
        return
    
    print(f"Found {len(unprocessed_sessions)} unprocessed sessions.")
    
    # Process each unprocessed session
    for date, files in sorted(unprocessed_sessions.items()):
        print(f"\nProcessing session from {date} ({len(files)} files)...")
        create_session_transcript(date, files, api_key, transcripts_dir, debug)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Transcribe audio files with speaker diarization')
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument('--single', dest='audio_file', help='Process a single audio file (specify the path)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to save raw API response')
    args = parser.parse_args()
    
    # Get API key from environment variable
    api_key = os.getenv('ELEVEN_API_KEY')
    if not api_key:
        print("Error: ELEVEN_API_KEY environment variable not set", file=sys.stderr)
        print("Please set it with: export ELEVEN_API_KEY='your-api-key-here'", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.audio_file:  # Single file mode
            # Check if file exists
            if not os.path.exists(args.audio_file):
                print(f"Error: File '{args.audio_file}' not found", file=sys.stderr)
                sys.exit(1)
                
            print("Single file mode: Transcribing audio with speaker diarization...")
            transcribe_audio(args.audio_file, api_key, debug=args.debug)
        else:  # Auto mode (default)
            print("Auto mode: Processing all unprocessed sessions...")
            auto_process_sessions(api_key, debug=args.debug)
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
