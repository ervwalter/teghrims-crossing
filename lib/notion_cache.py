"""
Cache layer for Notion databases to improve performance during agent runs.
"""
from datetime import datetime
from typing import Dict, List, Optional, Literal

from .notion_utils import (
    ensure_database_schema,
    find_database_entry,
    get_database_entries,
    create_database_entry,
    update_database_entry
)

# Database IDs
ENTITY_DB = "1f97b6a9807880cea2b4dbbf7cf4ad84"

# Valid entity types
EntityType = Literal[
    "PC",
    "NPC",
    "Location",
    "Organization",
    "Diety",
    "Creature",
    "Object",
    "Concept"
]

class EntityEntry:
    """Represents an entry in the entities database."""
    def __init__(
        self,
        name: str,
        type: EntityType,
        aliases: Optional[str] = None,
        common_misspellings: Optional[str] = None,
        description: Optional[str] = None,
        first_appearance: Optional[str] = None,
        notion_id: Optional[str] = None,
        modified: bool = True
    ):
        self.name = name
        self.type = type
        self.aliases = aliases or ""
        self.common_misspellings = common_misspellings or ""
        self.description = description or ""
        self.first_appearance = first_appearance
        self.notion_id = notion_id
        self.modified = modified  # True if entry needs to be synced to Notion
    
    def to_notion_properties(self) -> Dict:
        """Convert to Notion properties format."""
        return {
            "Name": {
                "title": [{
                    "text": {
                        "content": self.name
                    }
                }]
            },
            "Type": {
                "select": {
                    "name": self.type
                }
            },
            "Aliases": {
                "rich_text": [{
                    "text": {
                        "content": self.aliases
                    }
                }] if self.aliases else []
            },
            "Common Misspellings": {
                "rich_text": [{
                    "text": {
                        "content": self.common_misspellings
                    }
                }] if self.common_misspellings else []
            },
            "Description": {
                "rich_text": [{
                    "text": {
                        "content": self.description
                    }
                }] if self.description else []
            },
            "First Appearance": {
                "date": {
                    "start": self.first_appearance
                }
            } if self.first_appearance else {"date": None}
        }
    
    @classmethod
    def from_notion_properties(cls, properties: Dict, notion_id: str) -> 'EntityEntry':
        """Create from Notion properties format."""
        return cls(
            name=properties["Name"]["title"][0]["text"]["content"] if properties["Name"]["title"] else "",
            type=properties["Type"]["select"]["name"],
            aliases=properties["Aliases"]["rich_text"][0]["text"]["content"] if properties["Aliases"]["rich_text"] else "",
            common_misspellings=properties["Common Misspellings"]["rich_text"][0]["text"]["content"] if properties["Common Misspellings"]["rich_text"] else "",
            description=properties["Description"]["rich_text"][0]["text"]["content"] if properties["Description"]["rich_text"] else "",
            first_appearance=properties["First Appearance"]["date"]["start"] if properties["First Appearance"]["date"] else None,
            notion_id=notion_id,
            modified=False
        )

# Global cache of entities
_entity_cache: Dict[str, EntityEntry] = {}
_initialized = False

def initialize_cache() -> None:
    """Initialize the cache by loading all entries from Notion."""
    global _initialized, _entity_cache
    
    if _initialized:
        return
    
    # Ensure database schema
    schema = {
        "Name": {"title": {}},
        "Type": {"select": {
            "options": [
                {"name": "PC"},
                {"name": "NPC"},
                {"name": "Location"},
                {"name": "Organization"},
                {"name": "Diety"},
                {"name": "Creature"},
                {"name": "Object"},
                {"name": "Concept"}
            ]
        }},
        "Aliases": {"rich_text": {}},
        "Common Misspellings": {"rich_text": {}},
        "Description": {"rich_text": {}},
        "First Appearance": {"date": {}}
    }
    ensure_database_schema(ENTITY_DB, schema)
    
    try:
        # Load all entries
        entries = get_database_entries(ENTITY_DB)
        if entries:
            for entry in entries:
                if entry and "properties" in entry and "id" in entry:
                    entity = EntityEntry.from_notion_properties(entry["properties"], entry["id"])
                    _entity_cache[entity.name] = entity
                else:
                    print(f"Warning: Invalid entry format in database: {entry}")
    except Exception as e:
        print(f"Error initializing Notion cache: {str(e)}")
        # Continue with an empty cache rather than failing completely
    
    _initialized = True

def get_entity(name: str) -> Optional[EntityEntry]:
    """Get an entity from the cache by name."""
    if not _initialized:
        initialize_cache()
    return _entity_cache.get(name)

def update_entity(
    name: str,
    type: EntityType,
    aliases: Optional[str] = None,
    s: Optional[str] = None,
    description: Optional[str] = None,
    first_appearance: Optional[str] = None
) -> EntityEntry:
    """Create or update an entity in the cache."""
    if not _initialized:
        initialize_cache()
    
    entity = _entity_cache.get(name)
    if entity:
        # Update existing entry
        if type != entity.type:
            entity.type = type
            entity.modified = True
        if aliases is not None and aliases != entity.aliases:
            entity.aliases = aliases
            entity.modified = True
        if common_misspellings is not None and common_misspellings != entity.common_misspellings:
            entity.common_misspellings = common_misspellings
            entity.modified = True
        if description is not None and description != entity.description:
            entity.description = description
            entity.modified = True
        if first_appearance is not None and first_appearance != entity.first_appearance:
            entity.first_appearance = first_appearance
            entity.modified = True
    else:
        # Create new entry
        entity = EntityEntry(
            name=name,
            type=type,
            aliases=aliases,
            common_misspellings=common_misspellings,
            description=description,
            first_appearance=first_appearance
        )
        _entity_cache[name] = entity
    
    return entity

def sync_to_notion() -> None:
    """Sync all modified entries to Notion."""
    if not _initialized:
        return
    
    for entity in _entity_cache.values():
        if entity.modified:
            print(f"Syncing entity {entity.name} to Notion...")
            properties = entity.to_notion_properties()
            
            if entity.notion_id:
                # Update existing entry
                result = update_database_entry(
                    page_id=entity.notion_id,
                    properties=properties
                )
            else:
                # Create new entry
                result = create_database_entry(
                    database_id=ENTITY_DB,
                    properties=properties
                )
                if result:
                    # Store the new notion_id
                    entity.notion_id = result["id"]
            
            if result:
                print(f"✅ Successfully synced {entity.name}")
                entity.modified = False  # Reset modified flag
            else:
                print(f"❌ Failed to sync {entity.name}")
