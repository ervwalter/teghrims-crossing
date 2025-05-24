"""
Markdown to Notion converter for Teghrim's Crossing project.

This module provides functions to convert Markdown content to Notion API block format
using proper AST-based parsing for robustness.
"""
import re
import io
from typing import Dict, List, Optional, Union, Any
from mistletoe import Document
from mistletoe.block_token import (
    Heading, Paragraph, BlockCode, Quote, List as ListToken, 
    ListItem, TableRow, TableCell, ThematicBreak
)
from mistletoe.span_token import (
    Strong, Emphasis, InlineCode, Link, Image, RawText
)



class NotionBlockRenderer:
    """
    Renderer that converts mistletoe's Markdown AST to Notion blocks.
    Works directly with the AST, no HTML intermediate step.
    """
    def __init__(self):
        self.blocks = []
        self.list_nesting_level = 0
    def render(self, document):
        for token in document.children:
            self.render_token(token)
        return self.blocks
    def render_token(self, token):
        if isinstance(token, Heading):
            self._render_heading(token)
        elif isinstance(token, Paragraph):
            self._render_paragraph(token)
        elif isinstance(token, BlockCode):
            self._render_code_block(token)
        elif isinstance(token, Quote):
            self._render_quote(token)
        elif isinstance(token, ListToken):
            self._render_list(token)
        elif isinstance(token, ThematicBreak):
            self._render_thematic_break()
    def _render_heading(self, token):
        level = min(token.level, 3)
        heading_type = f"heading_{level}"
        self.blocks.append({
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": self._render_span_tokens(token.children)
            }
        })
    def _render_paragraph(self, token):
        if not token.children or (len(token.children) == 1 and isinstance(token.children[0], RawText) and not token.children[0].content.strip()):
            return
        self.blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._render_span_tokens(token.children)
            }
        })
    def _render_code_block(self, token):
        language = token.language or "plain_text"
        language_map = {"py": "python", "js": "javascript", "ts": "typescript", "rb": "ruby", "md": "markdown", "bash": "shell", "sh": "shell"}
        mapped_language = language_map.get(language.lower(), language.lower())
        self.blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": token.children[0].content}
                }],
                "language": mapped_language
            }
        })
    def _render_quote(self, token):
        rich_text = []
        for child in token.children:
            rich_text.extend(self._render_span_tokens(child.children))
            if child != token.children[-1]:
                rich_text.append({
                    "type": "text",
                    "text": {"content": "\n"}
                })
        self.blocks.append({
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": rich_text
            }
        })
    def _render_list(self, token):
        self.list_nesting_level += 1
        for item in token.children:
            self._render_list_item(item, token.start is not None)
        self.list_nesting_level -= 1
    def _render_list_item(self, token, is_ordered):
        list_type = "numbered_list_item" if is_ordered else "bulleted_list_item"
        rich_text = []
        for child in token.children:
            if not isinstance(child, ListToken):
                rich_text.extend(self._render_span_tokens(child.children))
        if self.list_nesting_level > 1:
            if rich_text and rich_text[0]["type"] == "text":
                content = rich_text[0]["text"]["content"]
                rich_text[0]["text"]["content"] = "  " * (self.list_nesting_level - 1) + content
        list_item_block = {
            "object": "block",
            "type": list_type,
            list_type: {
                "rich_text": rich_text,
                "color": "default"
            }
        }
        self.blocks.append(list_item_block)
        for child in token.children:
            if isinstance(child, ListToken):
                self._render_list(child)
    def _render_thematic_break(self):
        self.blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
    def _render_span_tokens(self, tokens):
        rich_text = []
        for token in tokens:
            if isinstance(token, RawText):
                if token.content:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": token.content},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "code": False,
                            "color": "default",
                            "strikethrough": False,
                            "underline": False
                        }
                    })
            elif isinstance(token, Strong):
                for child in token.children:
                    if isinstance(child, RawText) and child.content:
                        rich_text.append({
                            "type": "text",
                            "text": {"content": child.content},
                            "annotations": {
                                "bold": True,
                                "italic": False,
                                "code": False,
                                "color": "default",
                                "strikethrough": False,
                                "underline": False
                            }
                        })
            elif isinstance(token, Emphasis):
                for child in token.children:
                    if isinstance(child, RawText) and child.content:
                        rich_text.append({
                            "type": "text",
                            "text": {"content": child.content},
                            "annotations": {
                                "bold": False,
                                "italic": True,
                                "code": False,
                                "color": "default",
                                "strikethrough": False,
                                "underline": False
                            }
                        })
            elif isinstance(token, InlineCode):
                if token.children[0].content:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": token.children[0].content},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "code": True,
                            "color": "default",
                            "strikethrough": False,
                            "underline": False
                        }
                    })
            elif isinstance(token, Link):
                link_text = "".join(child.content for child in token.children if isinstance(child, RawText))
                if link_text:
                    rich_text.append({
                        "type": "text",
                        "text": {
                            "content": link_text,
                            "link": {"url": token.target}
                        },
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "code": False,
                            "color": "default",
                            "strikethrough": False,
                            "underline": True
                        }
                    })
        return rich_text



