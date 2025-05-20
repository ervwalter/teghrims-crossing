#!/usr/bin/env python
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
import time
from pathlib import Path
from elevenlabs.client import ElevenLabs
from io import BytesIO
from typing import Any, List, Dict, Tuple, Optional

# Import OpenAI SDK
import openai
from openai import OpenAI
from agents import Agent, Runner, function_tool

def transcribe_audio(file_path: str, api_key: str, num_speakers: int = 6, debug: bool = False, output_file: Optional[str] = None, max_retries: int = 1, 
timeout: int = 300) -> Tuple[Any, str]:
    """
    Transcribe an audio file using the ElevenLabs API with speaker diarization.
    
    Args:
        file_path: Path to the audio file to transcribe
        api_key: ElevenLabs API key
        num_speakers: Maximum number of speakers to detect (default: 6)
        debug: Enable debug mode to save raw API response
        output_file: Optional output file path, or "skip_file_output" to skip
        max_retries: Maximum number of retry attempts for API calls (default: 1)
        timeout: Timeout in seconds for API calls (default: 300 seconds / 5 minutes)
        
    Returns:
        Tuple of (raw response object, formatted transcript)
    """
    import httpx
    import time
    
    # Get the base name for output files
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Open the audio file in binary mode
    with open(file_path, "rb") as audio_file:
        audio_data = audio_file.read()
    
    # Initialize client with timeout
    client = ElevenLabs(
        api_key=api_key,
        timeout=timeout
    )
    
    # Make the API request with all parameters directly
    try:
        print(f"Transcribing {os.path.basename(file_path)}...")
        
        # Make the API request
        transcription = client.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",
            language_code="eng",
            diarize=True,
            num_speakers=num_speakers,
            tag_audio_events=True
        )
        
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

        # Format the transcript with timestamps (no time offset for single files)
        formatted_transcript = format_transcript(transcription, time_offset=0.0)
        
        # Save the transcript only if not part of a batch process
        if output_file is None:
            # Create Raw Transcripts directory if it doesn't exist
            base_dir = os.path.dirname(os.path.abspath(__file__))
            raw_transcripts_dir = os.path.join(base_dir, "Transcripts", "Raw Transcripts")
            os.makedirs(raw_transcripts_dir, exist_ok=True)
            
            # Save to Raw Transcripts directory only
            raw_output_path = os.path.join(raw_transcripts_dir, f"{base_name}_transcript.md")
            with open(raw_output_path, "w") as f:
                f.write(formatted_transcript)
            print(f"\nTranscription complete! File saved as: {raw_output_path}")
        elif output_file != "skip_file_output":
            with open(output_file, "w") as f:
                f.write(formatted_transcript)
            print(f"\nTranscription of {os.path.basename(file_path)} complete!")
        else:
            print(f"\nTranscription of {os.path.basename(file_path)} complete!")

        # Return the raw response object and the formatted transcript
        return transcription, formatted_transcript
        
    except Exception as e:
        error_message = f"Error transcribing {os.path.basename(file_path)}: {str(e)}"
        print(error_message)
        
        # Return a placeholder and error message
        placeholder = {"text": error_message, "words": []}
        return placeholder, f"*{error_message}*\n\n"

# Custom formatting function removed - using API's native formatting options instead

