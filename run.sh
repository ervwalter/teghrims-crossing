#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

python3 "process_audio.py"
python3 "transcript_agent.py"
python3 "create_podcasts.py"
python3 "create_docx.py"
