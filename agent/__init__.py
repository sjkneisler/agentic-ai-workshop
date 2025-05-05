"""
Core agent package initialization.

Uses LangGraph to define and run the agent pipeline for deep research.
Imports node functions from their respective modules.
"""

# --- Core Imports ---
import sys
import traceback
from typing import Dict, Any, Optional

# --- LangGraph Imports ---
from langgraph.graph import StateGraph, END

# --- Agent State Import ---
from .state import AgentState # Ensure AgentState includes all new fields

# --- Node Function Imports ---
from .nodes.clarifier import clarify_node # Moved to nodes/
from .nodes.reasoner import reason_node # Moved to nodes/
from .nodes.synthesizer import synthesize_node # Moved to nodes/
from .nodes.search import search_node # Executes web search
from .nodes.fetch import fetch_node # Fetches URL content
from .nodes.chunk_embed import chunk_and_embed_node # Chunks/embeds fetched content
from .nodes.retrieve import retrieve_relevant_chunks_node # Retrieves from session store
from .nodes.summarize import summarize_chunks_node # Summarizes retrieved chunks
from .nodes.consolidate import consolidate_notes_node # Consolidates notes before synthesis

# --- Shared Utilities Import ---
from .utils import print_verbose, RICH_AVAILABLE, console # Import shared logging
from .state import AgentState # Import AgentState from the correct file for type hint

# --- Define Conditional Edges & Error Handler ---

# Helper function for debugging the route after chunk/embed
def route_after_chunk_embed(state: AgentState) -> str:
    is_verbose = state.get('verbosity_level', 1) == 2
    error = state.get("error")
    retrieval_query = state.get("query_for_retrieval") # Check the correct state variable
    if is_verbose:
        print_verbose(f"Routing after chunk_embed. Error: {error}, Query for Retrieval: '{retrieval_query}'", style="cyan")
    if not error and retrieval_query: # Check if we have a query to use for retrieval
        if is_verbose: print_verbose(" -> Routing to retrieve_relevant_chunks_node", style="cyan")
        return "retrieve_relevant_chunks_node"
    elif not error:
        # If no retrieval query, go back to reasoner to decide next step
        if is_verbose: print_verbose(" -> Routing back to reason_node (no query for retrieval)", style="cyan")
        return "reason_node"
    else:
        if is_verbose: print_verbose(" -> Routing to error_handler", style="cyan")
        return "error_handler"

def error_handler_node(state: AgentState) -> Dict[str, Any]:
    """Handles errors encountered in the graph."""
    error = state.get("error", "Unknown error in graph execution")
    is_verbose = state.get('verbosity_level', 1) == 2
    if is_verbose:
        print_verbose(f"Error encountered: {error}", title="Graph Error", style="bold red")
    # Set a final answer indicating the error
    return {
        "final_answer": f"Agent encountered an error: {error}",
        # Preserve any potentially useful info if needed
        "notes": state.get("notes", []),
        "web_source_urls": state.get("web_source_urls", []),
        }

def route_after_reasoning(state: AgentState) -> str:
    """Determines the next node based on the reasoner's decision."""
    next_action = state.get("next_action")
    error = state.get("error")
    is_verbose = state.get('verbosity_level', 1) == 2

    if error:
        if is_verbose: print_verbose(f"Routing to error_handler due to error: {error}", style="yellow")
        return "error_handler"

    if is_verbose: print_verbose(f"Routing based on reasoner action: {next_action}", style="blue")

    if next_action == "SEARCH":
        return "search_node"
    elif next_action == "FETCH":
        # Add validation? Ensure url_to_fetch is set? Reasoner should handle this.
        return "fetch_node"
    elif next_action == "RETRIEVE_CHUNKS":
        return "retrieve_relevant_chunks_node"
    elif next_action == "CONSOLIDATE":
        return "consolidate_notes_node"
    elif next_action == "STOP":
        # If stopping gracefully, go to consolidation anyway to use gathered notes
        if is_verbose: print_verbose("Reasoner decided STOP, routing to CONSOLIDATE.", style="yellow")
        return "consolidate_notes_node"
    else:
        # Fallback / Unknown action
        if is_verbose: print_verbose(f"Unknown action '{next_action}', routing to error_handler.", style="red")
        state["error"] = f"Unknown action decided by reasoner: {next_action}"
        return "error_handler"


# --- Build the Graph ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("clarify_node", clarify_node)
workflow.add_node("reason_node", reason_node) # Decision maker
workflow.add_node("search_node", search_node)
workflow.add_node("fetch_node", fetch_node)
workflow.add_node("chunk_and_embed_node", chunk_and_embed_node)
workflow.add_node("retrieve_relevant_chunks_node", retrieve_relevant_chunks_node)
workflow.add_node("summarize_chunks_node", summarize_chunks_node)
workflow.add_node("consolidate_notes_node", consolidate_notes_node)
workflow.add_node("synthesize_node", synthesize_node)
workflow.add_node("error_handler", error_handler_node)

# Define edges

# Start with Clarification
workflow.set_entry_point("clarify_node")

# After Clarification -> Go to Reasoning
workflow.add_conditional_edges(
    "clarify_node",
    lambda state: "reason_node" if not state.get("error") else "error_handler",
    {"reason_node": "reason_node", "error_handler": "error_handler"}
)

# After Reasoning -> Route based on decision
workflow.add_conditional_edges(
    "reason_node",
    route_after_reasoning, # Use the routing function
    {
        "search_node": "search_node",
        "fetch_node": "fetch_node",
        "retrieve_relevant_chunks_node": "retrieve_relevant_chunks_node",
        "consolidate_notes_node": "consolidate_notes_node",
        "error_handler": "error_handler"
        # STOP action also routes to consolidate_notes_node via the router function
    }
)

