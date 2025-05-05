import re
from pathlib import Path
import warnings
from typing import Optional, List, Tuple

# --- Helper Functions for Link Processing ---

def extract_links(content: str) -> List[Tuple[str, str]]:
    """Extracts Markdown and Wiki-style links from text content."""
    links = []
    # Markdown links: [text](target)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, target in markdown_links:
        links.append((text, target.strip()))

    # Wiki links: [[target]] or [[target|text]]
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
    for link_content in wiki_links:
        parts = link_content.split('|', 1)
        target = parts[0].strip()
        text = parts[1].strip() if len(parts) > 1 else target
        # Assume wiki links might need .md appended if not present
        # Check specifically for file extensions we support for linking
        if not any(target.lower().endswith(ext) for ext in ['.md', '.txt']):
             target += ".md" # Default to .md if no supported extension
        links.append((text, target))

    return links

def is_web_link(link_target: str) -> bool:
    """Checks if a link target is a web URL."""
    return link_target.startswith('http://') or link_target.startswith('https://')

def resolve_link(link_target: str, current_file_path: Path, root_path: Path) -> Optional[Path]:
    """
    Resolves an internal link target using the B -> A -> C strategy.
    B: Relative to root_path
    A: Relative to current_file_path's parent directory
    C: Recursive search within root_path
    """
    target_path = None

    # Strategy B: Relative to root_path
    try:
        try_path_b = (root_path / link_target).resolve()
        if try_path_b.is_file():
            target_path = try_path_b
            # print(f"DEBUG: Resolved '{link_target}' via Strategy B: {target_path}")
            return target_path
    except Exception: # Catch potential errors during path resolution/checking
        pass

    # Strategy A: Relative to current file's directory
    try:
        # Ensure current_file_path is a file before getting parent
        if current_file_path.is_file():
             try_path_a = (current_file_path.parent / link_target).resolve()
             if try_path_a.is_file():
                 target_path = try_path_a
                 # print(f"DEBUG: Resolved '{link_target}' via Strategy A: {target_path}")
                 return target_path
    except Exception:
        pass

    # Strategy C: Recursive search within root_path
    # This can be slow for large directories, use with caution or optimize
    # We need the filename part of the link_target for searching
    link_filename = Path(link_target).name
    try:
        # Use rglob to find the first match
        found_files = list(root_path.rglob(f"**/{link_filename}"))
        if found_files:
            # Resolve to handle potential relative paths from rglob
            target_path = found_files[0].resolve()
            # print(f"DEBUG: Resolved '{link_target}' via Strategy C: {target_path}")
            return target_path
    except Exception as e:
        warnings.warn(f"Error during recursive search for '{link_filename}' in {root_path}: {e}")

    # print(f"DEBUG: Failed to resolve '{link_target}' from {current_file_path}")
    return None