"""
Notion integration utilities for Teghrim's Crossing project.
This module provides functions to interact with Notion API for creating pages,
uploading markdown content, and managing database entries for session summaries
and name references.
"""
import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any, Tuple

# Official API client
from notion_client import Client

# Local module for Markdown to Notion conversion
from lib.markdown_to_notion import markdown_to_notion_blocks, rich_text_from_markdown

# Environment variables for Notion API
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")

# Latest Notion API version as of 2024-12-20
NOTION_VERSION = "2024-12-20"

def get_notion_client() -> Client:
    """
    Initialize and return a Notion client using the official API.
    Raises an exception if the API key is not set.
    """
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY environment variable is not set.")
    
    return Client(auth=NOTION_API_KEY)

# -------------------- Page Management Functions --------------------

def create_page(parent_id: str, title: str, content: Optional[str] = None, source_file: Optional[str] = None) -> Dict:
    """
    Create a new page in Notion.
    
    Args:
        parent_id: ID of the parent page or database
        title: Title of the new page
        content: Optional markdown content for the page
        source_file: Optional source file name to use as a unique identifier
        
    Returns:
        Dict containing the new page data or error information
    """
    notion = get_notion_client()
    
    # Determine if parent_id is a database or page
    parent_type = "database_id" if parent_id.startswith("database_") else "page_id"
    
    # Basic page creation payload
    payload = {
        "parent": {parent_type: parent_id},
        "properties": {}
    }
    
    # Set title based on parent type
    if parent_type == "page_id":
        payload["properties"]["title"] = {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    else:
        # For database parent, assume "Name" is the title field
        # This may need adjustment based on the actual database schema
        payload["properties"]["Name"] = {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    
    # Create the page
    response = notion.pages.create(**payload)
    page_id = response.get("id")
    
    if page_id:
        # If we have a source file, add it as a callout block at the top
        if source_file:
            notion.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": f"Source: {source_file}"}
                            }],
                            "icon": {"emoji": "📄"}
                        }
                    }
                ]
            )
        
        # If content was provided, add it after the source file block
        if content:
            add_content_to_page(page_id, content)
    
    return response

def delete_page(page_id: str) -> Dict:
    """
    Archive (delete) a page in Notion.
    Note: Notion API doesn't fully delete pages, it places them in trash.
    
    Args:
        page_id: ID of the page to archive
        
    Returns:
        Dict containing response data or error information
    """
    notion = get_notion_client()
    
    # Update page to place it in trash
    return notion.pages.update(page_id=page_id, in_trash=True)

# -------------------- Markdown Conversion Functions --------------------

def add_content_to_page(page_id: str, content: str, append_only: bool = False) -> Dict:
    """
    Add content blocks to an existing Notion page.
    By default, replaces all existing content. Use append_only=True to append instead.
    Converts markdown to Notion blocks using our AST-based converter.
    
    Args:
        page_id: ID of the page to update
        content: Markdown content to convert and add
        append_only: If True, appends content without removing existing blocks.
                    If False (default), replaces all existing content.
        
    Returns:
        Dict containing response data
    """
    notion = get_notion_client()
    
    if not append_only:
        # Get all existing blocks in a single request
        response = notion.blocks.children.list(block_id=page_id)
        
        # Archive all blocks at once by setting their archived flag
        for block in response.get('results', []):
            notion.blocks.update(block_id=block['id'], archived=True)
    
    # Use our module to parse markdown into Notion blocks
    blocks = markdown_to_notion_blocks(content)
    
    # Add new content in a single call
    return notion.blocks.children.append(
        block_id=page_id,
        children=blocks
    )

def upload_markdown_file_to_page(page_id: str, markdown_file_path: str) -> Dict:
    """
    Upload markdown file content to an existing Notion page.
    
    Args:
        page_id: ID of the page to update
        markdown_file_path: Path to the markdown file
        
    Returns:
        Dict containing response data or error information
    """
    try:
        with open(markdown_file_path, 'r', encoding='utf-8') as file:
            markdown_content = file.read()
        
        return add_content_to_page(page_id, markdown_content)
    except Exception as e:
        return {"error": str(e)}

# -------------------- Database Management Functions --------------------

def ensure_database_schema(database_id: str, required_properties: Dict[str, Dict]) -> bool:
    """
    Ensure a Notion database has all the required properties with correct types.
    
    Args:
        database_id: ID of the database to check/update
        required_properties: Dict of property name to property configuration
                           e.g. {"Name": {"title": {}}, "Date": {"date": {}}}
    
    Returns:
        bool: True if schema was updated, False if no changes were needed
    """
    notion = get_notion_client()
    
    try:
        # Get current database schema
        db = notion.databases.retrieve(database_id)
        needs_update = False
        new_properties = {}
        
        # Check for required properties
        for prop_name, prop_config in required_properties.items():
            if prop_name not in db['properties']:
                print(f"Adding {prop_name} property...")
                new_properties[prop_name] = prop_config
                needs_update = True
            else:
                # TODO: Check if existing property has correct type
                pass
        
        # Update database if needed
        if needs_update:
            print("Updating database schema...")
            notion.databases.update(
                database_id=database_id,
                properties=new_properties
            )
            print("✅ Database schema updated")
        
        return needs_update
    except Exception as e:
        print(f"❌ Error updating database schema: {str(e)}")
        return False