# After Search -> Go back to Reasoning
workflow.add_conditional_edges(
    "search_node",
    lambda state: "reason_node" if not state.get("error") else "error_handler",
    {"reason_node": "reason_node", "error_handler": "error_handler"}
)

# After Fetch -> Go to Chunk/Embed
workflow.add_conditional_edges(
    "fetch_node",
    lambda state: "chunk_and_embed_node" if not state.get("error") else "error_handler",
     # Even if fetch returns an error in the dict, proceed to chunk/embed node to handle it
    {"chunk_and_embed_node": "chunk_and_embed_node", "error_handler": "error_handler"}
)

# After Chunk/Embed -> Go to Retrieve Relevant Chunks
workflow.add_conditional_edges(
    "chunk_and_embed_node",
    route_after_chunk_embed, # Use the debugging function instead of lambda
    {
        "retrieve_relevant_chunks_node": "retrieve_relevant_chunks_node",
        "reason_node": "reason_node",
        "error_handler": "error_handler"
    }
)

# After Retrieve Chunks -> Go to Summarize
workflow.add_conditional_edges(
    "retrieve_relevant_chunks_node",
    lambda state: "summarize_chunks_node" if not state.get("error") else "error_handler",
    {"summarize_chunks_node": "summarize_chunks_node", "error_handler": "error_handler"}
)

# After Summarize -> Go back to Reasoning
workflow.add_conditional_edges(
    "summarize_chunks_node",
    lambda state: "reason_node" if not state.get("error") else "error_handler",
    {"reason_node": "reason_node", "error_handler": "error_handler"}
)

# After Consolidate -> Go to Synthesize
workflow.add_conditional_edges(
    "consolidate_notes_node",
    lambda state: "synthesize_node" if not state.get("error") else "error_handler",
    {"synthesize_node": "synthesize_node", "error_handler": "error_handler"}
)

# After Synthesize -> End
workflow.add_conditional_edges(
    "synthesize_node",
    lambda state: END if not state.get("error") else "error_handler",
    {END: END, "error_handler": "error_handler"}
)

# Error Handler -> End
workflow.add_edge("error_handler", END)

# Compile the graph
app = workflow.compile()


# --- Main run_agent Function ---
def run_agent(question: str, verbosity_level: int = 1) -> tuple[str, list[str], list[str]]:
    """
    Main entry point to run the full agent pipeline using LangGraph.
    """
    is_verbose = verbosity_level == 2

    if is_verbose:
        print_verbose(f"Agent received question: [cyan]'{question}'[/cyan]", title="Starting Agent Pipeline (Deep Research)", style="bold blue")

    # Updated initial state with new fields
    initial_state: AgentState = {
        "original_question": question,
        "clarified_question": "",
        "plan_outline": "",
        "search_results": [],
        "rag_context": "", # Keep for potential future RAG tool integration
        "rag_source_paths": [], # Keep for potential future RAG tool integration
        "session_vector_store": None, # Initialize as None
        "fetched_docs": [],
        "notes": [],
        "seen_queries": set(), # Initialize as empty set
        "combined_context": "", # Will be populated by consolidator
        "final_answer": "Agent pipeline did not complete.",
        "web_source_urls": [], # Will be populated by citation post-processing
        "verbosity_level": verbosity_level,
        "error": None,
        "current_iteration": 0, # Start iteration count
        "next_action": None, # No initial action
        "current_query": None, # No initial query
        "url_to_fetch": None, # No initial URL
        "retrieved_chunks": [] # No initial retrieved chunks
    }

    final_state = None
    try:
        # Invoke the graph with stream() for potential intermediate state logging
        # Or use invoke() for final result only
        final_state = app.invoke(initial_state)

        # Log final state details if verbose
        if is_verbose and final_state:
             if final_state.get("error"):
                  print_verbose(f"Agent Pipeline Finished with Error: {final_state['error']}", style="bold red")
             else:
                  print_verbose("Agent Pipeline Finished Successfully (Deep Research)", style="bold green")
             # print_verbose(f"Final State: {final_state}", style="dim") # Can be very large

    except Exception as e:
        error_msg = f"Unexpected Error during Graph Execution: {e}"
        if verbosity_level >= 1:
            print_verbose(error_msg, title="Pipeline Exception", style="bold red")
            if is_verbose:
                if RICH_AVAILABLE:
                    console.print_exception(show_locals=True)
                else:
                    traceback.print_exc()
        if final_state is None: final_state = initial_state # Use initial if invoke failed completely
        final_state["error"] = error_msg
        final_state["final_answer"] = f"Agent encountered an unexpected error: {e}"
        final_state["web_source_urls"] = [] # Clear sources on unexpected error

    # Extract results
    if final_state is None: # Should not happen with try/except, but defensive check
        final_state = initial_state
        final_state["final_answer"] = "Agent encountered a critical error during execution."

    answer = final_state.get("final_answer", "Error: Final answer not found in state.")
    # Note: web_source_urls are now derived during citation post-processing in synthesizer
    # We might want to extract the reference list separately if needed.
    # For now, the answer string contains the references.
    web_urls = [] # Placeholder - actual URLs are in the answer's reference list
    rag_paths = [] # RAG not currently integrated into this flow

    return answer, web_urls, rag_paths


# Make the function easily importable
__all__ = ['run_agent']