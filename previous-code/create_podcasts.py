import os
import re
import io
import subprocess
import tempfile
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs # For v0.3.0+
from pathlib import Path
import time

# Configure pydub to use ffmpeg explicitly
os.environ['PYDUB_FFMPEG_PATH'] = '/opt/homebrew/bin/ffmpeg'

# Import pydub after setting the environment variable
try:
    from pydub import AudioSegment
except ImportError as e:
    print(f"Warning: Error importing pydub: {e}")
    print("Falling back to direct ffmpeg usage.")
    AudioSegment = None

# --- Configuration ---
# Determine the script's own directory to make paths relative to it
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR # Assuming create_podcasts.py is in the root of the Sessions folder
SUMMARIES_DIR = BASE_DIR / "Summaries"
PODCASTS_DIR = BASE_DIR / "Podcasts"
PROCESSED_AUDIO_DIR = BASE_DIR / ".processed-audio-snippets" # Temporary storage for snippets

HOST_VOICE_ID = "zGjIP4SZlMnY9m93k97r"  # Updated host voice
GUEST_VOICE_ID = "hmMWXCj9K7N5mCPcRkfC"

# Pause duration in milliseconds
PAUSE_BETWEEN_SEGMENTS_MS = 750

# ElevenLabs API settings
VOICE_SETTINGS = VoiceSettings(
    stability=0.7,
    similarity_boost=0.75,
    style=0.2, # A little style can make it less monotonous
    use_speaker_boost=True,
    speed=1.19  
)
MODEL_ID = "eleven_flash_v2_5" # Good general-purpose model

# --- Helper Functions ---

def parse_podcast_script(script_content: str) -> list[tuple[str, str]]:
    """Parses the podcast script into (speaker, text) segments."""
    segments = []
    current_speaker = None
    current_text_lines = [] # Stores lines for the current speaker's *entire turn*

    for line_num, line_raw in enumerate(script_content.splitlines()):
        line = line_raw.strip()

        speaker_match_host = re.match(r"^(HOST):(.*)", line, re.IGNORECASE)
        speaker_match_guest = re.match(r"^(GUEST):(.*)", line, re.IGNORECASE)
        is_new_speaker_line = bool(speaker_match_host or speaker_match_guest)

        if is_new_speaker_line:
            if current_speaker and current_text_lines:
                # Join with newline to preserve paragraph structure for ElevenLabs
                segments.append((current_speaker, "\n".join(current_text_lines).strip()))
                current_text_lines = []
            
            if speaker_match_host:
                current_speaker = "HOST"
                text_after_speaker_tag = speaker_match_host.group(2).strip()
            else: # speaker_match_guest
                current_speaker = "GUEST"
                text_after_speaker_tag = speaker_match_guest.group(2).strip()

            if text_after_speaker_tag:
                current_text_lines.append(text_after_speaker_tag)
        
        elif current_speaker: # Continuation of current speaker's dialogue
            # Add all lines (even if they were originally blank in the script and now just stripped to empty)
            # This preserves potential paragraph breaks (double newlines) for ElevenLabs when joined with "\n"
            current_text_lines.append(line)
        
        elif line: # Non-empty line before any speaker is defined or not part of a segment
            print(f"Warning: Skipping line {line_num+1} (not part of a speaker segment): '{line_raw}'")

    if current_speaker and current_text_lines: # Add the last collected segment
        segments.append((current_speaker, "\n".join(current_text_lines).strip()))
    
    # Filter out segments where the text became empty after stripping and joining
    # (e.g., if a speaker's turn was only blank lines)
    segments = [(speaker, text) for speaker, text in segments if text]
    return segments