def find_database_entry(database_id: str, property_name: str, property_value: str, property_type: str = "rich_text") -> Optional[Dict]:
    """
    Find an entry in a Notion database by matching a property value.
    
    Args:
        database_id: ID of the database to search
        property_name: Name of the property to match
        property_value: Value to match against
        property_type: Type of property to match (rich_text, date, etc.)
    
    Returns:
        Optional[Dict]: The matching entry if found, None otherwise
    """
    notion = get_notion_client()
    
    try:
        # Build filter based on property type
        if property_type == "date":
            filter_obj = {
                "property": property_name,
                "date": {
                    "equals": property_value
                }
            }
        else:  # default to rich_text
            filter_obj = {
                "property": property_name,
                "rich_text": {
                    "equals": property_value
                }
            }
        
        response = notion.databases.query(
            database_id=database_id,
            filter=filter_obj
        )
        
        if response.get('results'):
            return response['results'][0]
        return None
    except Exception as e:
        print(f"❌ Error searching database: {str(e)}")
        return None


def get_page_timestamps(page_id: str) -> Optional[Dict[str, datetime]]:
    """
    Get the created_time and last_edited_time for a Notion page.
    
    Args:
        page_id: ID of the page
    
    Returns:
        Optional[Dict[str, datetime]]: Dict with 'created_time' and 'last_edited_time',
                                      or None if page not found/error
    """
    notion = get_notion_client()
    
    try:
        page = notion.pages.retrieve(page_id)
        return {
            'created_time': datetime.fromisoformat(page['created_time'].replace('Z', '+00:00')),
            'last_edited_time': datetime.fromisoformat(page['last_edited_time'].replace('Z', '+00:00'))
        }
    except Exception as e:
        print(f"❌ Error getting page timestamps: {str(e)}")
        return None


def should_update_page(page_id: str, local_modified_time: datetime) -> bool:
    """
    Check if a Notion page should be updated based on timestamps.
    
    Args:
        page_id: ID of the Notion page
        local_modified_time: Modification time of the local content
    
    Returns:
        bool: True if the page should be updated (local content is newer)
    """
    timestamps = get_page_timestamps(page_id)
    if not timestamps:
        return True  # If we can't get timestamps, assume we should update
    
    # Convert local time to UTC for comparison
    local_modified_utc = local_modified_time.astimezone(timezone.utc)
    
    # Compare with creation time
    return local_modified_utc > timestamps['created_time']


def create_or_update_database_entry(database_id: str, properties: Dict, content: Optional[str] = None,
                                  unique_property: Optional[Tuple[str, str, str]] = None,
                                  local_modified_time: Optional[datetime] = None) -> Dict:
    """
    Create or update an entry in a Notion database. If unique_property is provided,
    will first search for an existing entry and update it instead of creating a new one.
    
    Args:
        database_id: ID of the database
        properties: Dict containing property values for the entry
        content: Optional markdown content to add to the page
        unique_property: Optional tuple of (property_name, property_value, property_type) to find existing entry
        local_modified_time: Optional timestamp to compare with Notion's last_edited_time
                           If provided, will only update if local content is newer
    
    Returns:
        Dict containing the entry data or error information
    """
    notion = get_notion_client()
    
    try:
        # Check for existing entry if unique_property provided
        existing_entry = None
        if unique_property:
            prop_name, prop_value, prop_type = unique_property
            existing_entry = find_database_entry(database_id, prop_name, prop_value, prop_type)
            
            if existing_entry:
                # Check if we should update based on timestamps
                if local_modified_time and not should_update_page(existing_entry['id'], local_modified_time):
                    print(f"Skipping update for {existing_entry['id']} - local content is not newer")
                    return existing_entry
                
                print(f"Found existing entry {existing_entry['id']}, deleting it...")
                delete_page(existing_entry['id'])
                print("✅ Existing entry deleted")
        
        # Create new entry
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        
        # Add content if provided
        if content and response.get("id"):
            add_content_to_page(response["id"], content)
        
        return response
    except Exception as e:
        return {"error": str(e)}

