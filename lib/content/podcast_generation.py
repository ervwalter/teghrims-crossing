#!/usr/bin/env python3
"""
Podcast generation module for processing podcast script files.
Converts markdown podcast scripts to MP3 files using ElevenLabs TTS.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
import time
from typing import List, Tuple, Optional

from ..config import SUMMARIES_DIR, PODCASTS_DIR

try:
    from elevenlabs import Voice, VoiceSettings
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# Voice IDs from the original code
HOST_VOICE_ID = "zGjIP4SZlMnY9m93k97r"
GUEST_VOICE_ID = "hmMWXCj9K7N5mCPcRkfC"

# Pause duration in milliseconds
PAUSE_BETWEEN_SEGMENTS_MS = 750

# ElevenLabs API settings
VOICE_SETTINGS = VoiceSettings(
    stability=0.7,
    similarity_boost=0.75,
    style=0.2,
    use_speaker_boost=True,
    speed=1.19
)
MODEL_ID = "eleven_flash_v2_5"


def parse_podcast_script(script_content: str) -> List[Tuple[str, str]]:
    """
    Parses the podcast script into (speaker, text) segments.
    
    Args:
        script_content: Raw script content
        
    Returns:
        List of (speaker, text) tuples
    """
    segments = []
    current_speaker = None
    current_text_lines = []

    for line_num, line_raw in enumerate(script_content.splitlines()):
        line = line_raw.strip()

        speaker_match_host = re.match(r"^(HOST):(.*)", line, re.IGNORECASE)
        speaker_match_guest = re.match(r"^(GUEST):(.*)", line, re.IGNORECASE)
        is_new_speaker_line = bool(speaker_match_host or speaker_match_guest)

        if is_new_speaker_line:
            if current_speaker and current_text_lines:
                segments.append((current_speaker, "\n".join(current_text_lines).strip()))
                current_text_lines = []
            
            if speaker_match_host:
                current_speaker = "HOST"
                text_after_speaker_tag = speaker_match_host.group(2).strip()
            else:
                current_speaker = "GUEST"
                text_after_speaker_tag = speaker_match_guest.group(2).strip()

            if text_after_speaker_tag:
                current_text_lines.append(text_after_speaker_tag)
        
        elif current_speaker:
            current_text_lines.append(line)
        
        elif line:
            print(f"Warning: Skipping line {line_num+1} (not part of a speaker segment): '{line_raw}'")

    if current_speaker and current_text_lines:
        segments.append((current_speaker, "\n".join(current_text_lines).strip()))
    
    segments = [(speaker, text) for speaker, text in segments if text]
    return segments


def generate_audio_segment_file(client: ElevenLabs, text: str, voice_id: str, 
                                temp_dir: Path, segment_idx: int) -> Optional[Path]:
    """
    Generates an audio segment and saves it to a temporary file.
    
    Args:
        client: ElevenLabs client
        text: Text to convert to speech
        voice_id: Voice ID to use
        temp_dir: Temporary directory for audio files
        segment_idx: Index of the segment
        
    Returns:
        Path to the generated audio file, or None if failed
    """
    try:
        print(f"  Generating audio for segment {segment_idx+1}: \"{text[:60].replace(chr(10), ' ')}...\" with voice {voice_id}")
        if not text.strip():
            print("  Skipping empty text segment.")
            return None

        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            voice_settings=VOICE_SETTINGS,
            model_id=MODEL_ID
        )
        
        temp_audio_path = temp_dir / f"segment_{segment_idx+1}.mp3"
        
        # Handle the response correctly
        if hasattr(audio, 'read'):
            audio_content = audio.read()
        elif isinstance(audio, bytes):
            audio_content = audio
        else:
            try:
                if hasattr(audio, '__iter__') and not isinstance(audio, (str, bytes, bytearray)):
                    audio_content = b''.join(chunk for chunk in audio)
                else:
                    audio_content = bytes(audio)
            except Exception as conversion_error:
                print(f"  Error converting audio response to bytes: {conversion_error}")
                return None
        
        with open(temp_audio_path, "wb") as f:
            f.write(audio_content)
            
        return temp_audio_path
        
    except Exception as e:
        print(f"Error generating audio for text '{text[:30]}...': {e}")
        time.sleep(1)
        return None


def process_script_to_mp3(client: ElevenLabs, script_file_path: Path, output_mp3_path: Path):
    """
    Process a single podcast script to MP3.
    
    Args:
        client: ElevenLabs client
        script_file_path: Path to the script file
        output_mp3_path: Path for the output MP3
    """
    print(f"Processing script: {script_file_path.name}")
    
    try:
        with open(script_file_path, "r", encoding="utf-8") as f:
            script_content = f.read()
    except Exception as e:
        print(f"Error reading script file {script_file_path}: {e}")
        return

    segments = parse_podcast_script(script_content)
    if not segments:
        print(f"No speaker segments found in the script: {script_file_path.name}. Skipping.")
        return

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_audio_files = []
        all_segments_processed_successfully = True
        
        for i, (speaker, text) in enumerate(segments):
            if not text.strip():
                print(f"  Skipping empty text for speaker {speaker} at segment {i+1}")
                continue

            voice_id = HOST_VOICE_ID if speaker.upper() == "HOST" else GUEST_VOICE_ID
            
            temp_audio_file = generate_audio_segment_file(client, text, voice_id, temp_dir_path, i)

            if temp_audio_file and temp_audio_file.exists():
                temp_audio_files.append(temp_audio_file)
            else:
                print(f"Failed to generate audio segment {i+1} for speaker {speaker}.")
                all_segments_processed_successfully = False
                break

        # Combine audio segments
        if all_segments_processed_successfully and temp_audio_files:
            try:
                print(f"Combining audio segments into {output_mp3_path}...")
                output_mp3_path.parent.mkdir(parents=True, exist_ok=True)
                
                if AudioSegment is not None:
                    # Use pydub to combine audio
                    combined_audio = AudioSegment.empty()
                    for i, audio_file in enumerate(temp_audio_files):
                        segment = AudioSegment.from_mp3(audio_file)
                        combined_audio += segment
                        
                        if i < len(temp_audio_files) - 1:
                            pause = AudioSegment.silent(duration=PAUSE_BETWEEN_SEGMENTS_MS)
                            combined_audio += pause
                            
                    combined_audio.export(output_mp3_path, format="mp3")
                else:
                    # Use ffmpeg directly
                    concat_file = temp_dir_path / "concat_list.txt"
                    
                    with open(concat_file, "w") as f:
                        for audio_file in temp_audio_files:
                            f.write(f"file '{audio_file}'\n")
                    
                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(concat_file),
                        "-c", "copy",
                        str(output_mp3_path)
                    ]
                    
                    subprocess.run(ffmpeg_cmd, check=True)
                
                print(f"Successfully created podcast: {output_mp3_path}")
            except Exception as e:
                print(f"Error creating combined MP3 at {output_mp3_path}: {e}")
        elif not all_segments_processed_successfully:
            print(f"Podcast generation failed for {script_file_path.name} due to errors in segment processing.")
        else:
            print(f"No audio segments were generated for {script_file_path.name}. Output MP3 not created.")


def process_all_podcasts(eleven_api_key: str) -> None:
    """
    Process all podcast script files in the output/summaries directory.
    
    Args:
        eleven_api_key: ElevenLabs API key
    """
    if ElevenLabs is None:
        print("ElevenLabs SDK not installed. Cannot generate podcasts.")
        return
    
    if not eleven_api_key:
        print("ElevenLabs API key not provided. Skipping podcast generation.")
        return
    
    try:
        client = ElevenLabs(api_key=eleven_api_key)
    except Exception as e:
        print(f"Error initializing ElevenLabs client: {e}")
        return

    summaries_dir = Path(SUMMARIES_DIR)
    podcasts_dir = Path(PODCASTS_DIR)
    
    # Ensure podcasts directory exists
    podcasts_dir.mkdir(parents=True, exist_ok=True)
    
    if not summaries_dir.exists():
        print(f"Summaries directory not found: {summaries_dir}")
        return

    script_files = sorted(list(summaries_dir.glob("podcast-script.*.md")))
    if not script_files:
        print("No podcast scripts found in the summaries directory.")
        return

    processed_count = 0
    skipped_count = 0
    error_count = 0

    print(f"\nStarting podcast generation process...")
    print(f"Scanning for podcast scripts in: {summaries_dir}")
    print(f"Outputting MP3s to: {podcasts_dir}")
    print("---")

    for script_file in script_files:
        match = re.search(r"podcast-script\.(.*?)\.md$", script_file.name)
        if match:
            date_str = match.group(1)
            output_mp3_filename = f"{date_str}.mp3"
            output_mp3_path = podcasts_dir / output_mp3_filename

            print(f"\nChecking script: {script_file.name}")
            if output_mp3_path.exists():
                print(f"  Podcast already exists: {output_mp3_path}. Skipping.")
                skipped_count += 1
                continue
            
            print(f"  Found new script to process: {script_file.name}")
            try:
                process_script_to_mp3(client, script_file, output_mp3_path)
                if output_mp3_path.exists():
                    processed_count += 1
                else:
                    print(f"  MP3 file was not created for {script_file.name} despite processing attempt.")
                    error_count += 1 
            except Exception as e:
                print(f"An unexpected error occurred processing {script_file.name}: {e}")
                error_count += 1
        else:
            print(f"Skipping file with unexpected name format: {script_file.name}")

    print("\n--- Processing Complete ---")
    print(f"Successfully processed {processed_count} new scripts.")
    print(f"Skipped {skipped_count} already existing podcasts.")
    if error_count > 0:
        print(f"Encountered errors with {error_count} scripts.")
    print("Podcast generation complete!")


if __name__ == "__main__":
    # For testing
    import sys
    api_key = os.getenv("ELEVEN_API_KEY")
    if not api_key:
        print("ELEVEN_API_KEY environment variable not set")
        sys.exit(1)
    
    process_all_podcasts(api_key)