def generate_audio_segment_file(client: ElevenLabs, text: str, voice_id: str, 
                                temp_dir: Path, segment_idx: int) -> Path | None:
    """Generates an audio segment and saves it to a temporary file."""
    try:
        print(f"  Generating audio for segment {segment_idx+1}: \"{text[:60].replace('\n', ' ')}...\" with voice {voice_id}")
        if not text.strip():
            print("  Skipping empty text segment.")
            return None

        # ElevenLabs API call - using the current API method
        # The text_to_speech.convert method returns the audio bytes directly
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            voice_settings=VOICE_SETTINGS,
            model_id=MODEL_ID
        )
        
        # Save the audio to a temporary file
        temp_audio_path = temp_dir / f"segment_{segment_idx+1}.mp3"
        
        # Handle the response correctly - it could be bytes or a generator
        if hasattr(audio, 'read'):
            # It's a file-like object, read it
            audio_content = audio.read()
        elif isinstance(audio, bytes):
            # It's already bytes
            audio_content = audio
        else:
            # It might be a generator or stream, try to consume it
            try:
                if hasattr(audio, '__iter__') and not isinstance(audio, (str, bytes, bytearray)):
                    # It's an iterable, collect all chunks
                    audio_content = b''.join(chunk for chunk in audio)
                else:
                    # Unknown type, try to convert to bytes
                    audio_content = bytes(audio)
            except Exception as conversion_error:
                print(f"  Error converting audio response to bytes: {conversion_error}")
                return None
        
        # Write the audio content to file
        with open(temp_audio_path, "wb") as f:
            f.write(audio_content)
            
        return temp_audio_path
        
    except Exception as e:
        print(f"Error generating audio for text '{text[:30]}...': {e}")
        # Adding a small delay in case of rate limiting issues
        time.sleep(1)
        return None

# --- Main Processing Function ---
def process_script_to_mp3(client: ElevenLabs, script_file_path: Path, output_mp3_path: Path):
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

    # Create a unique temporary subdirectory for this script's audio snippets
    script_name_base = output_mp3_path.stem
    temp_script_audio_dir = PROCESSED_AUDIO_DIR / script_name_base
    temp_script_audio_dir.mkdir(parents=True, exist_ok=True)

    temp_audio_files = []
    all_segments_processed_successfully = True
    
    for i, (speaker, text) in enumerate(segments):
        if not text.strip():
            print(f"  Skipping empty text for speaker {speaker} at segment {i+1}")
            continue

        voice_id = HOST_VOICE_ID if speaker.upper() == "HOST" else GUEST_VOICE_ID
        
        temp_audio_file = generate_audio_segment_file(client, text, voice_id, temp_script_audio_dir, i)

        if temp_audio_file and temp_audio_file.exists():
            temp_audio_files.append(temp_audio_file) # Keep track for cleanup
        else:
            print(f"Failed to generate audio segment {i+1} for speaker {speaker}.")
            all_segments_processed_successfully = False
            break # Stop processing this script if a segment fails

    # If we have audio segments, combine them using ffmpeg directly
    if all_segments_processed_successfully and temp_audio_files:
        try:
            print(f"Combining audio segments into {output_mp3_path}...")
            output_mp3_path.parent.mkdir(parents=True, exist_ok=True) # Ensure Podcasts dir exists
            
            # Method depends on whether pydub is available
            if AudioSegment is not None:
                # Use pydub to combine audio
                combined_audio = AudioSegment.empty()
                for i, audio_file in enumerate(temp_audio_files):
                    segment = AudioSegment.from_mp3(audio_file)
                    combined_audio += segment
                    
                    # Add pause between segments (not after the last one)
                    if i < len(temp_audio_files) - 1:
                        pause = AudioSegment.silent(duration=PAUSE_BETWEEN_SEGMENTS_MS)
                        combined_audio += pause
                        
                combined_audio.export(output_mp3_path, format="mp3")
            else:
                # Use ffmpeg directly to concatenate files
                # Instead of using a concat file, we'll use the filter_complex method
                # which is more reliable with complex paths
                
                # Create a temporary directory for a simple numbered sequence of files
                # This avoids path issues with spaces and special characters
                numbered_temp_dir = temp_script_audio_dir / "numbered"
                numbered_temp_dir.mkdir(exist_ok=True)
                
                # Copy files to numbered sequence for simpler handling
                numbered_files = []
                for i, audio_file in enumerate(temp_audio_files):
                    dest_file = numbered_temp_dir / f"{i:03d}.mp3"
                    # Use shutil.copy2 to preserve metadata
                    import shutil
                    shutil.copy2(audio_file, dest_file)
                    numbered_files.append(dest_file)
                
                # Add these to cleanup list
                temp_audio_files.extend(numbered_files)
                
                # Create a simpler approach using the concat demuxer with a list file
                # This is more reliable for audio-only files
                concat_file = temp_script_audio_dir / "concat_list.txt"
                
                # Write the file list with proper escaping
                with open(concat_file, "w") as f:
                    for i, _ in enumerate(numbered_files):
                        # Use relative paths to avoid issues with spaces
                        rel_path = f"numbered/{i:03d}.mp3"
                        f.write(f"file '{rel_path}'\n")
                
                # Create the ffmpeg command using the concat demuxer
                ffmpeg_cmd = [
                    "/opt/homebrew/bin/ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    str(output_mp3_path)
                ]
                
                # Add the concat file to cleanup
                temp_audio_files.append(concat_file)
                
                # Run the command as a list of arguments, not as shell command
                # This avoids shell escaping issues
                print(f"Running ffmpeg command: {' '.join(str(x) for x in ffmpeg_cmd)}")
                # Change working directory to temp_script_audio_dir before running ffmpeg
                # This allows us to use relative paths in the concat file
                original_cwd = os.getcwd()
                os.chdir(temp_script_audio_dir)
                try:
                    subprocess.run(ffmpeg_cmd, check=True)
                finally:
                    # Change back to original directory
                    os.chdir(original_cwd)
                # Add numbered_temp_dir to cleanup list
                temp_audio_files.append(numbered_temp_dir)
                
            print(f"Successfully created podcast: {output_mp3_path}")
        except Exception as e:
            print(f"Error creating combined MP3 at {output_mp3_path}: {e}")
    elif not all_segments_processed_successfully:
        print(f"Podcast generation failed for {script_file_path.name} due to errors in segment processing.")
    else:
        print(f"No audio segments were generated for {script_file_path.name}. Output MP3 not created.")

    # Clean up temporary audio files and directory
    print(f"Cleaning up temporary files in {temp_script_audio_dir}...")
    for temp_file in temp_audio_files:
        try:
            if isinstance(temp_file, Path) and temp_file.exists():
                if temp_file.is_dir():
                    # If it's a directory, remove all files in it first
                    for file in temp_file.glob('*'):
                        try:
                            file.unlink()
                        except Exception as e:
                            print(f"Error deleting file {file}: {e}")
                    # Then try to remove the directory
                    temp_file.rmdir()
                else:
                    # It's a file, just remove it
                    temp_file.unlink()
        except Exception as e:
            print(f"Error deleting temporary file/directory {temp_file}: {e}")
    
    try:
        # Remove the temporary script-specific directory if it's empty
        if temp_script_audio_dir.exists() and not any(temp_script_audio_dir.iterdir()):
            temp_script_audio_dir.rmdir()
        # Optionally, remove the parent _ProcessedAudioSnippets if it becomes empty
        if PROCESSED_AUDIO_DIR.exists() and not any(PROCESSED_AUDIO_DIR.iterdir()):
             PROCESSED_AUDIO_DIR.rmdir()
    except Exception as e:
        print(f"Error cleaning up temporary directory {temp_script_audio_dir}: {e}")

