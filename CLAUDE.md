# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a tabletop RPG session processing toolkit that automates the workflow from audio recordings to multiple output formats (transcripts, summaries, narratives, podcasts, and Notion publishing). The system processes D&D sessions for the "Teghrim's Crossing" campaign.

## Key Commands

### Running the Main Pipeline
```bash
python process-sessions.py  # Runs the complete 5-step pipeline
```

### Environment Variables Required
- `ELEVEN_API_KEY` - ElevenLabs API for audio transcription (optional, skips Step 1 if not set)
- `OPENAI_API_KEY` - OpenAI API for text processing
- `NOTION_API_KEY` - Notion API for publishing results

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

The system follows a 5-step pipeline implemented in `process-sessions.py`:

1. **Audio Transcription** (`lib/audio_transcription.py`, `lib/transcript_compilation.py`)
   - Converts audio files from `/audio` to transcripts in `/transcripts/raw-transcripts/`
   - Uses ElevenLabs API with speaker diarization

2. **Transcript Slicing** (`lib/transcript_slicing.py`, `lib/slice_summarization.py`)
   - Breaks transcripts into overlapping chunks in `/transcripts/slices/`
   - Summarizes each slice with OpenAI API

3. **Digest Compilation** (`lib/digest_compilation.py`)
   - Combines slice summaries into session digests in `/transcripts/digests/`
   - Updates memory articles based on entity detection

4. **Digest Processing** (`lib/digest_processing.py`)
   - Processes digests with prompts from `/prompts/` to generate:
     - Session summaries
     - Narrative versions
     - Podcast scripts
     - Key events for images
   - Outputs saved to `/output/summaries/`

5. **Notion Publishing** (`lib/notion_publish.py`, `lib/notion_tools.py`)
   - Publishes outputs to Notion database
   - Manages entity cache and synchronization

## Key Libraries and Modules

- **Agent Tools**: Uses OpenAI Agents SDK with custom function tools
  - `lib/reference_utils.py` - Access to campaign reference materials
  - `lib/memory_tools.py` - Memory article management
  - `lib/notion_tools.py` - Entity database operations
  
- **Entity Management**: 
  - `lib/notion_cache.py` - Local cache for Notion entities
  - Tracks NPCs, locations, organizations, etc.

- **Context Management**: 
  - `lib/context.py` - SessionContext class for tracking current session date
  - Essential for temporal consistency in memory queries

## Important Design Patterns

1. **Temporal Memory**: The system maintains temporal consistency by tracking session dates and querying memory "as of" specific dates to avoid anachronisms.

2. **Entity Cache**: All entity operations go through a local cache that syncs with Notion to minimize API calls and ensure consistency.

3. **Overlapping Slices**: Transcript slicing uses 30% overlap to maintain context across chunk boundaries.

4. **Prompt Templates**: All AI prompts are externalized in `/prompts/` directory for easy modification.

## Critical Files to Understand

- `process-sessions.py` - Main orchestrator
- `lib/digest_compilation.py` - Contains entity detection and memory update logic
- `lib/notion_cache.py` - Entity caching and synchronization
- `prompts/` - All AI prompt templates