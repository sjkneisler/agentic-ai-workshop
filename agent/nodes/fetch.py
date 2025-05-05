"""
LangGraph node for fetching content from a URL using the fetch_url tool.
"""
import warnings
from typing import Dict, Any, List

# State and Config
from agent.state import AgentState
# No specific config needed for this node itself

# Tool/Function Import
from agent.tools.fetch import fetch_url # Import the actual fetch tool/function

# Shared Utilities
from agent.utils import print_verbose

# --- LangGraph Node ---

def fetch_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches content from the URL specified in state['url_to_fetch']
    and updates state['fetched_docs'].
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"):
        if is_verbose: print_verbose("Skipping fetch due to previous error.", style="yellow")
        return {}

    if is_verbose: print_verbose("Entering Fetch Node", style="magenta")

    url = state.get('url_to_fetch')
    if not url:
        error_msg = "No URL provided for fetch node."
        if is_verbose: print_verbose(error_msg, style="red")
        # Clear results and set error
        return {"error": error_msg, "fetched_docs": [], "url_to_fetch": None}

    if is_verbose: print_verbose(f"Fetching content from URL: {url}", style="dim blue")

    try:
        # Call the underlying fetch tool/function
        # The fetch_url tool is already decorated with @tool, but we call it directly here.
        result_dict = fetch_url.invoke({"url": url}) # Invoke tool correctly

        if is_verbose:
            if 'error' in result_dict:
                 print_verbose(f"Fetch failed for {url}: {result_dict['error']}", style="yellow")
            else:
                 print_verbose(f"Fetch successful for {url}. Title: '{result_dict.get('title', 'N/A')}'", style="green")

        # Append the result (which might contain an error) to fetched_docs
        # The chunk_embed node should handle potential errors in the fetched data
        current_docs = state.get('fetched_docs', [])
        current_docs.append(result_dict)

        # Update state and clear the URL to fetch
        return {
            "fetched_docs": current_docs,
            "url_to_fetch": None, # Clear URL after attempting fetch
            "error": None # Don't set node error if fetch itself failed, let chunker handle it
            }
    except Exception as e:
        # This catches errors in invoking the tool itself, not errors *returned* by the tool
        error_msg = f"Fetch node failed unexpectedly while trying to fetch {url}: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Clear URL and set error
        return {"error": error_msg, "fetched_docs": state.get('fetched_docs', []), "url_to_fetch": None}