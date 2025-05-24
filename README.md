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
- `/lib`: Core processing modules (organized by functionality)
  - `/audio`: Audio transcription and compilation
  - `/content`: Content processing and generation
  - `/memory`: Campaign memory and reference management
  - `/notion`: Notion integration and publishing
  - `config.py`: Centralized path configuration
- `/output`: Generated outputs
  - `/summaries`: Session summaries, narratives, podcast scripts
  - `/images`: Generated artwork and metadata
  - `/podcasts`: Generated MP3 podcasts
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
python process-sessions.py                    # Runs all steps sequentially
python process-sessions.py --help            # Show all available options
python process-sessions.py --fix-spelling    # Fix entity name spellings in existing outputs
```

**Available Options:**
- `--fix-spelling`: Corrects entity name spellings in existing output files using the campaign entity database
- Each step can be skipped based on environment variables or existing outputs

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

### Core Configuration
- **`lib/config.py`**: Centralized path management and project root detection
  - Automatically finds project root using marker directories
  - Provides all critical paths as constants
  - Eliminates fragile relative path calculations

### Agent Tools
The system uses OpenAI's Agents SDK with custom function tools:

- **`lib/memory/references.py`**: Access campaign reference materials
- **`lib/memory/tools.py`**: Query and update memory articles
- **`lib/notion/tools.py`**: Interact with Notion entity database

### Entity Management
- **`lib/notion/cache.py`**: Local cache for Notion entities
- **`lib/notion/utils.py`**: Notion API utilities
- Tracks: NPCs, Locations, Organizations, Items, etc.

### Context Management
- **`lib/memory/context.py`**: SessionContext for temporal consistency
- Ensures memory queries are "as of" session date

### Content Generation
- **`lib/content/`**: Organized content processing modules
  - `digest_processing.py`: Multi-format content generation
  - `image_generation.py`: AI artwork creation
  - `podcast_generation.py`: Text-to-speech podcast creation
  - `spelling_correction.py`: Entity name consistency

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
   - Images in `/output/images/`
   - Podcasts in `/output/podcasts/`
   - Published to Notion database

4. **Optional Maintenance**:
   ```bash
   # Fix entity name spellings across all outputs
   python process-sessions.py --fix-spelling
   ```

## Design Patterns

### Centralized Configuration
- **Robust Path Management**: Uses marker directory detection to find project root
- **Single Source of Truth**: All paths defined in `lib/config.py`
- **Future-Proof**: Won't break with code reorganization

### Temporal Memory
The system maintains temporal consistency by:
- Tracking session dates via SessionContext
- Querying memory "as of" specific dates
- Preventing anachronisms in generated content

### Entity Cache
- All entity operations use local cache
- Minimizes Notion API calls
- Ensures consistency across pipeline
- Conservative spelling correction preserves content integrity

### Overlapping Slices
- 30% overlap between transcript chunks
- Maintains context across boundaries
- Improves summary quality

### Modular Architecture
- **Single Responsibility**: Each module has a clear, focused purpose
- **Logical Organization**: Code grouped by functionality (audio, content, memory, notion)
- **Tool-Based Processing**: Leverages OpenAI Agents SDK for consistent, reliable AI operations

### Prompt Templates
- All AI prompts externalized in `/prompts/`
- Easy customization without code changes
- Consistent formatting across outputs

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
