#!/usr/bin/env python
"""
Spelling correction module for fixing entity name spellings in existing content.
Uses the entity database to correct names while preserving all other content.
"""

import os
import glob
import asyncio
from typing import List, Dict, Optional
from agents import Agent, Runner
from ..notion.tools import get_all_entities
from ..memory.database import list_articles_meta, latest_revision_for_date, insert_revision
from ..memory.context import SessionContext
from datetime import date


async def correct_spelling_with_entities(content: str, entities_context: str) -> str:
    """
    Use OpenAI Agent SDK to correct entity name spellings in content.
    
    Args:
        content: The content to spell-check
        entities_context: String containing all entity information for reference
        
    Returns:
        str: Content with corrected entity spellings
    """
    tools = [get_all_entities]
    
    # Create a context with today's date (doesn't matter for spelling correction)
    session_context = SessionContext(session_date=date.today().isoformat())
    
    agent = Agent[SessionContext](
        name="SpellingCorrectionAgent",
        instructions=(
            "You are a SPELLING CORRECTION SPECIALIST for a D&D campaign called 'Teghrim's Crossing'. "
            "Your ONLY job is to fix misspelled entity names (characters, locations, organizations, etc.) "
            "based on the official entity database.\n\n"
            "CRITICAL RULES:\n"
            "- Use get_all_entities to access the official entity database\n"
            "- ONLY correct entity name spellings - do NOT rewrite, improve, or change anything else\n"
            "- Do NOT change sentence structure, word choice, or writing style\n"
            "- Do NOT add or remove content\n"
            "- Do NOT 'improve' the writing in any way\n"
            "- Focus ONLY on proper names, character names, location names, organization names, etc.\n"
            "- If you're unsure whether something is an entity name, leave it unchanged\n"
            "- Preserve all formatting, punctuation, and structure exactly\n\n"
            "Your goal is to make entity names consistent with the official database while "
            "leaving everything else completely untouched."
        ),
        model="gpt-4.1",
        tools=tools
    )
    
    prompt = f"""Please correct any misspelled entity names in the following content using the official entity database.

IMPORTANT: Only fix entity name spellings. Do NOT change anything else about the content - no rewriting, no improvements, no style changes.

Content to check:

{content}

Return the content with only entity name spellings corrected."""
    
    result = await Runner.run(agent, prompt, context=session_context)
    return result.final_output


def get_entities_context() -> str:
    """Get all entities formatted as context string for the agent."""
    # This will be provided by the agent tool, but we can prepare context if needed
    return "Entity information will be retrieved using the get_all_entities tool."


def process_summary_files(base_dir: str) -> List[str]:
    """
    Process all files in output/summaries/ for spelling corrections.
    
    Args:
        base_dir: Base directory of the project
        
    Returns:
        List of processed file paths
    """
    summaries_dir = os.path.join(base_dir, "output", "summaries")
    if not os.path.exists(summaries_dir):
        print("No summaries directory found")
        return []
    
    processed_files = []
    markdown_files = glob.glob(os.path.join(summaries_dir, "*.md"))
    
    print(f"Found {len(markdown_files)} summary files to process")
    
    entities_context = get_entities_context()
    
    for file_path in markdown_files:
        print(f"Processing {os.path.basename(file_path)}...")
        
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Correct spelling
            corrected_content = asyncio.run(
                correct_spelling_with_entities(original_content, entities_context)
            )
            
            # Only write if content changed
            if corrected_content.strip() != original_content.strip():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_content)
                print(f"  ✅ Updated {os.path.basename(file_path)}")
                processed_files.append(file_path)
            else:
                print(f"  ℹ️  No changes needed for {os.path.basename(file_path)}")
                
        except Exception as e:
            print(f"  ❌ Error processing {os.path.basename(file_path)}: {str(e)}")
            continue
    
    return processed_files


def process_campaign_memory_articles() -> List[str]:
    """
    Process all campaign memory articles and their revisions for spelling corrections.
    
    Returns:
        List of updated article slugs
    """
    print("Processing campaign memory articles...")
    
    # Get all articles
    articles = list_articles_meta()
    if not articles:
        print("No campaign memory articles found")
        return []
    
    print(f"Found {len(articles)} articles to process")
    
    entities_context = get_entities_context()
    updated_articles = []
    
    for article in articles:
        slug = article['slug']
        print(f"Processing article: {article['title']} ({slug})")
        
        try:
            # Get the latest version of the article
            latest_content, _ = latest_revision_for_date(slug, date.today())
            
            if not latest_content:
                print(f"  ℹ️  No content found for {slug}")
                continue
            
            # Correct spelling
            corrected_content = asyncio.run(
                correct_spelling_with_entities(latest_content, entities_context)
            )
            
            # Only update if content changed
            if corrected_content.strip() != latest_content.strip():
                # Create new revision with corrected content
                # Use today's date for the spelling correction revision
                insert_revision(
                    slug=slug,
                    content_md=corrected_content,
                    session_date=date.today(),
                    source="SPELLING_CORRECTION"
                )
                print(f"  ✅ Updated {slug}")
                updated_articles.append(slug)
            else:
                print(f"  ℹ️  No changes needed for {slug}")
                
        except Exception as e:
            print(f"  ❌ Error processing {slug}: {str(e)}")
            continue
    
    return updated_articles


def run_spelling_correction(base_dir: str) -> None:
    """
    Main function to run spelling correction on all content.
    
    Args:
        base_dir: Base directory of the project
    """
    print("Starting spelling correction process...\n")
    
    # Process summary files
    print("=== Processing Summary Files ===")
    processed_summaries = process_summary_files(base_dir)
    
    print(f"\nProcessed {len(processed_summaries)} summary files\n")
    
    # Process campaign memory articles
    print("=== Processing Campaign Memory Articles ===")
    updated_articles = process_campaign_memory_articles()
    
    print(f"\nUpdated {len(updated_articles)} campaign memory articles\n")
    
    # Publish updates to Notion
    if processed_summaries or updated_articles:
        print("=== Publishing Updates to Notion ===")
        
        # Publish summary updates
        if processed_summaries:
            print("Publishing summary updates to Notion...")
            try:
                from ..notion.publish import publish_session_outputs
                publish_session_outputs(base_dir)
                print("✅ Summary updates published to Notion")
            except Exception as e:
                print(f"❌ Error publishing summaries to Notion: {str(e)}")
        
        # Sync memory updates  
        if updated_articles:
            print("Syncing memory updates to Notion...")
            try:
                from ..notion.cache import sync_to_notion
                sync_to_notion()
                print("✅ Memory updates synced to Notion")
            except Exception as e:
                print(f"❌ Error syncing memory to Notion: {str(e)}")
    else:
        print("No updates needed - all content already has correct spelling!")
    
    print("\nSpelling correction complete!")