def create_database_entry(database_id: str, properties: Dict) -> Dict:
    """
    Create a new entry in a Notion database.
    
    Args:
        database_id: ID of the database
        properties: Dict containing property values for the new entry
        
    Returns:
        Dict containing the new database entry or error information
    """
    notion = get_notion_client()
    
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    
    return notion.pages.create(**payload)

def update_database_entry(page_id: str, properties: Dict) -> Dict:
    """
    Update an existing entry in a Notion database.
    
    Args:
        page_id: ID of the database entry (page) to update
        properties: Dict containing property values to update
        
    Returns:
        Dict containing the updated database entry or error information
    """
    notion = get_notion_client()
    return notion.pages.update(page_id=page_id, properties=properties)

def delete_database_entry(page_id: str) -> Dict:
    """
    Delete (place in trash) an entry in a Notion database.
    
    Args:
        page_id: ID of the database entry (page) to delete
        
    Returns:
        Dict containing response data or error information
    """
    return delete_page(page_id)

# -------------------- Session Summaries Database Functions --------------------

def create_session_summary(
    database_id: str, 
    title: str, 
    session_date: str,
    markdown_content: str
) -> Dict:
    """
    Create a session summary entry in the Notion database.
    
    Args:
        database_id: ID of the session summaries database
        title: Session title
        session_date: Session date in ISO format (YYYY-MM-DD)
        markdown_content: Markdown content of the session summary
        
    Returns:
        Dict containing the new database entry or error information
    """
    # Create properties for database entry
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        },
        "Date": {
            "date": {
                "start": session_date
            }
        }
    }
    
    # Create the database entry
    notion = get_notion_client()
    result = notion.pages.create(
        parent={"database_id": database_id},
        properties=properties
    )
    
    # If creation was successful, upload the markdown content
    if result.get("id"):
        add_content_to_page(result["id"], markdown_content)
    
    return result

def update_session_summary(
    page_id: str,
    title: Optional[str] = None,
    session_date: Optional[str] = None,
    markdown_content: Optional[str] = None
) -> Dict:
    """
    Update an existing session summary entry.
    
    Args:
        page_id: ID of the session summary page to update
        title: New title (optional)
        session_date: New session date in ISO format (optional)
        markdown_content: New markdown content (optional)
        
    Returns:
        Dict containing the updated entry or error information
    """
    notion = get_notion_client()
    properties = {}
    
    if title:
        properties["Name"] = {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    
    if session_date:
        properties["Date"] = {
            "date": {
                "start": session_date
            }
        }
    
    # Update properties if there are any
    result = {}
    if properties:
        result = notion.pages.update(
            page_id=page_id,
            properties=properties
        )
    
    # Update content if provided
    if markdown_content:
        # First, archive existing content blocks
        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
        for block in blocks:
            notion.blocks.update(block_id=block["id"], in_trash=True)
        
        # Then add new content
        add_content_to_page(page_id, markdown_content)
    
    return result

# -------------------- References Database Functions --------------------

def create_reference_entry(
    database_id: str,
    name: str,
    ref_type: str,
    aliases: str = "",
    misspellings: str = "",
    description: str = "",
    first_appearance: str = ""
) -> Dict:
    """
    Create an entry in the names and references database.
    
    Args:
        database_id: ID of the references database
        name: Name of the reference
        ref_type: Type of reference (PC, NPC, Location, etc.)
        aliases: Comma-delimited list of aliases
        misspellings: Comma-delimited list of common misspellings
        description: Description of the reference
        first_appearance: Session date of first appearance (YYYY-MM-DD)
        
    Returns:
        Dict containing the new database entry or error information
    """
    # Create properties for database entry
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": name
                    }
                }
            ]
        },
        "Type": {
            "select": {
                "name": ref_type
            }
        }
    }
    
    # Add optional properties if provided
    if aliases:
        properties["Aliases"] = {
            "rich_text": [
                {
                    "text": {
                        "content": aliases
                    }
                }
            ]
        }
    
    if misspellings:
        properties["Misspellings"] = {
            "rich_text": [
                {
                    "text": {
                        "content": misspellings
                    }
                }
            ]
        }
    
    if description:
        properties["Description"] = {
            "rich_text": [
                {
                    "text": {
                        "content": description
                    }
                }
            ]
        }
    
    if first_appearance:
        properties["First Appearance"] = {
            "date": {
                "start": first_appearance
            }
        }
    
    return create_database_entry(database_id, properties)

