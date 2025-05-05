"""
Agent module for performing web searches.

Uses the Serper API (serpapi.serper.dev) to gather information from the web.
Requires the SERPER_API_KEY environment variable to be set.
"""
import os
import requests
import json
import certifi
import warnings # Import warnings for error handling consistency
from typing import List, Dict, Any, Optional

# Shared Utilities (Logging)
from .utils import print_verbose # Import shared logging

# Config
from .config import get_search_config # Import config loader

# Agent State (for LangGraph node)
from agent.state import AgentState # Import the shared state


def serper_search(query: str, n: Optional[int] = None, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Performs a web search using the Serper API.

    Args:
        query: The search query string.
        n: The number of results to return. If None, uses the value from config.yaml.
        verbose: Flag for detailed output.

    Returns:
        A list of dictionaries, where each dictionary represents a search result
        containing 'title', 'link', and 'snippet'. Returns an empty list
        if the search fails or the API key is missing.

    Raises:
        RuntimeError: If the SERPER_API_KEY environment variable is not set.
    """
    search_config = get_search_config()
    num_results = n if n is not None else search_config.get('num_results', 5) # Use arg 'n' if provided, else config, else default 5

    if verbose:
        # Use imported print_verbose
        print_verbose(f"Searching for: {query} (n={num_results})", title="Performing Web Search")

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise RuntimeError("SERPER_API_KEY environment variable not set. Cannot perform web search.")

    search_url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        "q": query,
        "num": num_results # Use configured/determined number of results
    })

    results = []
    response = None # Initialize response to None
    try:
        response = requests.post(search_url, headers=headers, data=payload, verify=certifi.where()) # Added verify parameter
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        search_data = response.json()

        # Extract relevant fields (adjust based on actual Serper API response structure)
        if 'organic' in search_data:
            for item in search_data['organic']:
                results.append({
                    "title": item.get("title", "N/A"),
                    "link": item.get("link", "N/A"),
                    "snippet": item.get("snippet", "N/A")
                })
        if verbose:
            # Use imported print_verbose
            print_verbose(f"Found {len(results)} results via Serper.", style="dim blue")

    except requests.exceptions.RequestException as e:
        # Use imported print_verbose for errors too
        print_verbose(f"Error during Serper API call: {e}", style="red")
        if verbose:
            print_verbose(f"Response status: {response.status_code if response else 'N/A'}", style="red")
            print_verbose(f"Response text: {response.text if response else 'N/A'}", style="red")
        # Return empty list on error
        results = []
    except json.JSONDecodeError:
        # Use imported print_verbose
        print_verbose("Error decoding JSON response from Serper API.", style="red")
        if verbose:
             print_verbose(f"Response text: {response.text if response else 'N/A'}", style="red")
        results = []


    return results[:num_results] # Ensure we don't return more than requested if API gives more

# --- LangGraph Node ---

def search_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to perform web search."""
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping search due to previous error.", style="yellow")
         return {}

    if is_verbose: print_verbose("Entering Search Node", style="cyan")

    try:
        # Call the main logic function from this module
        # Pass None for 'n' so it uses the config value by default
        results = serper_search(state['clarified_question'], n=None, verbose=is_verbose)
        urls = [result.get("link", "N/A") for result in results if result.get("link")]
        # Verbose printing is handled within serper_search
        # Update the state
        return {"search_results": results, "web_source_urls": urls, "error": None}
    except RuntimeError as e: # Catch the specific error raised for missing API key
        error_msg = f"Search step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Search step failed with unexpected error: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Update state with error
        return {"error": error_msg}

# Optional: Add search_node to __all__
# __all__ = ['serper_search', 'search_node']