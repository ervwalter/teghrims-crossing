# Step 4 Implementation Plan: Process Session Digests with Agent SDK

This document outlines the plan for implementing Step 4 in the `process-sessions.py` script, which will process session digests created in Step 3 using the agent SDK with various prompts.

## Overview

Step 4 will:
1. Identify all session digests created in Step 3
2. For each digest, process it with multiple agent prompts to generate different outputs
3. Save the results to the appropriate subdirectories in the `output` folder
4. Use the memory tools to maintain continuity between sessions

## Available Resources

- **Prompts**: Located in `prompts/` directory:
  - `session-summary.md`: Creates a summary of the session
  - `session-narrative.md`: Creates a narrative version of the session
  - `podcast-script.md`: Creates a podcast script of the session
  - `image-key-events.md`: Identifies key events for potential image generation

- **Tools**:
  - Reference utilities (`lib/reference_utils.py`): 
    - `list_reference_files()`: Lists available reference files
    - `retrieve_reference_files()`: Retrieves content of specified reference files
    - `get_player_roster()`: Gets player roster information
  
  - Memory tools (`lib/memory_tools.py`):
    - `list_articles()`: Lists available memory articles
    - `get_articles()`: Retrieves memory articles as they existed at a specific date
    - `update_article()`: Updates memory articles with new content

- **Output Directories**:
  - `output/summaries/`: For session summaries
  - `output/podcasts/`: For podcast scripts
  - `output/images/`: For image descriptions
  - `output/codex/`: For other potential outputs

## Implementation Steps

### 1. Create Module Structure

Create a new module `lib/digest_processing.py` that will contain the functions for Step 4.

### 2. Implement Core Functions

#### 2.1 Find Digests Function

```python
def get_session_digests():
    """
    Get all available session digests.
    
    Returns:
        List of dictionaries containing session date and path to the digest file
    """
    # Scan the digests directory for all digest files
    # Parse session dates from filenames
    # Return sorted list of sessions with their digest paths
```

#### 2.2 Process Single Digest Function

```python
def process_digest_with_prompt(digest_path, session_date, prompt_name, openai_api_key, previous_output=None):
    """
    Process a single digest with a specific prompt using the agent SDK.
    
    Args:
        digest_path: Path to the digest file
        session_date: Date of the session (YYYY-MM-DD)
        prompt_name: Name of the prompt to use (without extension)
        openai_api_key: OpenAI API key
        previous_output: Path to previous output of the same type (optional)
        
    Returns:
        Generated content from the agent
    """
    # Load digest content
    # Set up agent with appropriate tools from reference_utils and memory_tools
    # Load prompt from prompts directory
    # If previous_output is provided, load it to give context to the agent
    # Run agent with the prompt, digest content, and previous output
    # Return generated content
```

#### 2.3 Get Previous Output Function

```python
def get_previous_output(session_date, output_type):
    """
    Get the most recent previous output of the specified type.
    
    Args:
        session_date: Date of the current session (YYYY-MM-DD)
        output_type: Type of output (summary, narrative, podcast, etc.)
        
    Returns:
        Path to the previous output file, or None if not found
    """
    # Get all output files of the specified type
    # Find the most recent one before the current session_date
    # Return the path to the file, or None if not found
```

#### 2.4 Save Output Function

```python
def save_output(content, session_date, output_type):
    """
    Save generated content to the appropriate output directory.
    
    Args:
        content: Generated content to save
        session_date: Date of the session (YYYY-MM-DD)
        output_type: Type of output (summary, narrative, podcast, etc.)
        
    Returns:
        Path to the saved file
    """
    # Determine output directory based on output_type
    # Create path with appropriate filename
    # Write content to file
    # Return path to saved file
```

#### 2.5 Main Processing Function

```python
def process_digest(digest_path, session_date, openai_api_key):
    """
    Process a digest with all available prompts.
    
    Args:
        digest_path: Path to the digest file
        session_date: Date of the session (YYYY-MM-DD)
        openai_api_key: OpenAI API key
        
    Returns:
        Dictionary of output paths by type
    """
    # Initialize results dictionary
    # Process with session-summary prompt
    # Process with session-narrative prompt
    # Process with podcast-script prompt
    # Process with image-key-events prompt
    # Return dictionary of results
```

#### 2.6 Process All Digests Function

```python
def process_all_digests(openai_api_key):
    """
    Process all available session digests with all prompts.
    
    Args:
        openai_api_key: OpenAI API key
    """
    # Get all session digests
    # For each digest:
    #   For each prompt type:
    #     Check if output already exists for this digest and prompt
    #     If output doesn't exist, process the digest with this prompt
    #     Skip if output already exists
    #   Print progress
```

### 3. Integrate into process-sessions.py

Add the Step 4 processing to the main script:

```python
# Step 4: Process session digests with agent prompts
print("Step 4: Processing session digests with agent prompts...")
process_all_digests(openai_api_key)
print("\nSession digest processing complete!\n")
```

### 4. Enhance Agent Prompting

For each prompt type:

1. Prepare a system prompt that includes:
   - The base prompt from the prompt file
   - Instructions to use the tools for accessing references and memory
   - Instructions on format and file structure
   
2. Prepare a user prompt that includes:
   - The digest content
   - Previous output context (if available)
   - Any specific instructions for this run

### 5. Ensure Proper Memory Access

When processing each digest:

1. Always provide the session date to the agent in the prompt
2. This allows the agent to query memory as it existed before the current session
3. Memory updates are already handled in the digest compilation phase, so no additional updates are needed

## Testing Strategy

1. Test with a single digest first
2. Verify outputs are correctly formatted and stored
3. Check if memory tools are working correctly
4. Process multiple digests to ensure continuity
5. Verify the entire pipeline works end-to-end

## Code Architecture

```
process-sessions.py
    - Main script that calls all steps

lib/digest_processing.py
    - Functions for processing digests with agent SDK

prompts/
    - Contains prompt templates

output/
    - Contains output directories for each type
    - summaries/
    - narratives/
    - podcasts/
    - images/
    - codex/
```

## Error Handling

- Handle API errors with retries
- Skip already processed sessions
- Log all errors for debugging
- Ensure memory consistency even if processing fails

This plan provides a comprehensive guide for implementing Step 4 in the process-sessions.py script. It focuses on modularity, reusability, and maintainability of the code.
