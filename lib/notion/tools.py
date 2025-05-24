"""notion_tools.py — OpenAI Agents SDK tools for Notion entity database."""
from typing import List, Dict, Optional
from datetime import datetime
from typing_extensions import TypedDict

from agents import function_tool, RunContextWrapper
from ..memory.context import SessionContext

from .cache import (
    get_entity,
    update_entity,
    EntityType,
    EntityEntry,
    _entity_cache
)


class EntityData(TypedDict):
    """Entity data for Notion database."""
    name: str
    type: str
    aliases: Optional[str]
    common_misspellings: Optional[str]
    description: Optional[str]
    notion_id: Optional[str]


class EntityUpdate(TypedDict):
    """Entity update data."""
    notion_id: str  # Required for updates
    name: str
    type: str
    aliases: Optional[str]
    common_misspellings: Optional[str]
    description: Optional[str]


class EntityCreate(TypedDict):
    """Entity creation data."""
    name: str
    type: str
    aliases: Optional[str]
    common_misspellings: Optional[str]
    description: Optional[str]


@function_tool
def get_all_entities() -> List[EntityData]:
    """
    Get information about all entities from the Notion database.
    
    This tool retrieves all known entities (characters, locations, organizations, etc.) 
    that exist in the game world. Use this to:
    - Check if an entity already exists before creating a new one
    - Find the correct spelling of names mentioned in transcripts/digests
    - Verify entity types and descriptions
    - Resolve aliases to canonical names
    
    Focus on proper names and uncommon names (even when they aren't proper, like fictional
    monster names such as 'Squig'). Skip mundane things where the spelling is common and
    there's no risk of misspelling (e.g., 'sword', 'horse', 'gold').
    
    Returns
    -------
    List[EntityData]: List of all entities. Each entity has:
        • name - Entity name (canonical/official spelling)
        • type - One of: PC, NPC, Location, Organization, Diety, Creature
        • aliases - Alternative names or titles (comma separated)
        • common_misspelling - Common misspellings found in transcripts (comma separated)
        • description - Brief description of the entity
        • notion_id - Notion page ID (required for updates)
    """
    results = []
    for entity in _entity_cache.values():
        results.append({
            "name": entity.name,
            "type": entity.type,
            "aliases": entity.aliases,
            "common_misspellings": entity.common_misspellings,
            "description": entity.description,
            "notion_id": entity.notion_id
        })
    return results

@function_tool
def update_existing_entities(entities: List[EntityUpdate]) -> str:
    """
    Update existing entities in the Notion database.
    
    Use this tool when you discover new information about existing entities in transcripts or digests.
    
    Remember to FOCUS ON PROPER NAMES OR UNCOMMON NAMES, even when they aren't proper
    (e.g., fictional monster names like 'Squig'). Don't worry about updating mundane things
    where the spelling is so common there is no risk of misspelling (e.g., 'sword', 'horse', 'gold').
    
    For example:
    - Add newly discovered aliases or titles for a character
    - Add common misspellings found in transcripts to help with future name resolution
    - Update descriptions with new information
    - Correct entity types if miscategorized
    
    This ensures the entity database stays current and helps maintain consistent naming
    across all campaign materials.
    
    Parameters
    ----------
    entities : List[EntityUpdate]
        List of entity updates. Each must have:
        • notion_id - Existing Notion page ID (required to identify the entity)
        • name - Entity name (canonical/official spelling)
        • type - One of: PC, NPC, Location, Organization, Diety, Creature
        And optionally:
        • aliases - Alternative names or titles (comma separated)
        • common_misspellings - Common misspellings found in transcripts (comma separated)
        • description - Brief description of the entity
    
    Returns
    -------
    str: "ok" on success.
    """
    for entity_data in entities:
        # Get existing entity to verify it exists
        entity = get_entity(entity_data["name"])
        if not entity or entity.notion_id != entity_data["notion_id"]:
            raise ValueError(f"Entity {entity_data['name']} not found or ID mismatch")
        
        # Update entity
        update_entity(
            name=entity_data["name"],
            type=entity_data["type"],
            aliases=entity_data.get("aliases"),
            common_misspellings=entity_data.get("common_misspellings"),
            description=entity_data.get("description")
        )
    
    return "ok"

@function_tool
def add_new_entities(wrapper: RunContextWrapper[SessionContext], entities: List[EntityCreate]) -> str:
    """
    Add new entities to the Notion database.
    
    Use this tool when you discover new characters, locations, organizations, or other
    entities mentioned in transcripts or digests that don't yet exist in the database.
    
    PRIMARILY FOCUS ON PROPER NAMES OR UNCOMMON NAMES, even when they aren't proper
    (e.g., fictional monster names like 'Squig'). SKIP adding entities for mundane things
    where the spelling is so common there is no risk of misspelling (e.g., 'sword', 'horse', 'gold').
    
    This is especially important for:
    - New PCs, NPCs, locations, or organizations introduced in a session
    - Organizations or concepts mentioned for the first time
    - Any significant named entity that appears in transcripts
    - Fictional creatures or items with unusual names
    
    By capturing new entities as they appear, we maintain a comprehensive reference
    of all named elements in the game world and ensure consistent spelling in future
    materials. If you detect misspellings in the transcript, include them in the
    common_misspellings field to help with future name resolution.
    
    Parameters
    ----------
    wrapper : RunContextWrapper[SessionContext]
        The context wrapper containing session information.
    entities : List[EntityCreate]
        List of new entities. Each must have:
        • name - Entity name (canonical/official spelling)
        • type - One of: PC, NPC, Location, Organization, Diety, Creature
        And optionally:
        • aliases - Alternative names or titles (comma separated)
        • common_misspellings - Common misspellings found in transcripts (comma separated)
        • description - Brief description of the entity based on context
    
    Returns
    -------
    str: "ok" on success.
    """
    for entity_data in entities:
        # Check if entity already exists
        if get_entity(entity_data["name"]):
            raise ValueError(f"Entity {entity_data['name']} already exists")
        
        # Use session date directly from context (already in ISO format)
        first_appearance = wrapper.context.session_date
        
        # Add new entity
        update_entity(
            name=entity_data["name"],
            type=entity_data["type"],
            aliases=entity_data.get("aliases"),
            common_misspellings=entity_data.get("common_misspellings"),
            description=entity_data.get("description"),
            first_appearance=first_appearance
        )
    
    return "ok"
