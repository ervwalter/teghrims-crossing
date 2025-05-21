#!/usr/bin/env python
"""
Functions for transcribing audio files using the ElevenLabs Speech-to-Text API.
Includes functionality to convert API responses to formatted transcripts.
"""

import os
import json
import time
from typing import Any, Tuple, Optional
from elevenlabs.client import ElevenLabs


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


def transcribe_audio(file_path: str, api_key: str, num_speakers: int = 6, debug: bool = False, 
                     output_file: Optional[str] = None, max_retries: int = 1, 
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
            # Create raw-transcripts directory if it doesn't exist
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            raw_transcripts_dir = os.path.join(base_dir, "transcripts", "raw-transcripts")
            os.makedirs(raw_transcripts_dir, exist_ok=True)
            
            # Save to raw-transcripts directory only
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
