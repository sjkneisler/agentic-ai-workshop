"""
Agent module for reasoning over gathered information.

Combines information from various sources (e.g., web search, RAG)
into a coherent context string suitable for synthesis.
"""
from typing import List, Dict, Any

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
        print("--- Reasoning Over Sources ---")
        print(f"Received {len(search_results)} search results.")
        if rag_context:
            print("Received RAG context.")
        else:
            print("No RAG context received.")

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
            print("No sources to reason over.")
    else:
        final_context = "\n\n---\n\n".join(combined_context_parts)
        if verbose:
            print("Combined context generated.")
            # print(f"Context:\n{final_context}") # Potentially too verbose

    return final_context