#!/usr/bin/env python
"""
Transcribe audio files using the ElevenLabs Speech-to-Text API with speaker diarization.
Outputs a nicely formatted markdown file with speaker turns.

Usage:
    python process_audio.py          # Process all unprocessed sessions

Environment Variables:
    ELEVEN_API_KEY: Your ElevenLabs API key
    OPENAI_API_KEY: Your OpenAI API key (required for slice processing and combining)
"""

import os
import sys
import argparse
from lib.audio_transcription import transcribe_audio
from lib.transcript_compilation import auto_process_sessions
from lib.slice_summarization import process_all_transcripts_to_slices
from lib.digest_compilation import process_all_sessions_to_digests


def main():
    # Get API keys from environment variables
    eleven_api_key = os.environ.get("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("Error: ELEVEN_API_KEY environment variable not set")
        sys.exit(1)
    
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process audio files to generate transcripts, slice them, and combine into session bibles.")
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for API calls (default: 300)')
    parser.add_argument('--retries', type=int, default=2, help='Maximum number of retry attempts for API calls (default: 2)')
    args = parser.parse_args()
    
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "audio")
    transcripts_dir = os.path.join(base_dir, "transcripts")
    
    try:
        # Step 1: Process audio files into transcripts
        print("Step 1: Processing audio files into transcripts...")
        auto_process_sessions(eleven_api_key, False, args.timeout, args.retries)
        print("\nAudio processing complete!\n")
        
        # Step 2: Process transcripts into slices
        print("Step 2: Processing transcripts into slices...")
        process_all_transcripts_to_slices(openai_api_key)
        print("\nSlice processing complete!\n")
        
        # Step 3: Combine slices into session digests
        print("Step 3: Creating session digests from slices...")
        process_all_sessions_to_digests(openai_api_key)
        print("\nSession digest creation complete!\n")
        
        print("All processing complete!")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error during processing: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
