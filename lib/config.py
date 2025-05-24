"""
Project configuration and path management.
Provides centralized access to project directories.
"""

import os


def _find_project_root():
    """
    Find the project root by looking for characteristic top-level directories.
    This is robust to folder reorganizations.
    """
    current = os.path.dirname(os.path.abspath(__file__))
    
    # Top-level directories that should exist in the project root
    marker_dirs = {'audio', 'data', 'output', 'prompts', 'references'}
    
    while current != '/' and current != '':
        # Check if this directory contains our marker directories
        existing_dirs = set()
        if os.path.isdir(current):
            for item in os.listdir(current):
                item_path = os.path.join(current, item)
                if os.path.isdir(item_path) and item in marker_dirs:
                    existing_dirs.add(item)
        
        # If we find most of our marker directories, this is likely the project root
        if len(existing_dirs) >= 3:  # At least 3 of the 5 expected directories
            return current
            
        current = os.path.dirname(current)
    
    raise RuntimeError("Could not find project root - expected directories (audio, data, output, prompts, references) not found")


# Project paths - calculated once when module is imported
PROJECT_ROOT = _find_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
AUDIO_DIR = os.path.join(PROJECT_ROOT, "audio")
REFERENCES_DIR = os.path.join(PROJECT_ROOT, "references")
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")

# Specific data subdirectories
RAW_TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "raw-transcripts")
SLICES_DIR = os.path.join(DATA_DIR, "slices")
DIGESTS_DIR = os.path.join(DATA_DIR, "digests")

# Specific output subdirectories
SUMMARIES_DIR = os.path.join(OUTPUT_DIR, "summaries")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
PODCASTS_DIR = os.path.join(OUTPUT_DIR, "podcasts")

# Database path
CAMPAIGN_DB_PATH = os.path.join(DATA_DIR, "campaign-memory.db")


def ensure_directories():
    """Create all necessary directories if they don't exist."""
    directories = [
        DATA_DIR,
        OUTPUT_DIR,
        RAW_TRANSCRIPTS_DIR,
        SLICES_DIR,
        DIGESTS_DIR,
        SUMMARIES_DIR,
        IMAGES_DIR,
        PODCASTS_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Auto-create directories when module is imported
ensure_directories()