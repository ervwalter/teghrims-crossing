#!/usr/bin/env python
"""
Utilities for accessing and processing reference data such as player rosters and world information.
"""

import os
import re
import yaml
from typing import List, Dict
from agents import function_tool


def extract_yaml_frontmatter(content: str) -> dict:
    """
    Extract YAML frontmatter from markdown content.
    
    Args:
        content: The markdown content containing frontmatter
        
    Returns:
        dict: Extracted frontmatter as a dictionary
    """
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        try:
            return yaml.safe_load(frontmatter)
        except Exception:
            return {}
    return {}


def get_player_roster():
    """
    Read the player roster file and extract the content without frontmatter.
    
    Returns:
        str: Player roster content without frontmatter
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        roster_path = os.path.join(base_dir, "references", "player-roster.md")
        
        if not os.path.exists(roster_path):
            return ""
        
        with open(roster_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove frontmatter if present
        frontmatter_pattern = r'^---\s*\n.*?\n---\s*\n'
        roster_content = re.sub(frontmatter_pattern, '', content, flags=re.DOTALL)
        return roster_content.strip()
    except Exception as e:
        print(f"Error reading player roster: {str(e)}")
        return ""


@function_tool
def list_reference_files() -> List[Dict[str, str]]:
    """
    List all available reference files in the references directory with descriptions.
    Returns a list of dictionaries containing filename and description for each markdown file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    references_dir = os.path.join(base_dir, "references")
    if not os.path.exists(references_dir):
        return [{"filename": "error", "description": "references directory not found"}]
    
    result = []
    for filename in [f for f in os.listdir(references_dir) if f.endswith(".md")]:
        file_path = os.path.join(references_dir, filename)
        description = "No description available"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                meta = extract_yaml_frontmatter(content)
                if meta and isinstance(meta, dict) and 'description' in meta:
                    description = meta['description']
                else:
                    heading_match = re.search(r'^#+\s+(.+?)\n', content)
                    if heading_match:
                        description = heading_match.group(1).strip()
                    else:
                        first_para = re.split(r'\n\s*\n', content)[0].strip()
                        description = first_para[:150]
                        if len(first_para) > 150:
                            description += "..."
        except Exception as e:
            description = f"Error reading file: {str(e)}"
        result.append({"filename": filename, "description": description})
    return result


@function_tool
def retrieve_reference_files(filenames: List[str]) -> dict:
    """
    Retrieve the contents of one or more reference files.
    
    Args:
        filenames: A list of filenames to retrieve from the references directory.
                   Do not include paths, just the filename with extension.
    
    Returns:
        A dictionary mapping filenames to their contents.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    references_dir = os.path.join(base_dir, "references")
    
    if not os.path.exists(references_dir):
        return {"error": "references directory not found"}
    
    result = {}
    for filename in filenames:
        file_path = os.path.join(references_dir, filename)
        if os.path.exists(file_path) and filename.endswith(".md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    result[filename] = f.read()
            except Exception as e:
                result[filename] = f"Error reading file: {str(e)}"
        else:
            result[filename] = f"File not found: {filename}"
    
    return result
