#!/usr/bin/env python
"""
Functions for updating campaign knowledge (articles and entities) based on session digests.
"""

import asyncio
import time
from agents import Agent, Runner
from ..memory.tools import list_articles, get_articles, update_article
from ..memory.references import list_reference_files, retrieve_reference_files
from ..notion.tools import get_all_entities, add_new_entities, update_existing_entities
from ..memory.context import SessionContext


def update_campaign_knowledge(session_date: str, openai_api_key: str, digest_content: str, max_retries: int = 1) -> None:
    """
    Use an agent to process the session digest and update campaign knowledge (articles and entities) accordingly.
    Args:
        session_date: The date of the session in YYYY-MM-DD format
        openai_api_key: OpenAI API key
        digest_content: Content of the session digest
        max_retries: Maximum number of retry attempts (default: 1)
    """
    # Tools for updating articles and entities
    tools = [
        list_articles, 
        get_articles, 
        update_article, 
        list_reference_files, 
        retrieve_reference_files,
        get_all_entities,
        add_new_entities,
        update_existing_entities
    ]

    # Create session context
    session_context = SessionContext(session_date=session_date)

    agent = Agent[SessionContext](
        name="CampaignKnowledgeUpdaterAgent",
        instructions=(
            "You are the CAMPAIGN KNOWLEDGE UPDATER. Your job is to read the session digest "
            "and update both campaign memory articles and entity database to reflect new or changed information.\n\n"
            "PART 1: UPDATING CAMPAIGN MEMORY ARTICLES\n"
            "Rules:\n"
            "- Use list_articles and get_articles to review the current state of the memory.\n"
            "- Use update_article to add new information or revise details as needed.\n"
            "- Be careful not to overwrite important existing information.\n"
            "- Reference the digest and existing memory to ensure continuity and accuracy.\n"
            "- Only update articles if there is clear, new, or corrected information from the digest.\n"
            "- Do NOT remove or overwrite important information that is not contradicted by the digest.\n"
            "- If uncertain, make your best effort to update the article using reasonable inference from the digest and prior memory.\n"
            "- Document all changes in the article body, maintaining good formatting.\n\n"
            "PART 2: UPDATING ENTITY DATABASE\n"
            "Rules:\n"
            "- Use get_all_entities to review the current entities in the database.\n"
            "- ONLY ADD PROPER NAMES AND SPECIFIC NAMED ENTITIES. Do not add generic terms.\n"
            "- ADD: Named characters ('Sir Galahad'), named locations ('Minas Tirith'), named organizations ('The Fellowship').\n"
            "- DO NOT ADD: Generic terms ('the armory', 'town guard', 'a sword', 'the tavern', 'the blacksmith').\n"
            "- For new NAMED entities mentioned in the digest that don't exist in the database, use add_new_entities.\n"
            "- For existing entities that have new information (aliases, descriptions, etc.), use update_existing_entities.\n"
            "- Pay special attention to the 'Entities' section of the digest which lists NPCs, locations, and items.\n"
            "- For new entities, set appropriate entity types (PC, NPC, Location, Organization, Diety, Creature).\n"
            "- ALIASES are correctly spelled alternative names. MISSPELLINGS are incorrect versions.\n"
            "- Include aliases and common misspellings when available to help with future name resolution.\n"
            "- Write concise but informative descriptions based on what's known from the digest.\n\n"
            "GENERAL GUIDANCE:\n"
            "- You may use list_reference_files and retrieve_reference_files to access reference documents provided by the GM.\n"
            "- These may help you understand the general campaign world and ensure your updates are accurate and consistent.\n"
            "- Always prioritize consistency with existing information unless new information clearly contradicts it.\n"
        ),
        model="gpt-4.1",
        tools=tools
    )

    prompt = (
        """
        Please retrieve and update every campaign memory article based on the session digest below.
        \n---\n
        SESSION DIGEST:\n\n"""
        f"""{digest_content}"""
    )

    async def run_update():
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = await Runner.run(agent, prompt, context=session_context)
                print("Campaign knowledge update agent output:\n", result.final_output)
                return
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Clean up error message - remove HTML and keep only useful info
                if "<!DOCTYPE html>" in error_msg or "<html>" in error_msg:
                    lines = error_msg.split('\n')
                    clean_msg = lines[0] if lines else "API request failed"
                    if len(clean_msg) > 200:
                        clean_msg = clean_msg[:200] + "..."
                    error_msg = clean_msg
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"  ⚠️  Campaign knowledge update attempt {attempt + 1} failed: {error_msg}")
                    print(f"  🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Error updating campaign knowledge for {session_date}: {error_msg}")
                    raise last_error

    asyncio.run(run_update())