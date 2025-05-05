"""
Agent module for reasoning over gathered information.

Combines information from various sources (e.g., web search, RAG)
into a coherent context string suitable for synthesis.
"""
from typing import List, Dict, Any

# Shared Utilities (Logging)
from .utils import print_verbose # Import shared logging

# Agent State (for LangGraph node)
from agent.state import AgentState # Import the shared state


def reason_over_sources(search_results: List[Dict[str, Any]], rag_context: str, verbose: bool = False) -> str:
    """
    Reasons over the collected information from search and RAG by concatenating them.

    Args:
        search_results: A list of dictionaries from the search module (expecting 'title', 'link', 'snippet').
        rag_context: A string containing context from the RAG module.
        verbose: Flag for detailed output.

    Returns:
        A string representing the combined context. Returns a default message
        if no information was gathered.
    """
    if verbose:
        # Use imported print_verbose
        print_verbose(f"Received {len(search_results)} search results.", title="Reasoning Over Sources")
        if rag_context:
            print_verbose("Received RAG context.", style="dim blue")
        else:
            print_verbose("No RAG context received.", style="yellow")

    combined_context_parts = []

    if search_results:
        search_summary = "Web Search Results:\n"
        for i, res in enumerate(search_results):
            title = res.get('title', 'N/A')
            snippet = res.get('snippet', 'N/A')
            link = res.get('link', 'N/A')
            search_summary += f"{i+1}. {title}\n   Snippet: {snippet}\n   Source: {link}\n"
        combined_context_parts.append(search_summary.strip())

    if rag_context:
        rag_summary = f"Relevant Information from Local Documents (RAG):\n{rag_context}"
        combined_context_parts.append(rag_summary)

    if not combined_context_parts:
        final_context = "No information gathered from search or RAG."
        if verbose:
            print_verbose("No sources to reason over.", style="yellow")
    else:
        final_context = "\n\n---\n\n".join(combined_context_parts)
        if verbose:
            print_verbose("Combined context generated.", style="green")
            # print_verbose(f"Context:\n{final_context}", style="dim") # Potentially too verbose

    return final_context

# --- LangGraph Node ---

def reason_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to reason over collected sources."""
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping reasoning due to previous error.", style="yellow")
         return {}

    if is_verbose: print_verbose("Entering Reasoning Node", style="magenta")

    try:
        # Ensure defaults if steps were skipped or failed partially
        search_res = state.get('search_results', [])
        rag_ctx = state.get('rag_context', "")

        # Call the main logic function from this module
        combined = reason_over_sources(search_res, rag_ctx, verbose=is_verbose)
        # Verbose printing is handled within reason_over_sources
        # Update the state
        return {"combined_context": combined, "error": None}
    except Exception as e:
        error_msg = f"Reasoning step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Update state with error
        return {"error": error_msg}

# Optional: Add reason_node to __all__
# __all__ = ['reason_over_sources', 'reason_node']