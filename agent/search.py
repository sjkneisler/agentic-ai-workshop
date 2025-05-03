"""
Agent module for performing web searches.

Uses the Serper API (serpapi.serper.dev) to gather information from the web.
Requires the SERPER_API_KEY environment variable to be set.
"""
import os
import requests
import json
import certifi
from typing import List, Dict, Any, Optional
from .config import get_search_config # Import config loader

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
        print("--- Performing Web Search ---")
        print(f"Searching for: {query} (n={num_results})")

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
            print(f"Found {len(results)} results via Serper.")

    except requests.exceptions.RequestException as e:
        print(f"Error during Serper API call: {e}")
        if verbose:
            print(f"Response status: {response.status_code if 'response' in locals() else 'N/A'}")
            print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
        # Return empty list on error
        results = []
    except json.JSONDecodeError:
        print("Error decoding JSON response from Serper API.")
        if verbose:
             print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
        results = []


    return results[:num_results] # Ensure we don't return more than requested if API gives more