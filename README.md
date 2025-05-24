# Teghrim's Crossing - Session Processing Pipeline

An automated pipeline for processing tabletop RPG session recordings into transcripts, summaries, narratives, podcasts, and Notion pages.

## Overview

This system-agnostic toolkit provides a complete workflow for processing tabletop RPG session recordings. While currently used for the "Teghrim's Crossing" Pathfinder 2e campaign, the tools work with any tabletop RPG system:

1. **Audio Transcription**: Convert session recordings to text transcripts with speaker diarization
2. **Transcript Slicing**: Break transcripts into overlapping chunks for processing
3. **Digest Compilation**: Create session digests and update campaign memory
4. **Content Generation**: Generate summaries, narratives, podcast scripts, and image prompts
5. **Notion Publishing**: Publish all outputs to a Notion database

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export OPENAI_API_KEY='your-openai-api-key'
export NOTION_API_KEY='your-notion-api-key'
export ELEVEN_API_KEY='your-elevenlabs-api-key'  # Optional, for audio transcription

# Run the complete pipeline
python process-sessions.py
```

## Directory Structure

- `/audio`: Raw audio recordings of sessions
- `/data`: Session data files (participants, locations, etc.)
- `/lib`: Core processing modules
- `/memory`: Campaign memory articles
- `/output`: Generated outputs (summaries, podcasts, images)
- `/prompts`: AI prompt templates
- `/references`: Campaign reference materials
- `/transcripts`: Processed transcripts
  - `/raw-transcripts`: Initial transcriptions
  - `/slices`: Chunked transcript segments
  - `/digests`: Compiled session digests

## Main Script

### `process-sessions.py`

The main orchestrator that runs the complete 5-step pipeline:

```bash
python process-sessions.py  # Runs all steps sequentially
```

Each step can be skipped based on environment variables or existing outputs.

## Pipeline Steps

### Step 1: Audio Transcription
- **Module**: `lib/audio_transcription.py`
- **Purpose**: Transcribes audio files using ElevenLabs API
- **Output**: Raw transcripts in `/transcripts/raw-transcripts/`
- **Note**: Skipped if `ELEVEN_API_KEY` not set

### Step 2: Transcript Slicing
- **Module**: `lib/transcript_slicing.py`
- **Purpose**: Breaks transcripts into overlapping chunks (30% overlap)
- **Output**: Sliced transcripts in `/transcripts/slices/`

### Step 3: Digest Compilation
- **Module**: `lib/digest_compilation.py`
- **Purpose**: Compiles slices into session digests
- **Features**: 
  - Entity detection and extraction
  - Memory article updates
  - Temporal consistency tracking
- **Output**: Session digests in `/transcripts/digests/`

### Step 4: Digest Processing
- **Module**: `lib/digest_processing.py`
- **Purpose**: Generates various content formats from digests
- **Outputs**:
  - Session summaries
  - Narrative versions
  - Podcast scripts
  - Key events for image generation
- **Templates**: Uses prompts from `/prompts/`

### Step 5: Notion Publishing
- **Module**: `lib/notion_publish.py`
- **Purpose**: Publishes all outputs to Notion
- **Features**:
  - Entity synchronization
  - Page creation and updates
  - Attachment handling

## Key Libraries

### Agent Tools
The system uses OpenAI's Agents SDK with custom function tools:

- **`lib/reference_utils.py`**: Access campaign reference materials
- **`lib/memory_tools.py`**: Query and update memory articles
- **`lib/notion_tools.py`**: Interact with Notion entity database

### Entity Management
- **`lib/notion_cache.py`**: Local cache for Notion entities
- **`lib/notion_utils.py`**: Notion API utilities
- Tracks: NPCs, Locations, Organizations, Items, etc.

### Context Management
- **`lib/context.py`**: SessionContext for temporal consistency
- Ensures memory queries are "as of" session date

## Requirements

- Python 3.7+
- See `requirements.txt` for Python dependencies

## Environment Variables

```bash
# Required for all AI processing
export OPENAI_API_KEY='your-openai-api-key'

# Required for Notion publishing
export NOTION_API_KEY='your-notion-api-key'

# Optional - for audio transcription (Step 1)
export ELEVEN_API_KEY='your-elevenlabs-api-key'
```

## Workflow

1. **Prepare Session Data**:
   - Place audio files in `/audio/YYYY-MM-DD/`
   - Create session info in `/data/YYYY-MM-DD.yaml`

2. **Run Pipeline**:
   ```bash
   python process-sessions.py
   ```

3. **Review Outputs**:
   - Transcripts in `/transcripts/`
   - Summaries in `/output/summaries/`
   - Published to Notion database

## Design Patterns

### Temporal Memory
The system maintains temporal consistency by:
- Tracking session dates via SessionContext
- Querying memory "as of" specific dates
- Preventing anachronisms in generated content

### Entity Cache
- All entity operations use local cache
- Minimizes Notion API calls
- Ensures consistency across pipeline

### Overlapping Slices
- 30% overlap between transcript chunks
- Maintains context across boundaries
- Improves summary quality

### Prompt Templates
- All AI prompts externalized in `/prompts/`
- Easy customization without code changes
- Consistent formatting across outputs

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