def update_reference_entry(
    page_id: str,
    name: Optional[str] = None,
    ref_type: Optional[str] = None,
    aliases: Optional[str] = None,
    misspellings: Optional[str] = None,
    description: Optional[str] = None,
    first_appearance: Optional[str] = None
) -> Dict:
    """
    Update an existing entry in the references database.
    
    Args:
        page_id: ID of the reference entry to update
        name: New name (optional)
        ref_type: New reference type (optional)
        aliases: New comma-delimited list of aliases (optional)
        misspellings: New comma-delimited list of misspellings (optional)
        description: New description (optional)
        first_appearance: New first appearance date (optional)
        
    Returns:
        Dict containing the updated entry or error information
    """
    properties = {}
    
    if name:
        properties["Name"] = {
            "title": [
                {
                    "text": {
                        "content": name
                    }
                }
            ]
        }
    
    if ref_type:
        properties["Type"] = {
            "select": {
                "name": ref_type
            }
        }
    
    if aliases is not None:  # Allow empty string to clear the field
        properties["Aliases"] = {
            "rich_text": [
                {
                    "text": {
                        "content": aliases
                    }
                }
            ]
        }
    
    if misspellings is not None:  # Allow empty string to clear the field
        properties["Misspellings"] = {
            "rich_text": [
                {
                    "text": {
                        "content": misspellings
                    }
                }
            ]
        }
    
    if description is not None:  # Allow empty string to clear the field
        properties["Description"] = {
            "rich_text": [
                {
                    "text": {
                        "content": description
                    }
                }
            ]
        }
    
    if first_appearance:
        properties["First Appearance"] = {
            "date": {
                "start": first_appearance
            }
        }
    
    return update_database_entry(page_id, properties)

# -------------------- Query Functions --------------------

def query_database(database_id: str, filter_obj: Optional[Dict] = None, sorts: Optional[List] = None) -> Dict:
    """
    Query entries from a Notion database with optional filtering and sorting.
    
    Args:
        database_id: ID of the database to query
        filter_obj: Optional filter object for the query
        sorts: Optional sorting specifications
        
    Returns:
        Dict containing the query results or error information
    """
    notion = get_notion_client()
    
    query_params = {"database_id": database_id}
    if filter_obj:
        query_params["filter"] = filter_obj
    if sorts:
        query_params["sorts"] = sorts
    
    return notion.databases.query(**query_params)

def search_references(database_id: str, search_text: str) -> List[Dict]:
    """
    Search for references in the references database by name, aliases, or misspellings.
    
    Args:
        database_id: ID of the references database
        search_text: Text to search for
        
    Returns:
        List of matching reference entries
    """
    notion = get_notion_client()
    
    # Create a filter for name, aliases, and misspellings
    filter_obj = {
        "or": [
            {
                "property": "Name",
                "title": {
                    "contains": search_text
                }
            },
            {
                "property": "Aliases",
                "rich_text": {
                    "contains": search_text
                }
            },
            {
                "property": "Misspellings",
                "rich_text": {
                    "contains": search_text
                }
            }
        ]
    }
    
    response = notion.databases.query(
        database_id=database_id,
        filter=filter_obj
    )
    
    return response.get("results", [])


def _self_test_notion_utils():
    """
    Self-test for notion_utils: uploads session summary markdown to a test Notion database.
    Uses source file name as a unique identifier for updates.
    """
    # Use the existing database
    print("Starting notion_utils self-test...")
    DATABASE_ID = "1fa7b6a980788076bdf2ed80a214d132"  # The database you created
    print(f"Using database: {DATABASE_ID}")
    
    # Define required database schema
    required_properties = {
        "Name": {"title": {}},  # Required
        "Source File": {"rich_text": {}},
        "Date": {"date": {}}
    }
    
    # Ensure database has required properties
    ensure_database_schema(DATABASE_ID, required_properties)
    
    # Path to the session summary file
    summary_file = "../output/summaries/session-summary.2025-05-16.md"
    source_file = os.path.basename(summary_file)
    
    print(f"Loading content from: {summary_file}")
    try:
        # Read the markdown content from file
        with open(summary_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
            
        print(f"Read {len(markdown_content)} characters from {summary_file}")
        
        # Extract date from filename (assuming format session-summary.YYYY-MM-DD.md)
        date_str = source_file.split('.')[1]  # Gets YYYY-MM-DD
        
        # Create or update the entry
        result = create_or_update_database_entry(
            database_id=DATABASE_ID,
            properties={
                "Name": {
                    "title": [{
                        "text": {
                            "content": f"Session Summary - {date_str}"
                        }
                    }]
                },
                "Source File": {
                    "rich_text": [{
                        "text": {
                            "content": source_file
                        }
                    }]
                },
                "Date": {
                    "date": {
                        "start": date_str
                    }
                }
            },
            content=markdown_content,
            unique_property=("Source File", source_file)
        )
        
        if "error" in result:
            print(f"❌ Error during page creation: {result['error']}")
        else:
            print("✅ Successfully created page with session summary.")
            print("Please check the page to verify the content is correct.")
    
    except FileNotFoundError:
        print(f"❌ Error: Could not find file: {summary_file}")
        print("Please make sure the file exists and the path is correct.")
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    _self_test_notion_utils()
