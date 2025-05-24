#!/usr/bin/env python
"""
Functions for compiling audio file transcripts into complete session transcripts.
"""

import os
import sys
import re
from typing import List

from .audio_transcription import transcribe_audio, format_transcript
from .file_utils import find_unprocessed_sessions


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
    raw_transcripts_dir = os.path.join(transcripts_dir, "raw-transcripts")
    os.makedirs(raw_transcripts_dir, exist_ok=True)
    
    # Create a segments directory for individual pieces
    segments_dir = os.path.join(raw_transcripts_dir, "segments", date)
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
                from .transcript_slicing import slice_transcript
                from .slice_summarization import process_transcript_slices
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
        print("Individual successfully transcribed segments are saved in the segments directory.")
        print("Run the script again to retry failed segments.")
        sys.exit(1)  # Exit with error code


def auto_process_sessions(api_key: str, debug: bool = False, timeout: int = 300, retries: int = 2) -> None:
    """
    Automatically process all unprocessed sessions.
    
    Args:
        api_key: ElevenLabs API key (can be None to skip audio processing)
        debug: Enable debug mode (kept for compatibility, but not used)
        timeout: Timeout in seconds for API calls
        retries: Maximum number of retry attempts for API calls
    """
    # Set up paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audio_dir = os.path.join(base_dir, "audio")
    transcripts_dir = os.path.join(base_dir, "data")
    
    print(f"Looking for unprocessed sessions in {audio_dir}...\n")
    
    # Check if API key is provided
    if api_key is None:
        print("ElevenLabs API key not provided. Skipping audio transcription.")
        return
        
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
