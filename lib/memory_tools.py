"""
memory_tools.py — single‑file lore encyclopedia store + OpenAI Agents SDK tools
==============================================================================
Purpose
-------
Maintain a small campaign "encyclopedia" (7 wiki‑style articles) with **point‑in‑time**
reads so an OpenAI Agent sees only the campaign-memory that existed prior to the session it
is currently processing.

Key features
~~~~~~~~~~~~
* **Embedded SQLite** database (`campaign-memory.db`) — no server process.
* Auto‑seeds the DB on first run with the starter article stubs you supplied.
* Three Agent SDK function tools with rich docstrings:

  1. `list_articles`   – discover slugs/titles/descriptions for planning/UI.
  2. `get_article`     – fetch an article *as it existed before* a given date.
  3. `update_article`  – append a new revision (session‑dated or human edit).

* All date parameters are optional & forgiving (default to *today* if missing or
  malformed) so calls never crash the Agent.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from datetime import date
import logging
from typing import List, Optional, Dict, TypedDict, Tuple, Union

from agents import RunContextWrapper, function_tool
from .context import SessionContext

# Set up absolute path to the data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(MEMORY_DIR, exist_ok=True)
DB_PATH = Path(os.path.join(MEMORY_DIR, "campaign-memory.db"))

# ---------------------------------------------------------------------------
# INITIAL ARTICLE STUBS ------------------------------------------------------
class ArticleStub(TypedDict):
    title: str
    description: str
    body: str

_INITIAL_ARTICLES: Dict[str, ArticleStub] = {
    "characters": {
        "title": "Characters",
        "description": "This entry tracks all significant characters encountered throughout the campaign, including player characters, NPCs, and important faction members. Each entry includes essential details such as name, race, class/occupation, current location, relationship to the party, and notable characteristics. This file serves as the central repository for character information, helping maintain continuity in character interactions and development across sessions. Characters should be organized by category (PC, NPC, faction) and include cross-references to related locations, quests, and relationships.",
        "body": """# Characters\n\n## Player Characters\n<!-- Format: Name (Race, Class) - Brief description -->\n\n## Non-Player Characters (NPCs)\n<!-- Format: Name (Race, Occupation) - Location - Relationship to party - Brief description -->\n\n### Allies\n\n### Neutral\n\n### Antagonists\n\n## Factions and Organizations\n<!-- Format: Name - Purpose/Goals - Key Members - Relationship to party -->\n""",
    },
    "items-resources": {
        "title": "Items & Resources",
        "description": "This entry catalogs all significant items, artifacts, and resources acquired or encountered throughout the campaign. It tracks magical items, quest-related objects, valuable resources, and other important possessions. This file helps maintain consistency in item properties and availability, ensuring that important objects aren't forgotten or their powers inconsistently portrayed. Items are organized by type and significance, with cross-references to related characters, locations, and plot elements.",
        "body": """# Items & Resources\n\n## Magical Artifacts\n<!-- Format: Item name - Properties/powers - Current location/owner - Origin/history -->\n\n## Quest Items\n<!-- Format: Item name - Related quest - Current status - Significance -->\n\n## Valuable Resources\n<!-- Format: Resource name - Properties - Source locations - Current quantity -->\n\n## Party Inventory\n<!-- Format: Item name - Properties - Current holder - Acquisition details -->\n\n## Currency & Wealth\n<!-- Format: Character/party - Current funds - Notable expenses/income -->\n""",
    },
    "knowledge-lore": {
        "title": "Knowledge & Lore",
        "description": "This entry preserves all significant knowledge, secrets, legends, and historical information discovered throughout the campaign. It includes discovered lore, prophecies, ancient histories, and other information that enriches the world and informs future adventures. This file helps maintain consistency in the world's mythology and ensures that discovered knowledge is properly tracked and utilized in future sessions. Lore entries are organized by topic and source, with cross-references to related characters, locations, and plot elements.",
        "body": """# Knowledge & Lore\n\n## Discovered Secrets\n<!-- Format: Secret description - Source/how discovered - Significance - Related elements -->\n\n## Legends & Prophecies\n<!-- Format: Legend/prophecy name - Content - Source - Current relevance -->\n\n## Historical Events\n<!-- Format: Event name - Time period - Description - Current significance -->\n\n## Religious & Mystical Knowledge\n<!-- Format: Topic - Details - Source - Significance -->\n\n## Maps & Navigational Information\n<!-- Format: Region mapped - Notable features - Current accuracy -->\n""",
    },
    "locations": {
        "title": "Locations",
        "description": "This entry catalogs all significant locations encountered or mentioned throughout the campaign. Each entry includes the location name, geographic position, notable features, important NPCs, available services, and relevant history. This file helps maintain consistency in world-building and allows for quick reference when players return to previously visited locations. Locations are organized by region and include cross-references to related characters, quests, and items found there.",
        "body": """# Locations\n\n## Major Settlements\n<!-- Format: Name - Region - Notable features - Important NPCs - Available services -->\n\n## Points of Interest\n<!-- Format: Name - Region - Description - Significance to campaign -->\n\n## Dungeons & Adventure Sites\n<!-- Format: Name - Region - Status (explored/unexplored) - Notable features/encounters -->\n\n## Regions & Territories\n<!-- Format: Name - Governing faction - Geography - Notable settlements -->\n""",
    },
    "player-decisions": {
        "title": "Player Decisions & Consequences",
        "description": "This entry records significant choices made by players and their resulting consequences throughout the campaign. It captures branching narrative paths, moral dilemmas, and how player actions have shaped the world. This file helps ensure that player agency is respected and that their decisions have meaningful, consistent impacts on the game world. Entries are organized chronologically and include cross-references to affected characters, locations, and plot elements.",
        "body": """# Player Decisions & Consequences\n\n## Major Decisions\n<!-- Format: Decision description - Session/date - Character(s) involved - Immediate consequences -->\n\n## Long-term Consequences\n<!-- Format: Original decision - Resulting consequences - Current status -->\n\n## Altered Relationships\n<!-- Format: Character/faction - Original relationship - Current relationship - Cause of change -->\n\n## World State Changes\n<!-- Format: Change description - Cause - Areas affected -->\n""",
    },
    "plot-elements": {
        "title": "Plot Elements",
        "description": "This entry tracks all significant plot elements, story arcs, and narrative threads throughout the campaign. It includes main quests, side quests, and overarching campaign storylines with their current status and progress. This file helps maintain narrative continuity across sessions and ensures that story threads are not forgotten or contradicted. Plot elements are organized by importance and timeline, with cross-references to related characters, locations, and items.",
        "body": """# Plot Elements\n\n## Main Quest Line\n<!-- Format: Quest name - Current status - Key objectives - Related NPCs/locations -->\n\n## Active Side Quests\n<!-- Format: Quest name - Source/giver - Objectives - Current progress -->\n\n## Completed Quests\n<!-- Format: Quest name - Outcome - Consequences - Date completed -->\n\n## Future Hooks & Foreshadowing\n<!-- Format: Hook description - Potential development - Related elements -->\n\n## Campaign Timeline\n<!-- Format: Date/Session - Major event - Significance -->\n""",
    },
    "world-state": {
        "title": "World State",
        "description": "This entry tracks the current political, social, and environmental conditions of the campaign world. It includes information on ruling powers, ongoing conflicts, seasonal events, and other dynamic elements that change over time. This file helps maintain a consistent and evolving world that responds realistically to the passage of time and player actions. World state elements are organized by region and sphere of influence, with cross-references to related characters, factions, and plot elements.",
        "body": """# World State\n\n## Political Landscape\n<!-- Format: Region - Ruling power - Current stability - Notable tensions -->\n\n## Active Conflicts\n<!-- Format: Conflict name - Involved parties - Current status - Areas affected -->\n\n## Seasonal & Time-Dependent Events\n<!-- Format: Event name - Timing - Significance - Affected regions -->\n\n## Economic Conditions\n<!-- Format: Region - Resource availability - Trade status - Price fluctuations -->\n""",
    },
}

