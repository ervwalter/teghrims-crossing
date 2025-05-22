"""
Publish session summaries to Notion.
This module handles uploading session summaries to a Notion database,
keeping them in sync with local markdown files.
"""
import os
import glob
from datetime import datetime, date, timezone
import re
from typing import Dict, Optional

from lib.memory_tools import list_articles_meta, latest_revision_for_date

from lib.notion_utils import (
    ensure_database_schema,
    create_or_update_database_entry
)

# Database IDs
SESSION_SUMMARIES_DB = "1f97b6a98078808094a5fd9f7558afd1"
ARTICLES_DB = "1fa7b6a98078809ebf8dfd349b8bc92a"
SESSION_NARRATIVES_DB = "1fb7b6a9807880f98d29ce1cf89c1e17"

def parse_session_summary(file_path: str) -> dict:
    """
    Parse a session summary markdown file to extract title and overview.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        dict with 'title' and 'overview' keys
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title from first heading
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        # Remove any markdown formatting (bold, italics)
        title = re.sub(r'[\*_]', '', title_match.group(1).strip())
    else:
        title = "Untitled Session"
    
    # Split content into sections and find overview
    sections = content.split('##')
    overview = ""
    for section in sections:
        if 'Session Overview' in section:
            # Remove the section title and any extra whitespace
            lines = section.split('\n')
            # Skip the title line and any empty lines
            content_lines = [line for line in lines[1:] if line.strip()]
            if content_lines:
                overview = content_lines[0]
                break
    
    return {
        'title': title,
        'overview': overview
    }

def publish_session_summaries(base_dir: str) -> None:
    """
    Publish all session summaries to Notion, updating only if local content is newer.
    
    Args:
        base_dir: Base directory containing the output/summaries folder
    """
    # Ensure database has required properties
    schema = {
        "Title": {"title": {}},
        "Date": {"date": {}},
        "Overview": {"rich_text": {}}
    }
    ensure_database_schema(SESSION_SUMMARIES_DB, schema)
    
    # Find all session summary files
    summaries_dir = os.path.join(base_dir, "output", "summaries")
    pattern = os.path.join(summaries_dir, "session-summary.*.md")
    
    for file_path in glob.glob(pattern):
        # Extract date from filename
        date_match = re.search(r'session-summary\.(\d{4}-\d{2}-\d{2})\.md$', file_path)
        if not date_match:
            print(f"Skipping {file_path} - invalid filename format")
            continue
        
        session_date = date_match.group(1)
        print(f"\nProcessing summary for {session_date}...")
        
        try:
            # Parse the summary file
            summary_data = parse_session_summary(file_path)
            
            # Get file's modification time
            local_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).replace(tzinfo=timezone.utc)
            
            # Create properties for Notion entry
            properties = {
                "Title": {
                    "title": [{
                        "text": {
                            "content": summary_data['title']
                        }
                    }]
                },
                "Date": {
                    "date": {
                        "start": session_date
                    }
                },
                "Overview": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": summary_data['overview'][:2000]  # Notion has a 2000 char limit
                        }
                    }]
                }
            }
            

            
            # Read full content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create/update the entry
            result = create_or_update_database_entry(
                database_id=SESSION_SUMMARIES_DB,
                properties=properties,
                content=content,
                unique_property=("Date", session_date, "date"),  # Specify date property type
                local_modified_time=local_modified_time
            )
            
            if "error" in result:
                print(f"❌ Error publishing {session_date}: {result['error']}")
            else:
                print(f"✅ Successfully published/updated {session_date}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()

def publish_articles() -> None:
    """
    Publish all articles to Notion.
    This includes character info, locations, lore, etc.
    """
    # Ensure database has correct schema
    schema = {
        "Title": {"title": {}},
        "Description": {"rich_text": {}},
        "Slug": {"rich_text": {}}
    }
    ensure_database_schema(ARTICLES_DB, schema)
    
    # Get list of all articles
    articles = list_articles_meta()
    
    # Get current date for latest revisions
    today = date.today()
    
    # Process each article
    for article in articles:
        print(f"\nProcessing article {article['slug']}...")
        
        # Get latest revision
        content, timestamp = latest_revision_for_date(article['slug'], today)
        if content is None:
            print(f"No content found for {article['slug']}, skipping")
            continue
        
        # Create properties
        properties = {
            "Title": {
                "title": [{
                    "text": {
                        "content": article['title']
                    }
                }]
            },
            "Description": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": article['description'] or ""
                    }
                }]
            },
            "Slug": {
                "rich_text": [{
                    "type": "text",
                    "text": {
                        "content": article['slug']
                    }
                }]
            }
        }
        
        # Create or update entry
        result = create_or_update_database_entry(
            database_id=ARTICLES_DB,
            properties=properties,
            content=content,
            unique_property=("Slug", article['slug'], "rich_text"),
            local_modified_time=datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)
        )
        
        if result:
            print(f"✅ Successfully published/updated {article['slug']}")


def parse_session_narrative(file_path: str) -> dict:
    """
    Parse a session narrative markdown file to extract title.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        dict with 'title' key
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title from first heading
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        # Remove any markdown formatting (bold, italics)
        title = re.sub(r'[\*_]', '', title_match.group(1).strip())
    else:
        title = "Untitled Session"
    
    return {
        'title': title,
        'content': content
    }