def format_transcript(transcription_data, time_offset=0.0) -> str:
    """
    Format the transcription with speaker labels (Speaker 1, Speaker 2, etc.)
    and timestamps for each speaker entry.
    
    Args:
        transcription_data: The raw transcription response from ElevenLabs API
        time_offset: Cumulative time offset in seconds from previous audio files
        
    Returns:
        str: Formatted markdown transcript with speaker labels and timestamps
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
            
            # Add speaker label with timestamp if speaker changed
            if current_speaker != speaker_id:
                # Calculate cumulative time with offset
                cumulative_time = time_offset + start_time
                # Format time as [HH:MM:SS]
                hours, remainder = divmod(cumulative_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"[{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}]"
                
                # Add timestamp and speaker label
                current_paragraph.append(f"{time_str} {speaker_label}: ")
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
    # Ensure Raw Transcripts directory exists
    raw_transcripts_dir = os.path.join(transcripts_dir, "Raw Transcripts")
    os.makedirs(raw_transcripts_dir, exist_ok=True)
    
    # Create a segments directory for individual pieces
    segments_dir = os.path.join(raw_transcripts_dir, "Segments", date)
    os.makedirs(segments_dir, exist_ok=True)
    
    # Prepare output file path
    raw_output_path = os.path.join(raw_transcripts_dir, f"{date}.md")
    
    # Initialize transcript content (no header)
    transcript_content = []
    
    # Process each audio file
    total_files = len(audio_files)
    cumulative_time_offset = 0.0  # Track cumulative time across files
    all_files_successful = True
    
    for i, audio_file in enumerate(audio_files):
        file_basename = os.path.basename(audio_file)
        segment_file = os.path.join(segments_dir, f"{file_basename}.md")
        
        # Check if this segment already exists
        if os.path.exists(segment_file):
            print(f"Segment file for {file_basename} already exists, skipping transcription")
            with open(segment_file, "r") as f:
                segment_content = f.read()
                
            # Extract duration from the segment file if possible
            duration_match = re.search(r'DURATION:(\d+\.\d+)', segment_content)
            if duration_match:
                file_duration = float(duration_match.group(1))
                cumulative_time_offset += file_duration
                
            # Remove the metadata line before adding to transcript
            segment_content = re.sub(r'DURATION:\d+\.\d+\n', '', segment_content)
            transcript_content.append(segment_content)
            
        else:
            print(f"Processing file {i+1}/{total_files}: {file_basename}")
            
            # Transcribe the audio file
            try:
                transcription_data, formatted_transcript = transcribe_audio(
                    audio_file, 
                    api_key, 
                    debug=debug,
                    output_file="skip_file_output"  # Skip individual file output
                )
                
                # Format transcript with cumulative time offset
                formatted_transcript = format_transcript(transcription_data, cumulative_time_offset)
                
                # Get the duration of the current file
                file_duration = 0
                if hasattr(transcription_data, 'words') and transcription_data.words:
                    last_word = transcription_data.words[-1]
                    if hasattr(last_word, 'end'):
                        file_duration = last_word.end
                        cumulative_time_offset += file_duration
                
                # Only save segment file if transcription was successful and has content
                if formatted_transcript.strip():
                    with open(segment_file, "w") as f:
                        f.write(f"DURATION:{file_duration}\n")
                        f.write(formatted_transcript)
                
                # Add to transcript content
                transcript_content.append(formatted_transcript)
                    
            except Exception as e:
                error_msg = f"Error transcribing {file_basename}: {str(e)}"
                print(error_msg, file=sys.stderr)
                all_files_successful = False
                # Don't add error messages to transcript content
                # Exit the loop if any file fails
                break
        
        # Add separation between sections
        if i < total_files - 1:
            transcript_content.append("\n---\n\n")
    
    # Only write the combined transcript if all files were processed successfully
    if all_files_successful:
        # Write the combined transcript to the raw file only
        with open(raw_output_path, "w") as f:
            f.write("".join(transcript_content))
        
        print(f"\nSession transcript complete! Saved to: {raw_output_path}")
        
        # Process transcript slices if OpenAI API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            print("\nProcessing transcript slices with OpenAI...")
            try:
                process_transcript_slices(raw_output_path, openai_api_key)
                print("Slice processing complete!")
            except Exception as e:
                print(f"Error processing slices: {str(e)}")
                print("Transcript was generated successfully, but slice processing failed.")
        else:
            print("\nOpenAI API key not found in environment variables. Skipping slice processing.")
            print("To process slices, set the OPENAI_API_KEY environment variable.")
    else:
        print("\nTranscription incomplete. Some files failed to process.")
        print("Individual successfully transcribed segments are saved in the Segments directory.")
        print("Run the script again to retry failed segments.")
        sys.exit(1)  # Exit with error code

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
    
    prompt = f"""You are **THE RECORDER**, a ruthless but narrative-aware stenographer.

CONTEXT
• Each input chunk covers some amount of raw audio.
• Speaker tags like "Speaker 1" mark dialogue turns but do not identify real people.

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

## Questions for GM
- …

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


def slice_transcript(transcript_text: str, slice_minutes: int = 30, overlap_minutes: int = 5) -> List[Dict]:
    """
    Slice a transcript into chunks based on timestamps.
    
    Args:
        transcript_text: The full transcript text
        slice_minutes: Size of each slice in minutes
        overlap_minutes: Overlap between slices in minutes
        
    Returns:
        List of dictionaries containing slice info (start_time, end_time, text)
    """
    # Regular expression to find timestamps in the format [HH:MM:SS]
    timestamp_pattern = r'\[(\d{2}):(\d{2}):(\d{2})\]'
    
    # Find all timestamps in the transcript
    matches = list(re.finditer(timestamp_pattern, transcript_text))
    
    if not matches:
        # If no timestamps found, return the entire transcript as one slice
        return [{
            "start_time": "00:00:00",
            "end_time": "Unknown",
            "text": transcript_text
        }]
    
    # Convert slice and overlap times to seconds
    slice_seconds = slice_minutes * 60
    overlap_seconds = overlap_minutes * 60
    step_seconds = slice_seconds - overlap_seconds
    
    # Get the last timestamp to determine the end of the transcript
    last_match = matches[-1]
    last_hours = int(last_match.group(1))
    last_minutes = int(last_match.group(2))
    last_seconds = int(last_match.group(3))
    last_total_seconds = last_hours * 3600 + last_minutes * 60 + last_seconds
    
    # Create slices
    slices = []
    current_start = 0
    
    while current_start <= last_total_seconds:
        current_end = min(current_start + slice_seconds, last_total_seconds + 60)  # Add 60 seconds buffer at the end
        
        # Find the closest timestamp to the start and end times
        start_idx = None
        end_idx = None
        
        for i, match in enumerate(matches):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Find the closest timestamp to the start time
            if total_seconds >= current_start and start_idx is None:
                start_idx = i
            
            # Find the closest timestamp to the end time
            if total_seconds >= current_end and end_idx is None:
                end_idx = i
                break
        
        # If we couldn't find an end index, use the last match
        if end_idx is None:
            end_idx = len(matches) - 1
        
        # If we couldn't find a start index, use the first match
        if start_idx is None:
            start_idx = 0
        
        # Get the text between the start and end timestamps
        if start_idx <= end_idx:
            start_match = matches[start_idx]
            end_match = matches[end_idx]
            
            # Format the start and end times
            start_time = f"{start_match.group(1)}:{start_match.group(2)}:{start_match.group(3)}"
            end_time = f"{end_match.group(1)}:{end_match.group(2)}:{end_match.group(3)}"
            
            # Extract the text for this slice
            if end_idx < len(matches) - 1:
                slice_text = transcript_text[start_match.start():matches[end_idx + 1].start()]
            else:
                slice_text = transcript_text[start_match.start():]
            
            slices.append({
                "start_time": start_time,
                "end_time": end_time,
                "text": slice_text
            })
        
        # Move to the next slice
        current_start += step_seconds
    
    return slices


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
    transcript_dir = os.path.dirname(transcript_path)
    date = os.path.basename(transcript_path).replace(".md", "")
    slices_dir = os.path.join(transcript_dir, "Slices", date)
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


