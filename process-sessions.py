#!/usr/bin/env python
"""
Transcribe audio files using the ElevenLabs Speech-to-Text API with speaker diarization.
Outputs a nicely formatted markdown file with speaker turns.

Usage:
    python process_audio.py          # Process all unprocessed sessions

Environment Variables:
    ELEVEN_API_KEY: Your ElevenLabs API key
    OPENAI_API_KEY: Your OpenAI API key (required for slice processing and combining)
    NOTION_API_KEY: Your Notion API key (required for publishing to Notion)
"""

import os
import sys
import argparse
from lib.audio.transcription import transcribe_audio
from lib.audio.compilation import auto_process_sessions
from lib.audio.summarization import process_all_transcripts_to_slices
from lib.content.session_digest import process_all_sessions_to_digests
from lib.content.digest_processing import process_all_digests
from lib.content.image_generation import process_all_images
from lib.content.podcast_generation import process_all_podcasts
from lib.notion.publish import publish_session_outputs
from lib.notion.cache import initialize_cache, sync_to_notion


def main():
    """Main entry point."""
    # Parse command line arguments first (so --help works without initialization)
    parser = argparse.ArgumentParser(description="Process audio files to generate transcripts, slice them, and combine into session bibles.")
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for API calls (default: 300)')
    parser.add_argument('--retries', type=int, default=2, help='Maximum number of retry attempts for API calls (default: 2)')
    args = parser.parse_args()
    
    # Get API keys from environment variables (after parsing args so --help works)
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
        
    notion_api_key = os.environ.get("NOTION_API_KEY")
    if not notion_api_key:
        print("Error: NOTION_API_KEY environment variable not set")
        sys.exit(1)
        
    eleven_api_key = os.environ.get("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("Warning: ELEVEN_API_KEY environment variable not set. Audio transcription will be skipped.")
        eleven_api_key = None
        
    try:
        # Initialize notion cache
        print("\nInitializing Notion cache...")
        initialize_cache()
    except Exception as e:
        print(f"Error initializing Notion cache: {e}")
        sys.exit(1)
    
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "audio")
    transcripts_dir = os.path.join(base_dir, "data")
    
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
        
        # Step 4: Process session digests with agent prompts
        print("Step 4: Processing session digests with agent prompts...")
        process_all_digests(openai_api_key)
        print("\nSession digest processing complete!\n")
        
        # Step 5: Generate images from image prompts
        print("Step 5: Generating images from image prompts...")
        process_all_images(openai_api_key)
        print("\nImage generation complete!\n")
        
        # Step 6: Generate podcasts from podcast scripts
        print("Step 6: Generating podcasts from podcast scripts...")
        process_all_podcasts(eleven_api_key)
        print("\nPodcast generation complete!\n")
        
        # Step 7: Publish session outputs to Notion
        print("Step 7: Publishing session outputs to Notion...")
        publish_session_outputs(base_dir)
        print("\nNotion publishing complete!\n")
        
        # Notion cache is now synced immediately after digest creation
        # to ensure entity updates are persisted even if later steps are interrupted
        
        print("All processing complete!")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error during processing: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