# --- Main Orchestration ---
def main():
    api_key = os.getenv("ELEVEN_API_KEY")
    if not api_key:
        print("Error: ELEVEN_API_KEY environment variable not set. Please set it and try again.")
        return

    try:
        client = ElevenLabs(api_key=api_key)
    except Exception as e:
        print(f"Error initializing ElevenLabs client: {e}")
        return

    # Ensure required base directories exist
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    PODCASTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    skipped_count = 0
    error_count = 0

    print(f"\nStarting podcast generation process...")
    print(f"Scanning for podcast scripts in: {SUMMARIES_DIR}")
    print(f"Outputting MP3s to: {PODCASTS_DIR}")
    print(f"Using temporary snippet storage: {PROCESSED_AUDIO_DIR}")
    print("---")

    script_files = sorted(list(SUMMARIES_DIR.glob("podcast-script-*.md"))) # Process in order
    if not script_files:
        print("No podcast scripts found in the Summaries directory.")

    for script_file in script_files:
        match = re.search(r"podcast-script-(\d{4}-\d{2}-\d{2})\.md$", script_file.name)
        if match:
            date_str = match.group(1)
            output_mp3_filename = f"{date_str}.mp3"
            output_mp3_path = PODCASTS_DIR / output_mp3_filename

            print(f"\nChecking script: {script_file.name}")
            if output_mp3_path.exists():
                print(f"  Podcast already exists: {output_mp3_path}. Skipping.")
                skipped_count += 1
                continue
            
            print(f"  Found new script to process: {script_file.name}")
            try:
                process_script_to_mp3(client, script_file, output_mp3_path)
                # Check if file was actually created
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
    print("Finished.")

if __name__ == "__main__":
    main()
