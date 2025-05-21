#!/usr/bin/env python
"""
Combine multiple markdown files from the Summaries folder and convert them to DOCX.

This script:
1. Processes all session-summary markdown files from the Summaries folder
2. Combines them into one document
3. Converts it to DOCX format with Arial font
4. Does the same for session-narrative files
5. Results in two DOCX files in the Summaries folder

Usage:
  python publish_docx.py
"""

from pathlib import Path
import tempfile
import re
import os
import subprocess

# ---- constants -------------------------------------------------------------

# Base directory for the project
BASE_DIR = Path(__file__).parent

# Summaries directory
SUMMARIES_DIR = BASE_DIR / "Summaries"

# Document titles
SUMMARY_DOC_TITLE = "Teghrim's Crossing - Session Summaries"
NARRATIVE_DOC_TITLE = "Teghrim's Crossing - A Narrative Tale"

# ---- helper functions ------------------------------------------------------

def create_reference_docx(output_path: Path) -> bool:
    """Create a reference DOCX file with Arial font.
    
    Args:
        output_path: Path to save the reference DOCX file
        
    Returns:
        bool: True if creation was successful, False otherwise
    """
    try:
        # Create a simple markdown file with style definitions
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md_file:
            temp_md_path = Path(temp_md_file.name)
            # Define a document with basic styles using Arial font
            temp_md_file.write("""
# Heading 1

This is normal text in Arial font.

## Heading 2

More text with **bold** and *italic* formatting.

### Heading 3

- Bullet point 1
- Bullet point 2

1. Numbered item 1
2. Numbered item 2
            """)
        
        # Create a CSS file to define styles
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False, encoding='utf-8') as temp_css_file:
            temp_css_path = Path(temp_css_file.name)
            # Define CSS with Arial font for all elements
            temp_css_file.write("""
            body { font-family: Arial, sans-serif; font-size: 11pt; }
            h1, h2, h3, h4, h5, h6 { font-family: Arial, sans-serif; }
            p { font-family: Arial, sans-serif; }
            li { font-family: Arial, sans-serif; }
            """)
        
        try:
            # Convert the markdown to DOCX with the CSS styling
            result = subprocess.run(
                [
                    'pandoc',
                    str(temp_md_path),
                    '-o', str(output_path),
                    '--css', str(temp_css_path),
                    '--standalone'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        finally:
            # Clean up temporary files
            temp_md_path.unlink(missing_ok=True)
            temp_css_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"Error creating reference DOCX: {e}")
        return False

def convert_markdown_to_docx(md_path: Path, output_path: Path) -> bool:
    """Convert a markdown file to DOCX using Pandoc.
    
    Args:
        md_path: Path to the markdown file
        output_path: Path to save the DOCX file
        
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        # Create a temporary reference DOCX file with Arial font
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_ref_file:
            reference_docx_path = Path(temp_ref_file.name)
        
        print("Creating temporary reference DOCX template...")
        if not create_reference_docx(reference_docx_path):
            print("Warning: Could not create reference DOCX. Will use default styling.")
            reference_docx_path = None
        
        # Read the markdown content
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a modified version of the content that avoids bookmark issues
        # Replace heading markdown with plain text but keep the content
        # This prevents Pandoc from creating automatic bookmarks for headings
        modified_content = re.sub(r'^(#+)\s+(.*?)$', r'**\2**', content, flags=re.MULTILINE)
        
        # Create a temporary file with the modified content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md_file:
            temp_md_path = Path(temp_md_file.name)
            temp_md_file.write(modified_content)
        
        try:
            # Build the pandoc command
            pandoc_cmd = [
                'pandoc',
                str(temp_md_path),
                '-f', 'markdown-auto_identifiers',  # Disable automatic identifiers
                '-t', 'docx',
                '-o', str(output_path),
                '--standalone',
                '--wrap=none',
                '--no-highlight'  # Disable syntax highlighting which can add bookmarks
            ]
            
            # Add reference docx if available
            if reference_docx_path and reference_docx_path.exists():
                pandoc_cmd.extend(['--reference-doc', str(reference_docx_path)])
            
            # Run pandoc with options that avoid creating bookmarks
            result = subprocess.run(
                pandoc_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Created DOCX file: {output_path}")
            return True
        finally:
            # Clean up temporary files
            temp_md_path.unlink(missing_ok=True)
            if reference_docx_path and reference_docx_path.exists():
                reference_docx_path.unlink(missing_ok=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting markdown to DOCX: {e}")
        print(f"Pandoc output: {e.stdout}")
        print(f"Pandoc error: {e.stderr}")
        
        # Try a simpler fallback approach if the first method fails
        try:
            print("Trying simpler conversion method...")
            # For the fallback, use a different approach - convert to HTML first with Arial font
            html_path = output_path.with_suffix('.html')
            
            # Create a CSS file with Arial font
            with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False, encoding='utf-8') as temp_css_file:
                css_path = Path(temp_css_file.name)
                temp_css_file.write("""
                body { font-family: Arial, sans-serif; }
                h1, h2, h3, h4, h5, h6 { font-family: Arial, sans-serif; }
                p { font-family: Arial, sans-serif; }
                """)
            
            # First convert markdown to HTML with CSS
            result1 = subprocess.run(
                [
                    'pandoc',
                    str(md_path),
                    '-o', str(html_path),
                    '--css', str(css_path),
                    '--standalone',
                    '--wrap=none'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Then convert HTML to DOCX
            result2 = subprocess.run(
                [
                    'pandoc',
                    str(html_path),
                    '-o', str(output_path),
                    '--standalone'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Clean up temporary files
            html_path.unlink(missing_ok=True)
            css_path.unlink(missing_ok=True)
            
            print(f"✓ Created DOCX file: {output_path}")
            return True
        except Exception as fallback_e:
            print(f"Fallback conversion also failed: {fallback_e}")
            return False
    except Exception as e:
        print(f"Unexpected error converting markdown to DOCX: {e}")
        return False

def extract_date_from_filename(filename: str) -> str:
    """Extract date from filename like 'session-summary-2025-05-16.md'."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else ""

def combine_markdown_files(file_pattern: str, add_title: bool = False, title: str = None) -> tuple[str, list[Path]]:
    """Concatenate markdown files matching the pattern into a single string, optionally prepending a title.
    Args:
        file_pattern: Pattern to match files
        add_title: Whether to add a title at the top
        title: The title to add (as H1)
    Returns:
        tuple: (combined markdown content, list of files processed)
    """
    files = sorted(SUMMARIES_DIR.glob(file_pattern), 
                   key=lambda x: extract_date_from_filename(x.name), 
                   reverse=True)
    if not files:
        print(f"No files found matching pattern: {file_pattern}")
        return "", []
    combined_content = []
    if add_title and title:
        combined_content.append(f"# {title}\n\n")
    for idx, file in enumerate(files):
        with open(file, 'r') as f:
            content = f.read()
            combined_content.append(content)
        if idx < len(files) - 1:
            combined_content.append("\n\n")
    return "".join(combined_content), files

def process_markdown_to_docx(title: str, file_pattern: str, add_title: bool = False) -> bool:
    """Process markdown files to DOCX.
    Args:
        title: Title for the document
        file_pattern: Pattern to match files
        add_title: Whether to add a title to the combined markdown
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Combine markdown files
    content, files = combine_markdown_files(file_pattern, add_title, title)
    if not files:
        return False
    print(f"Found {len(files)} files matching {file_pattern}")
    # Generate filename for the DOCX and MD files
    docx_path = SUMMARIES_DIR / f"{title}.docx"
    md_path = SUMMARIES_DIR / f"{title}.md"
    # Write the combined markdown to a permanent file
    with open(md_path, 'w', encoding='utf-8') as md_file:
        md_file.write(content)
    # Convert to DOCX
    success = convert_markdown_to_docx(md_path, docx_path)
    if success:
        print(f"✓ Successfully created {docx_path}")
        print(f"✓ Markdown file saved as {md_path}")
        return True
    else:
        print(f"Failed to create {docx_path}")
        return False

# ---- main ------------------------------------------------------------------

def main():
    print("\nProcessing session summaries...")
    # Summaries: concatenate as-is, no headers/titles added
    process_markdown_to_docx(SUMMARY_DOC_TITLE, "session-summary-*.md", add_title=False)
    
    print("\nProcessing session narratives...")
    # Narrative: add title at top
    process_markdown_to_docx(NARRATIVE_DOC_TITLE, "session-narrative-*.md", add_title=True)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