def markdown_to_notion_blocks(markdown_text: str) -> List[Dict]:
    """
    Convert markdown text to Notion blocks using direct mistletoe AST parsing.
    
    Args:
        markdown_text: Markdown text to convert
        
    Returns:
        List of Notion blocks representing the markdown content
    """
    # Parse markdown directly to AST
    document = Document(markdown_text)
    
    # Render AST to Notion blocks
    renderer = NotionBlockRenderer()
    blocks = renderer.render(document)
    
    # Post-process to handle task lists and other special cases
    processed_blocks = post_process_blocks(blocks, markdown_text)
    
    return processed_blocks


def post_process_blocks(blocks: List[Dict], original_markdown: str) -> List[Dict]:
    """
    Apply additional processing to blocks after initial conversion.
    
    Args:
        blocks: Initial Notion blocks
        original_markdown: Original markdown text for reference
        
    Returns:
        Processed blocks
    """
    processed_blocks = []
    
    # Process normal content blocks
    for block in blocks:
        # Skip empty blocks
        if block["type"] in ["paragraph", "heading_1", "heading_2", "heading_3", "quote"]:
            rich_text = block[block["type"]].get("rich_text", [])
            if not rich_text or (len(rich_text) == 1 and not rich_text[0]["text"]["content"].strip()):
                continue
        
        # Add the block to the processed blocks
        processed_blocks.append(block)
    
    # Look for patterns in the original markdown that might have been missed
    # Like task lists
    lines = original_markdown.split('\n')
    task_blocks = []
    
    for line in lines:
        line = line.strip()
        if re.match(r'^\*\s\[([ xX])\]\s(.*)', line) or re.match(r'^-\s\[([ xX])\]\s(.*)', line):
            match = re.match(r'^[*-]\s\[([ xX])\]\s(.*)', line)
            if match:
                checked = match.group(1).lower() == 'x'
                content = match.group(2)
                task_blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": content},
                            "annotations": {
                                "bold": False,
                                "italic": False,
                                "code": False,
                                "color": "default",
                                "strikethrough": False,
                                "underline": False
                            }
                        }],
                        "checked": checked
                    }
                })
    
    # Merge task blocks with processed blocks if they aren't already represented
    # In a real implementation, you would need a more sophisticated approach
    # to determine where to insert these blocks
    if task_blocks:
        # For simplicity, we'll just append them at the end
        processed_blocks.extend(task_blocks)
    
    return processed_blocks


def rich_text_from_markdown(markdown_text: str) -> List[Dict]:
    """
    Convert markdown text to Notion rich text objects (for use within blocks).
    """
    with io.StringIO(markdown_text) as f:
        document = Document(f)
    renderer = NotionBlockRenderer()
    for token in document.children:
        if isinstance(token, Paragraph):
            return renderer._render_span_tokens(token.children)
    if document.children:
        return renderer._render_span_tokens(document.children)
    return []


def _self_test_markdown_to_notion():
    """
    Self-test for markdown_to_notion: prints Notion blocks for a sample session summary markdown.
    """
    sample_md = '''
# Session Summary 2025-05-16

## Session Overview
The party journeyed eastward by caravan from Menoth-Derith toward Teghrim’s Crossing, facing perils ranging from territorial aurochs to deadly goblin and orc ambushes.

## Story Developments
The session began with **Arnór Josefson**, the sociable Norn Witch, traveling by trade boat from Ni to Menoth-Derith, accompanied by a cargo of grain and other Norn sailors. Passengers included **Aurelia**, a noble-like Dhampir Rogue, whose quiet vigilance set her apart.

- **Arnór Josefson** established group camaraderie with dice games and later contributed both magical support (Needle Darts, occult intimidation) and practical help (trap setting, flute playing).
- **Aurelia** survived and concealed a deadly snotling encounter, then deftly blended diplomacy and violence as circumstances demanded.
- **Qotal** displayed both humility and heroism: sharing religious insights, channeling spirit magic, building defenses, and using his glowing tattoos to intimidate enemies.

## Combat & Challenges
- The battle against the aurochs tested the group’s creativity: from direct melee to failed intimidation and magical distractions.
- At the caravanserai, Aurelia dispatched snotlings with swift, deadly efficiency.
- The fort defense against Doorkwill’s orc/goblin warband was a brutal melee.

## Quest Updates
- **Primary Objective:** Protect and escort the caravan safely from Menoth-Derith to Teghrim’s Crossing—successfully achieved for this leg.
- **Side Quests:**
  - *Qotal’s Vision/Relic:* Seek the moss-eaten carving in Teghrim’s Crossing.
  - *Aurelia’s Investigation:* Ongoing personal mission for a friend, details undisclosed but supported by group.
'''
    blocks = markdown_to_notion_blocks(sample_md)
    import json
    print(json.dumps(blocks, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    _self_test_markdown_to_notion()

