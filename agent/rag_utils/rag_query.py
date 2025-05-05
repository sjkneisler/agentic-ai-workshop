"""
Handles querying the RAG vector store.

Uses the initialized RAG state to perform semantic searches,
optionally traverses internal chunk links, and optionally fetches
external web links found in the retrieved context.
"""

import os
import warnings
from pathlib import Path
from typing import Tuple, List, Set, Dict, Any
from collections import deque
import requests
from bs4 import BeautifulSoup
import traceback # Keep for error reporting

# Langchain Imports
from langchain.schema import Document

# --- Local Imports ---
from agent.config import get_rag_config
from agent.rag_utils.ingestion import extract_links, is_web_link # Keep utils import
# Import state management functions from the sibling initializer module
from agent.rag_utils.rag_initializer import is_rag_enabled, get_vector_store
# Shared Utilities (Logging)
from agent.utils import print_verbose # Import shared logging
# Agent State (for LangGraph node)
from agent.state import AgentState # Import the shared state


def query_vector_store(query: str, n_results: int = 3, verbose: bool = False) -> Tuple[str, List[str]]:
    """
    Queries the Langchain vector store for context relevant to the query.
    Optionally traverses internal links between retrieved chunks and fetches
    external web links found in the collected context.

    Args:
        query: The query string to search for in the vector store.
        n_results: The maximum number of results to retrieve (passed as 'k').
        verbose: Flag for detailed output.

    Returns:
        A tuple containing:
        - A string with relevant context from initial retrieval, internal chunk traversal, and external web fetching.
        - A list of unique source file paths/URLs contributing to the context.
        Returns ("", []) if RAG is disabled, not initialized, or no context found.
    """
    if verbose:
        # Use imported print_verbose
        print_verbose(f"Querying for: '{query}' (k={n_results})", title="Querying Vector Store (Langchain RAG)")

    # Use the state check function from the initializer
    if not is_rag_enabled():
        if verbose: print_verbose("RAG is not enabled or vector store failed to initialize. Skipping query.", style="yellow")
        return "", []

    # Get the initialized vector store instance
    vector_store = get_vector_store()
    if not vector_store: # Double-check, though is_rag_enabled should cover this
         if verbose: print_verbose("Vector store instance not available. Skipping query.", style="yellow")
         return "", []


    final_context_parts: List[str] = []
    final_sources: Set[str] = set()
    collected_chunks: Dict[str, Document] = {} # Use dict to store chunks by ID for easy lookup

    try:
        # --- Step 1: Initial Retrieval ---
        if verbose: print_verbose(f"Performing initial retrieval (k={n_results})", title="RAG Step 1: Initial Retrieval", style="dim blue")
        retriever = vector_store.as_retriever(search_kwargs={'k': n_results})
        initial_chunks: List[Document] = retriever.invoke(query)

        if not initial_chunks:
            if verbose: print_verbose("No relevant documents found in initial retrieval.", style="yellow")
            return "", []

        for chunk in initial_chunks:
             chunk_id = chunk.metadata.get('id', str(hash(chunk.page_content))) # Example ID generation
             if chunk_id not in collected_chunks:
                 collected_chunks[chunk_id] = chunk

        if verbose: print_verbose(f"Retrieved {len(collected_chunks)} initial unique chunks.", style="dim blue")

        # --- Step 2: Internal Chunk Link Traversal ---
        rag_config = get_rag_config()
        follow_internal_chunks = rag_config.get('rag_follow_internal_chunk_links', False)
        internal_link_depth = rag_config.get('rag_internal_link_depth', 1)
        internal_link_k = rag_config.get('rag_internal_link_k', 2)

        if follow_internal_chunks and internal_link_depth > 0:
            if verbose: print_verbose(f"Traversing internal chunk links (max_depth={internal_link_depth}, k={internal_link_k})", title="RAG Step 2: Internal Link Traversal", style="dim blue")
            queue: deque[Tuple[str, int]] = deque([(cid, 0) for cid in collected_chunks]) # Queue of (chunk_id, depth)
            visited_chunk_ids_for_traversal = set(collected_chunks.keys()) # Track visited during traversal

            while queue:
                current_chunk_id, current_depth = queue.popleft()

                if current_depth >= internal_link_depth:
                    continue

                current_chunk = collected_chunks.get(current_chunk_id)
                if not current_chunk or 'internal_linked_paths_str' not in current_chunk.metadata:
                    continue

                linked_paths_str = current_chunk.metadata['internal_linked_paths_str']
                if not linked_paths_str or not isinstance(linked_paths_str, str):
                    continue
                linked_paths = linked_paths_str.split(";;")

                if verbose: print_verbose(f"  [Depth {current_depth}] Chunk from '{current_chunk.metadata.get('source', 'Unknown')}' links to {len(linked_paths)} files.", style="dim blue")

                for target_path_str in linked_paths:
                    if verbose: print_verbose(f"    Searching for chunks related to query in linked file: {target_path_str}", style="dim blue")
                    try:
                        linked_retriever = vector_store.as_retriever(
                            search_kwargs={'k': internal_link_k, 'filter': {'source': target_path_str}}
                        )
                        found_linked_chunks = linked_retriever.invoke(query)

                        if verbose: print_verbose(f"      Found {len(found_linked_chunks)} chunks in {target_path_str}.", style="dim blue")

                        for linked_chunk in found_linked_chunks:
                            linked_chunk_id = linked_chunk.metadata.get('id', str(hash(linked_chunk.page_content)))
                            if linked_chunk_id not in visited_chunk_ids_for_traversal:
                                visited_chunk_ids_for_traversal.add(linked_chunk_id)
                                collected_chunks[linked_chunk_id] = linked_chunk # Add to overall collection
                                queue.append((linked_chunk_id, current_depth + 1))
                                if verbose: print_verbose(f"        Added linked chunk (ID: {linked_chunk_id}) from {target_path_str} to results and queue.", style="dim blue")

                    except Exception as search_err:
                        warnings.warn(f"Error performing filtered search for linked path {target_path_str}: {search_err}")

        # --- Step 3: Extract Content and External Links from ALL Collected Chunks ---
        if verbose: print_verbose(f"Processing {len(collected_chunks)} total collected chunks (initial + linked)", title="RAG Step 3: Content Extraction", style="dim blue")
        external_links_to_fetch = set()
        rag_doc_path_env = os.getenv("RAG_DOC_PATH", ".") # Get base path for relative sources

        for chunk_id, chunk in collected_chunks.items():
            final_context_parts.append(chunk.page_content)
            # Add source
            if chunk.metadata and 'source' in chunk.metadata:
                 source_val = str(chunk.metadata['source'])
                 # Try to make local paths relative
                 try:
                     source_path = Path(source_val)
                     if source_path.is_absolute():
                          relative_path = str(source_path.relative_to(Path(rag_doc_path_env).resolve()))
                          final_sources.add(relative_path)
                     elif source_path.resolve().is_relative_to(Path(rag_doc_path_env).resolve()):
                          relative_path = str(source_path.resolve().relative_to(Path(rag_doc_path_env).resolve()))
                          final_sources.add(relative_path)
                     else:
                          final_sources.add(source_val) # Use original if not relative to RAG path
                 except (ValueError, TypeError, OSError):
                      final_sources.add(source_val) # Fallback on error
            # Extract external links
            links_in_chunk = extract_links(chunk.page_content)
            for _, link_target in links_in_chunk:
                if is_web_link(link_target):
                    external_links_to_fetch.add(link_target)

        # --- Step 4: Fetch External Links if Enabled ---
        follow_external = rag_config.get('rag_follow_external_links', False)
        fetched_web_sources = set()

        if follow_external and external_links_to_fetch:
            if verbose: print_verbose(f"Fetching {len(external_links_to_fetch)} unique external links found in collected chunks", title="RAG Step 4: External Link Fetching", style="dim blue")
            for link_target in external_links_to_fetch:
                if verbose: print_verbose(f"  Fetching: {link_target}", style="dim blue")
                try:
                    response = requests.get(link_target, timeout=10, headers={'User-Agent': 'RooResearchAgent/1.0'})
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.decompose()
                    body_text = soup.get_text(separator='\n', strip=True)

                    if body_text:
                        fetched_content = f"--- Content from {link_target} ---\n{body_text}\n--- End Content from {link_target} ---"
                        final_context_parts.append(fetched_content)
                        fetched_web_sources.add(link_target)
                        if verbose: print_verbose(f"    Successfully fetched and parsed.", style="dim blue")
                    else:
                        if verbose: print_verbose(f"    No text content extracted.", style="yellow")
                except requests.exceptions.RequestException as req_err:
                    warnings.warn(f"Failed to fetch external link {link_target} during query: {req_err}")
                except Exception as parse_err:
                     warnings.warn(f"Failed to parse content from {link_target} during query: {parse_err}")

            final_sources.update(fetched_web_sources) # Add successfully fetched URLs to sources

        # --- Step 5: Combine and Return ---
        final_rag_context = "\n\n".join(final_context_parts)
        final_rag_source_paths = sorted(list(final_sources))

        if verbose:
             print_verbose(f"Total Chunks Contributed (Initial + Linked): {len(collected_chunks)}\nExternal URLs Fetched: {len(fetched_web_sources)}\nFinal Sources: {final_rag_source_paths}", title="Final RAG Results", style="green")

        return final_rag_context, final_rag_source_paths

    except Exception as e:
        warnings.warn(f"Error during RAG query processing: {e}")
        if verbose:
            print_verbose(f"Error during RAG query processing: {e}", title="RAG Query Error", style="red")
            traceback.print_exc()
        # Return empty results on error
        return "", []

