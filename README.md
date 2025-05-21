# Teghrim's Crossing - Session Processing Tools

A collection of Python scripts for processing tabletop RPG session recordings into various formats including transcripts, summaries, narratives, and podcasts.

## Overview

This toolkit helps manage and transform recordings from tabletop RPG sessions (like D&D) into different formats:

1. **Audio Transcription**: Convert session recordings to text transcripts with speaker diarization
2. **AI-Assisted Summaries**: Generate session summaries and narrative versions using AI
3. **Podcast Creation**: Transform session content into podcast format with voice synthesis
4. **Document Publishing**: Compile summaries and narratives into formatted DOCX files

## Directory Structure

- `/audio`: Raw audio recordings of sessions (organized by date)
- `/transcripts`: Transcribed text from audio recordings
- `/Summaries`: Generated summaries, narratives, and podcast scripts
- `/Podcasts`: Generated podcast audio files
- `/references`: Reference materials for the campaign
- `/memory`: Campaign memory database and information
- `/Prompts`: AI prompts for generating different types of content
- `/Images`: Generated or stored images related to sessions

## Scripts

### `process_audio.py`

Transcribes audio recordings using ElevenLabs Speech-to-Text API with speaker diarization.

```
Usage:
  python process_audio.py                      # Auto mode: processes all unprocessed sessions
  python process_audio.py --single <audio_file> # Process a single file
```

### `transcript_agent.py`

Uses OpenAI's Agents SDK to process transcripts and generate summaries, narratives, and other content.

```
Usage:
  python transcript_agent.py
```

### `create_podcasts.py`

Converts podcast scripts into audio files using ElevenLabs text-to-speech API.

```
Usage:
  python create_podcasts.py
```

### `create_docx.py`

Combines markdown files from the Summaries folder and converts them to DOCX format.

```
Usage:
  python create_docx.py
```

## Requirements

- Python 3.7+
- Pandoc (for DOCX conversion)
- FFmpeg (for audio processing)

## Python Dependencies

- elevenlabs
- openai
- pydub
- agents (OpenAI Agents SDK)
- yaml
- pathlib

## Environment Setup

1. Set up required environment variables:
   ```
   # Required for process_audio.py and create_podcasts.py
   export ELEVEN_API_KEY='your-elevenlabs-api-key'
   
   # Required for transcript_agent.py
   export OPENAI_API_KEY='your-openai-api-key'
   export OPENAI_ORG_ID='your-openai-organization-id'
   ```

2. Install Python dependencies:
   ```
   pip install elevenlabs openai pydub pyyaml
   ```

3. Install external dependencies:
   ```
   # macOS
   brew install pandoc ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install pandoc ffmpeg
   ```

## Workflow

1. Record your tabletop RPG session
2. Place audio files in the `/audio` directory with naming format: `YYMMDD_####.mp3`
3. Run `process_audio.py` to transcribe audio to text
4. Run `transcript_agent.py` to generate summaries and other content
5. Run `create_podcasts.py` to generate podcast audio from scripts
6. Run `create_docx.py` to compile summaries/narratives into documents

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