def auto_process_sessions(api_key: str, debug: bool = False, timeout: int = 300, retries: int = 2) -> None:
    """
    Automatically process all unprocessed sessions.
    
    Args:
        api_key: ElevenLabs API key
        debug: Enable debug mode
        timeout: Timeout in seconds for API calls
        retries: Maximum number of retry attempts for API calls
    """
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "Audio")
    transcripts_dir = os.path.join(base_dir, "Transcripts")
    
    print(f"Looking for unprocessed sessions in {audio_dir}...\n")
    
    # Find unprocessed sessions
    unprocessed_sessions = find_unprocessed_sessions(audio_dir, transcripts_dir)
    
    if not unprocessed_sessions:
        print("No unprocessed sessions found.")
        return
    
    print(f"Found {len(unprocessed_sessions)} unprocessed sessions.\n")
    
    # Process each session
    for date, files in unprocessed_sessions.items():
        print(f"Processing session from {date} ({len(files)} files)...")
        create_session_transcript(date, files, api_key, transcripts_dir, debug)


def process_all_transcripts_to_slices(openai_api_key: str, model: str = "gpt-4.1-mini") -> None:
    """
    Process all existing transcripts into slices.
    
    Args:
        openai_api_key: OpenAI API key
        model: The OpenAI model to use
    """
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_transcripts_dir = os.path.join(base_dir, "Transcripts", "Raw Transcripts")
    
    if not os.path.exists(raw_transcripts_dir):
        print(f"No transcripts directory found at {raw_transcripts_dir}")
        return
    
    # Find all transcript files (excluding the Segments and Slices directories)
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
        slices_dir = os.path.join(raw_transcripts_dir, "Slices", date)
        
        # Check if slices directory already exists and has files
        if os.path.exists(slices_dir) and os.listdir(slices_dir):
            print(f"Transcript {date} already has slices, skipping")
            continue
        
        print(f"Processing transcript from {date}...")
        try:
            process_transcript_slices(transcript_path, openai_api_key, model)
            print(f"Slice processing complete for {date}!\n")
        except Exception as e:
            print(f"Error processing transcript {date}: {str(e)}\n")
            continue


def main():
    # Get API keys from environment variables
    eleven_api_key = os.environ.get("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("Error: ELEVEN_API_KEY environment variable not set")
        sys.exit(1)
    
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process audio files to generate transcripts and process them into slices.")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to save raw API response')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for API calls (default: 300)')
    parser.add_argument('--retries', type=int, default=2, help='Maximum number of retry attempts for API calls (default: 2)')
    parser.add_argument('--model', type=str, default="gpt-4.1-mini", help='OpenAI model to use for slice processing (default: gpt-4.1-mini)')
    args = parser.parse_args()
    
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "Audio")
    transcripts_dir = os.path.join(base_dir, "Transcripts")
    
    try:
        # Step 1: Process audio files into transcripts
        print("Step 1: Processing audio files into transcripts...")
        auto_process_sessions(eleven_api_key, args.debug, args.timeout, args.retries)
        print("\nAudio processing complete!\n")
        
        # Step 2: Process transcripts into slices if OpenAI API key is available
        if openai_api_key:
            print("Step 2: Processing transcripts into slices...")
            process_all_transcripts_to_slices(openai_api_key, args.model)
            print("\nSlice processing complete!")
        else:
            print("\nOpenAI API key not found in environment variables. Skipping slice processing.")
            print("To process slices, set the OPENAI_API_KEY environment variable.")
        
        print("\nAll processing complete!")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error during processing: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