def publish_session_narratives(base_dir: str) -> None:
    """
    Publish all session narratives to Notion.
    
    Args:
        base_dir: Base directory containing the output/summaries folder
    """
    # Ensure database has correct schema
    schema = {
        "Title": {"title": {}},
        "Chapter": {"number": {}},
        "Date": {"date": {}}
    }
    ensure_database_schema(SESSION_NARRATIVES_DB, schema)
    
    # Find all session narrative files
    narrative_dir = os.path.join(base_dir, "output", "summaries")
    pattern = os.path.join(narrative_dir, "session-narrative.*.md")
    narrative_files = glob.glob(pattern)
    
    # Sort by date to assign chapter numbers
    narrative_files.sort()
    
    # Process each narrative
    for chapter, file_path in enumerate(narrative_files, start=1):
        print(f"\nProcessing narrative {os.path.basename(file_path)}...")
        
        try:
            # Extract date from filename
            date_match = re.search(r'session-narrative\.(\d{4}-\d{2}-\d{2})\.md$', file_path)
            if not date_match:
                print(f"❌ Invalid filename format: {file_path}")
                continue
            
            session_date = date_match.group(1)
            
            # Parse narrative
            narrative_data = parse_session_narrative(file_path)
            
            # Get file's modification time
            local_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).replace(tzinfo=timezone.utc)
            
            # Create properties for Notion entry
            properties = {
                "Title": {
                    "title": [{
                        "text": {
                            "content": narrative_data['title']
                        }
                    }]
                },
                "Chapter": {
                    "number": chapter
                },
                "Date": {
                    "date": {
                        "start": session_date
                    }
                }
            }
            
            # Create or update entry
            result = create_or_update_database_entry(
                database_id=SESSION_NARRATIVES_DB,
                properties=properties,
                content=narrative_data['content'],
                unique_property=("Date", session_date, "date"),
                local_modified_time=local_modified_time
            )
            
            if result:
                print(f"✅ Successfully published/updated {session_date}")
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()


def publish_session_outputs(base_dir: str) -> None:
    """
    Publish all session outputs to Notion.
    This includes summaries, references, and other generated content.
    
    Args:
        base_dir: Base directory containing the output folder
    """
    # Publish session summaries
    publish_session_summaries(base_dir)
    
    # Publish articles
    publish_articles()
    
    # Publish session narratives
    publish_session_narratives(base_dir)


def main():
    """Main entry point when run as a script."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    publish_session_outputs(base_dir)


if __name__ == "__main__":
    main()
