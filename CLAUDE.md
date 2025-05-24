# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a tabletop RPG session processing toolkit that automates the workflow from audio recordings to multiple output formats (transcripts, summaries, narratives, podcasts, and Notion publishing). The system processes D&D sessions for the "Teghrim's Crossing" campaign.

## Key Commands

### Running the Main Pipeline
```bash
python process-sessions.py                    # Runs the complete 5-step pipeline
python process-sessions.py --help            # Show all available options
python process-sessions.py --fix-spelling    # Fix entity name spellings in existing outputs
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

### Code Organization
The `lib/` directory is organized by functionality:
- `lib/audio/` - Audio transcription and compilation
- `lib/content/` - Content processing and generation
- `lib/memory/` - Campaign memory and reference management  
- `lib/notion/` - Notion integration and publishing
- `lib/config.py` - **Centralized path configuration** (CRITICAL)

### Pipeline Steps
The system follows a 5-step pipeline implemented in `process-sessions.py`:

1. **Audio Transcription** (`lib/audio/transcription.py`, `lib/audio/compilation.py`)
   - Converts audio files from `/audio` to transcripts in `/transcripts/raw-transcripts/`
   - Uses ElevenLabs API with speaker diarization

2. **Transcript Slicing** (`lib/audio/slicing.py`, `lib/audio/slice_summarization.py`)
   - Breaks transcripts into overlapping chunks in `/transcripts/slices/`
   - Summarizes each slice with OpenAI API

3. **Digest Compilation** (`lib/content/session_digest.py`)
   - Combines slice summaries into session digests in `/transcripts/digests/`
   - Updates memory articles based on entity detection

4. **Content Generation** (`lib/content/digest_processing.py`)
   - Processes digests with prompts from `/prompts/` to generate:
     - Session summaries
     - Narrative versions  
     - Podcast scripts
     - Key events for images
   - Additional modules: `image_generation.py`, `podcast_generation.py`
   - Outputs saved to `/output/summaries/`, `/output/images/`, `/output/podcasts/`

5. **Notion Publishing** (`lib/notion/publish.py`, `lib/notion/tools.py`)
   - Publishes outputs to Notion database
   - Manages entity cache and synchronization

## Key Libraries and Modules

- **Core Configuration** (CRITICAL):
  - `lib/config.py` - **USE THIS FOR ALL PATH OPERATIONS**
  - Automatically detects project root using marker directories
  - Provides constants: `PROJECT_ROOT`, `AUDIO_DIR`, `DATA_DIR`, `SUMMARIES_DIR`, etc.
  - Eliminates fragile `dirname()` chains - NEVER use relative path calculations

- **Agent Tools**: Uses OpenAI Agents SDK with custom function tools
  - `lib/memory/references.py` - Access to campaign reference materials
  - `lib/memory/tools.py` - Memory article management
  - `lib/notion/tools.py` - Entity database operations
  
- **Entity Management**: 
  - `lib/notion/cache.py` - Local cache for Notion entities
  - `lib/notion/utils.py` - Notion API utilities
  - Tracks NPCs, locations, organizations, etc.

- **Context Management**: 
  - `lib/memory/context.py` - SessionContext class for tracking current session date
  - Essential for temporal consistency in memory queries
  
- **Content Processing**:
  - `lib/content/spelling_correction.py` - Conservative entity name spelling fixes
  - `lib/content/image_generation.py` - AI artwork generation  
  - `lib/content/podcast_generation.py` - Text-to-speech podcast creation

## Important Design Patterns

1. **Centralized Path Management** (CRITICAL): 
   - ALWAYS import paths from `lib.config` - never use `dirname()` chains
   - The config module finds project root by detecting marker directories
   - Future-proof against code reorganization
   - Example: `from lib.config import SUMMARIES_DIR, DIGESTS_DIR`

2. **Temporal Memory**: The system maintains temporal consistency by tracking session dates and querying memory "as of" specific dates to avoid anachronisms.

3. **Entity Cache**: All entity operations go through a local cache that syncs with Notion to minimize API calls and ensure consistency.

4. **Conservative Text Processing**: 
   - Spelling correction only fixes entity names, preserves all other content
   - Uses Agent SDK with entity database for accuracy
   - Never rewrites or improves text beyond the specific task

5. **Overlapping Slices**: Transcript slicing uses 30% overlap to maintain context across chunk boundaries.

6. **Modular Architecture**: Code organized by single responsibility principle
   - `audio/` - Audio processing only
   - `content/` - Content generation only
   - `memory/` - Memory and reference management only
   - `notion/` - Notion integration only

7. **Prompt Templates**: All AI prompts are externalized in `/prompts/` directory for easy modification.

## Critical Files to Understand

- `process-sessions.py` - Main orchestrator with command-line options
- `lib/config.py` - **MOST CRITICAL** - Centralized path management
- `lib/content/session_digest.py` - Entity detection and memory update logic
- `lib/notion/cache.py` - Entity caching and synchronization
- `lib/content/spelling_correction.py` - Conservative entity name fixing
- `prompts/` - All AI prompt templates

## Path Management Rules (CRITICAL)

1. **NEVER** use `os.path.dirname(__file__)` chains - they are fragile
2. **ALWAYS** import from `lib.config` for paths:
   ```python
   from lib.config import SUMMARIES_DIR, PROJECT_ROOT, DIGESTS_DIR
   ```
3. The config module automatically finds the project root
4. All critical paths are provided as constants
5. This pattern prevents breakage during code reorganization

## Special Features

- **--fix-spelling mode**: Corrects entity name spellings in existing outputs using conservative approach
- **Spelling correction**: Only fixes entity names, preserves all other content integrity
- **Robust path detection**: Uses marker directories to find project root reliably