# --- LangGraph Node ---

def rag_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to perform RAG retrieval."""
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping RAG due to previous error.", style="yellow")
         return {}

    if not is_rag_enabled(): # Check if RAG is configured/initialized properly
        if is_verbose: print_verbose("Skipping RAG node because RAG is not enabled/initialized.", style="yellow")
        # Return empty results but no error, as skipping might be intentional
        return {"rag_context": "", "rag_source_paths": []}

    if is_verbose: print_verbose("Entering RAG Node", style="cyan")

    try:
        # Call the main logic function from this module
        rag_config = get_rag_config()
        n_results = rag_config.get('rag_num_results', 3) # Example: get k from config

        context, paths = query_vector_store(
            state['clarified_question'],
            n_results=n_results,
            verbose=is_verbose
        )
        # Verbose printing is handled within query_vector_store
        # Update the state
        return {"rag_context": context, "rag_source_paths": paths, "error": None}
    except Exception as e:
        error_msg = f"RAG step failed: {e}"
        if is_verbose:
             print_verbose(error_msg, title="Node Error", style="bold red")
             traceback.print_exc() # Show traceback for RAG errors in verbose mode
        # Update state with error
        return {"error": error_msg, "rag_context": "", "rag_source_paths": []} # Ensure fields exist even on error

# Optional: Add rag_node to __all__ if needed elsewhere
# __all__ = ['query_vector_store', 'rag_node'] # Add other exports if necessary