# ---------------------------------------------------------------------------
# DB INITIALISATION & SEEDING -------------------------------------------------

def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS article (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS article_revision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL REFERENCES article(id),
            session_date DATE NULL,           -- NULL = human edit
            source TEXT NOT NULL,             -- 'LLM' | 'HUMAN'
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content_md TEXT NOT NULL          -- full markdown body
        );
        """
    )

    if not conn.execute("SELECT 1 FROM article LIMIT 1").fetchone():
        for slug, meta in _INITIAL_ARTICLES.items():
            conn.execute(
                "INSERT INTO article(slug, title, description) VALUES (?,?,?)",
                (slug, meta["title"], meta["description"]),
            )
            article_id = conn.execute("SELECT id FROM article WHERE slug = ?", (slug,)).fetchone()[0]
            conn.execute(
                "INSERT INTO article_revision(article_id, session_date, source, content_md, updated_at) VALUES (?,?,?,?,?)",
                (article_id, None, "HUMAN", meta["body"], '1970-01-01T00:00:00'),
            )
        conn.commit()


def _get_conn() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _init_db(conn)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        raise

# ---------------------------------------------------------------------------
# HELPER UTILITIES ------------------------------------------------------------
class ArticleMeta(TypedDict):
    slug: str
    title: str
    description: str


def _safe_date(raw: Optional[str]) -> date:
    """Parse `YYYY-MM-DD`. Fallback to today() on None/invalid."""
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.today()


def list_articles_meta() -> List[ArticleMeta]:
    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT slug, title, description FROM article ORDER BY slug").fetchall()
        return [{"slug": r["slug"], "title": r["title"], "description": r["description"]} for r in rows]
    except sqlite3.Error as e:
        logging.error(f"Error listing articles: {e}")
        return []


def latest_revision_for_date(slug: str, cutoff: date) -> Tuple[Optional[str], Optional[float]]:
    """Given a slug and cutoff date, return the most recent version and timestamp as of that date (inclusive).
    
    Args:
        slug: The article slug
        cutoff: The date to get the article as of (inclusive)
        
    Returns:
        A tuple of (content, timestamp) where both can be None if not found
    """
    # Retrieve both content and timestamp information
    sql = """
    SELECT r.content_md, COALESCE(r.session_date, DATE(r.updated_at)) as revision_date, r.updated_at
    FROM article_revision r
    JOIN article a ON a.id = r.article_id
    WHERE a.slug = ?
      AND (COALESCE(r.session_date, DATE(r.updated_at)) <= ?)
    ORDER BY COALESCE(r.session_date, DATE(r.updated_at)) DESC,
             r.updated_at DESC
    LIMIT 1;
    """
    try:
        with _get_conn() as conn:
            row = conn.execute(sql, (slug, cutoff.isoformat())).fetchone()
            
            if not row:
                return (None, None)
                
            content = row[0]
            timestamp = None
            
            # Convert the updated_at timestamp
            import time
            from datetime import datetime
            
            # Always use the updated_at timestamp - it will always exist
            try:
                dt = datetime.fromisoformat(row[2].replace(' ', 'T'))
                timestamp = dt.timestamp()
            except (ValueError, TypeError):
                # Fall back to current time if parsing fails
                timestamp = time.time()
                
            return (content, timestamp)
    except sqlite3.Error as e:
        logging.error(f"Database error in latest_revision_for_date: {e}")
        return (None, None)





def insert_revision(slug: str, content_md: str, *, session_date: Optional[date], source: str) -> None:
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT id FROM article WHERE slug = ?", (slug,)).fetchone()
            if row is None:
                raise ValueError(f"Unknown article '{slug}'. Use admin flow to create new campaign-memory entries.")
            article_id = row[0]
            conn.execute(
                "INSERT INTO article_revision(article_id, session_date, source, content_md) VALUES (?,?,?,?)",
                (article_id, session_date.isoformat() if session_date else None, source, content_md),
            )
            conn.commit()
    except (sqlite3.Error, ValueError) as e:
        logging.error(f"Error inserting revision for {slug}: {e}")
        raise

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AGENT SDK TOOLS -------------------------------------------------------------

@function_tool
def list_articles() -> List[ArticleMeta]:
    """Return a list of campaign memory articles.

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

    Parameters
    ----------
    wrapper : RunContextWrapper[SessionContext]
        The context wrapper containing session information.
    slugs : List[str]
        List of slugs from `list_articles`.
    Returns
    -------
    Dict[str, str]: Mapping of slug to markdown body as of the session date (empty string if not found).
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
    Append a new revision (no overwrite) to `slug`.

    Parameters
    ----------
    wrapper : RunContextWrapper[SessionContext]
        The context wrapper containing session information.
    slug : str
        Target article slug.
    content_md : str
        **Entire replacement** markdown body for the article.
    source : str
        Source of the update. Defaults to "LLM". Can be "HUMAN" or other identifiers.
    Returns
    -------
    "ok" on success.
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


# ---------------------------------------------------------------------------
# SELF-TEST CODE ------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print(f"\n{'='*80}\nCampaign Memory Tools Self-Test\n{'='*80}")
    
    # List all articles
    articles = list_articles_meta()
    print(f"\nFound {len(articles)} articles in the database:\n")
    
    # Display article metadata
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']} ({article['slug']})")
        print(f"   Description: {article['description']}")
    
    # Get the content of each article
    print(f"\n{'='*80}\nArticle Contents\n{'='*80}")
    for article in articles:
        slug = article['slug']
        from datetime import timedelta
        cutoff = date.today()
        content = latest_revision_for_date(slug, cutoff)[0] or ""
        print(f"\n\n{'*'*80}\n{article['title']} ({slug})\n{'*'*80}")
        print(content[:500] + ("..." if len(content) > 500 else ""))
    
    print(f"\n{'='*80}\nSelf-Test Completed Successfully\n{'='*80}")

