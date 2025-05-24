"""
memory_tools.py — OpenAI Agents SDK tools for campaign memory access
===================================================================
Purpose
-------
Provides Agent SDK function tools for accessing campaign memory articles with
temporal consistency. Uses the campaign_memory module for actual database operations.

Key features
~~~~~~~~~~~~
* Three Agent SDK function tools with rich docstrings:
  1. `list_articles`   – discover slugs/titles/descriptions for planning/UI.
  2. `get_articles`    – fetch articles *as they existed before* a given date.
  3. `update_article`  – append a new revision (session‑dated or human edit).

* All date parameters are optional & forgiving (default to *today* if missing or
  malformed) so calls never crash the Agent.
"""

from __future__ import annotations

import logging
from typing import List, Dict

from agents import RunContextWrapper, function_tool
from .context import SessionContext
from .database import list_articles_meta, latest_revision_for_date, insert_revision, ArticleMeta


# ---------------------------------------------------------------------------
# AGENT SDK TOOLS -------------------------------------------------------------

@function_tool
def list_articles() -> List[ArticleMeta]:
    """Return a list of campaign memory articles.

    Use this first to discover what campaign knowledge is available before reading specific articles.
    This helps you understand the scope of campaign information and choose which articles to read.

    Each entry contains:
      • `slug` – unique identifier used in other calls.
      • `title` – human‑readable title.
      • `description` – brief summary of the article's purpose.
    """
    return list_articles_meta()


@function_tool
def get_articles(wrapper: RunContextWrapper[SessionContext], slugs: List[str]) -> Dict[str, str]:
    """
    Fetch the full markdown *body* of each article in `slugs` **as it existed on or before** the session date in context.

    CRITICAL: This provides temporal consistency - you only see campaign knowledge that existed before the current session,
    preventing anachronisms and ensuring you don't reference events that haven't happened yet in the campaign timeline.

    Use this to:
    - Read existing campaign memory before processing new session information
    - Understand what the characters knew at a specific point in time
    - Maintain narrative continuity by respecting the campaign timeline

    Args:
        slugs: List of article slugs from `list_articles`. You can request multiple articles at once for efficiency.
    
    Returns:
        Dict mapping slug to full markdown content (empty string if article doesn't exist or has no content).
    """
    # Convert session_date string to date object (required by latest_revision_for_date)
    cutoff = wrapper.context.get_date_object()
        
    result = {}
    
    for slug in slugs:
        content, _ = latest_revision_for_date(slug, cutoff)
        result[slug] = content or ""
    
    return result


@function_tool
def update_article(wrapper: RunContextWrapper[SessionContext], slug: str, content_md: str, source: str = "LLM") -> str:
    """
    Update a campaign memory article with new information from the current session.

    IMPORTANT: This creates a new revision dated to the current session - it does NOT overwrite existing content.
    The content_md should be the COMPLETE updated article, incorporating both existing information and new details.

    Use this to:
    - Add new NPCs, locations, or plot developments discovered in the session
    - Update existing entries with new information or status changes
    - Maintain a living record of campaign knowledge that grows over time

    Workflow:
    1. First use `get_articles` to read the current content
    2. Incorporate new session information into the existing content  
    3. Use this function to save the complete updated article

    Args:
        slug: Article slug to update (from `list_articles`)
        content_md: Complete markdown content for the article (existing + new information)
        source: Source of update (defaults to "LLM", can be "HUMAN" for manual edits)
    
    Returns:
        "ok" on success, error message on failure.
    """
    # Convert session_date string to date object (required by insert_revision)
    session_date_obj = wrapper.context.get_date_object()
    
    try:
        insert_revision(
            slug=slug,
            content_md=content_md,
            session_date=session_date_obj,
            source=source
        )
        return "ok"
    except Exception as e:
        logging.error(f"Error updating article {slug}: {e}")
        return f"Error: {str(e)}"