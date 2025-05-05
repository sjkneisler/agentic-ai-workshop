"""
LangGraph node for performing web searches using the Serper API.
"""
import warnings
from typing import Dict, Any

# State and Config
from agent.state import AgentState
# Assuming search config might be needed, though serper_search handles it internally
# from agent.config import get_search_config

# Tool/Function Import
from agent.search import serper_search # Import the actual search function

# Shared Utilities
from agent.utils import print_verbose

# --- LangGraph Node ---

def search_node(state: AgentState) -> Dict[str, Any]:
    """
    Performs a web search based on the query in state['current_query']
    and updates state['search_results'].
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"):
        if is_verbose: print_verbose("Skipping search due to previous error.", style="yellow")
        return {}

    if is_verbose: print_verbose("Entering Search Node", style="magenta")

    query = state.get('current_query')
    if not query:
        error_msg = "No query provided for search node."
        if is_verbose: print_verbose(error_msg, style="red")
        # Clear results and set error
        return {"error": error_msg, "search_results": [], "current_query": None}

    if is_verbose: print_verbose(f"Performing web search for: '{query}'", style="dim blue")

    try:
        # Call the underlying search function
        # Let serper_search handle num_results based on its config access
        results = serper_search(query=query, n=None, verbose=is_verbose) # Pass verbosity
        urls = [result.get("link", "N/A") for result in results if result.get("link")]

        if is_verbose: print_verbose(f"Search returned {len(results)} results.", style="green")

        # Update state with results and clear the query
        return {
            "search_results": results,
            "web_source_urls": state.get("web_source_urls", []) + urls, # Append new URLs? Or replace? Let's append for now.
            "current_query": None, # Clear query after use
            "error": None
            }
    except RuntimeError as e: # Catch missing API key error specifically
        error_msg = f"Search step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "search_results": [], "current_query": None}
    except Exception as e:
        error_msg = f"Search step failed with unexpected error: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "search_results": [], "current_query": None}