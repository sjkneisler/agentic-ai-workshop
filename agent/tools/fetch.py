"""
Tool for fetching and extracting content from a URL.
"""
import warnings
from typing import Dict, Any
import requests # Import the requests library
from requests_html import HTMLSession, MaxRetries
from langchain_core.tools import tool

# Shared Utilities (Logging) - might need later
# from ..utils import print_verbose

@tool
def fetch_url(url: str) -> Dict[str, Any]:
    """
    Fetches the HTML content and title from a given URL.

    Use this tool to get the full content of a webpage identified by a URL,
    typically found from a web search result.

    Args:
        url: The URL of the webpage to fetch.

    Returns:
        A dictionary containing:
        - 'url': The original URL fetched.
        - 'title': The title of the webpage.
        - 'html': The raw HTML content of the page's body.
        Returns {'error': message} if fetching fails.
    """
    session = HTMLSession()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # Use GET request with headers and timeout
        response = session.get(url, headers=headers, timeout=15) # 15 second timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # --- Content Extraction ---
        # Attempt to render JavaScript - might be slow or unnecessary often
        # Consider making this optional or removing if causing issues
        # try:
        #     response.html.render(timeout=20) # Render JS with timeout
        # except MaxRetries as e:
        #     warnings.warn(f"JavaScript rendering timed out for {url}: {e}. Proceeding with static HTML.")
        # except Exception as e:
        #     warnings.warn(f"Error rendering JavaScript for {url}: {e}. Proceeding with static HTML.")

        title_element = response.html.find('title', first=True)
        title = title_element.text if title_element else "No title found"

        # Get HTML content - start with body, refinement needed for main content extraction
        body_element = response.html.find('body', first=True)
        html_content = body_element.html if body_element else response.html.html # Fallback to full HTML

        # Basic boilerplate removal (example - needs improvement)
        # This is simplistic; libraries like trafilatura are better for this.
        # selectors_to_remove = ['nav', 'footer', 'header', 'aside', 'script', 'style']
        # for selector in selectors_to_remove:
        #     for element in response.html.find(selector):
        #         html_content = html_content.replace(element.outer_html, '')


        return {
            "url": url,
            "title": title.strip(),
            "html": html_content.strip() # Return the HTML string
        }

    except requests.exceptions.RequestException as e: # Use requests.exceptions
        error_msg = f"Network error fetching {url}: {e}"
        warnings.warn(error_msg)
        return {"error": error_msg, "url": url}
    except Exception as e:
        error_msg = f"Error processing {url}: {e}"
        warnings.warn(error_msg)
        return {"error": error_msg, "url": url}
    finally:
        session.close()

# Example Usage (for testing)
if __name__ == '__main__':
    test_url = "https://example.com"
    result = fetch_url(test_url)
    if 'error' in result:
        print(f"Error fetching {test_url}: {result['error']}")
    else:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        # print(f"HTML (first 500 chars): {result['html'][:500]}...") # Be careful printing large HTML
        print("HTML fetched successfully.")