"""
Core agent package initialization.

Uses LangGraph to define and run the agent pipeline.
Imports node functions from their respective modules.
"""

# --- Core Imports ---
import sys
import traceback
from typing import Dict, Any # Keep basic types if needed by conditional logic

# --- LangGraph Imports ---
from langgraph.graph import StateGraph, END

# --- Agent State Import ---
from .state import AgentState

# --- Node Function Imports ---
from .clarifier import clarify_node
from .planner import plan_node
from .search import search_node
from .rag_utils.rag_query import rag_node # Import from the correct location
from .reasoner import reason_node
from .synthesizer import synthesize_node

# --- Shared Utilities Import ---
from .utils import print_verbose, RICH_AVAILABLE, console # Import shared logging

# --- Define Conditional Edges & Error Handler ---
# These functions define the graph's flow logic and remain here.

def should_execute_step(state: AgentState) -> str:
    """Determines the next step after planning."""
    if state.get("error"): return "error_handler"
    planned_steps = state.get('planned_steps', [])
    if "search" in planned_steps:
        return "search_node"
    elif "rag" in planned_steps:
        return "rag_node"
    else:
        return "reason_node"

def after_search_decision(state: AgentState) -> str:
    """Routes after the search node completes."""
    if state.get("error"): return "error_handler"
    if "rag" in state.get('planned_steps', []):
        return "rag_node"
    else:
        return "reason_node"

def after_rag_decision(state: AgentState) -> str:
    """Routes after the RAG node completes."""
    if state.get("error"): return "error_handler"
    else:
        return "reason_node"

def error_handler_node(state: AgentState) -> Dict[str, Any]:
    """Handles errors encountered in the graph. Defined here as it's graph-specific."""
    error = state.get("error", "Unknown error in graph execution")
    # Use the imported print_verbose helper
    is_verbose = state.get('verbosity_level', 1) == 2 # Default to level 1 if missing
    if is_verbose:
        print_verbose(f"Error encountered: {error}", title="Graph Error", style="bold red")
    # Set a final answer indicating the error
    # Ensure other fields potentially expected by main.py are present (empty)
    return {
        "final_answer": f"Agent encountered an error: {error}",
        "web_source_urls": state.get("web_source_urls", []), # Preserve if they exist
        "rag_source_paths": state.get("rag_source_paths", []) # Preserve if they exist
        }


# --- Build the Graph ---
workflow = StateGraph(AgentState)

# Add nodes using imported functions
workflow.add_node("clarify_node", clarify_node)
workflow.add_node("plan_node", plan_node)
workflow.add_node("search_node", search_node)
workflow.add_node("rag_node", rag_node) # Use imported rag_node
workflow.add_node("reason_node", reason_node)
workflow.add_node("synthesize_node", synthesize_node)
workflow.add_node("error_handler", error_handler_node) # Use local error handler

# Define edges (remains the same)
workflow.set_entry_point("clarify_node")
workflow.add_edge("clarify_node", "plan_node")

workflow.add_conditional_edges(
    "plan_node",
    should_execute_step,
    {
        "search_node": "search_node",
        "rag_node": "rag_node",
        "reason_node": "reason_node",
        "error_handler": "error_handler"
    }
)

workflow.add_conditional_edges(
    "search_node",
    after_search_decision,
    {
        "rag_node": "rag_node",
        "reason_node": "reason_node",
        "error_handler": "error_handler"
    }
)

workflow.add_conditional_edges(
    "rag_node",
    after_rag_decision,
    {
        "reason_node": "reason_node",
        "error_handler": "error_handler"
    }
)

workflow.add_conditional_edges(
    "reason_node",
    lambda state: "synthesize_node" if not state.get("error") else "error_handler",
    {
        "synthesize_node": "synthesize_node",
        "error_handler": "error_handler"
    }
)

workflow.add_conditional_edges(
    "synthesize_node",
    lambda state: END if not state.get("error") else "error_handler",
    {
        END: END,
        "error_handler": "error_handler"
    }
)
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
        # Use imported print_verbose
        print_verbose(f"Agent received question: [cyan]'{question}'[/cyan]", title="Starting Agent Pipeline (LangGraph)", style="bold blue")

    initial_state: AgentState = {
        "original_question": question,
        "clarified_question": "",
        "planned_steps": [],
        "search_results": [],
        "rag_context": "",
        "rag_source_paths": [],
        "combined_context": "",
        "final_answer": "Agent pipeline did not complete.",
        "web_source_urls": [],
        "verbosity_level": verbosity_level,
        "error": None
    }

    final_state = None
    try:
        final_state = app.invoke(initial_state)
        if is_verbose and final_state and not final_state.get("error"):
             # Use imported print_verbose
             print_verbose("Agent Pipeline Finished Successfully (LangGraph)", style="bold green")

    except Exception as e:
        error_msg = f"Unexpected Error during Graph Execution: {e}"
        if verbosity_level >= 1:
            # Use imported print_verbose
            print_verbose(error_msg, title="Pipeline Exception", style="bold red")
            if is_verbose:
                # Use imported RICH_AVAILABLE and console
                if RICH_AVAILABLE:
                    console.print_exception(show_locals=True)
                else:
                    traceback.print_exc()
        if final_state is None: final_state = initial_state
        # Ensure error is propagated to final state for extraction
        final_state["error"] = error_msg
        final_state["final_answer"] = f"Agent encountered an unexpected error: {e}"
        final_state["web_source_urls"] = []
        final_state["rag_source_paths"] = []

    # Extract results, handling potential errors during execution
    if final_state is None: # Should not happen with try/except, but defensive check
        final_state = initial_state
        final_state["final_answer"] = "Agent encountered a critical error during execution."

    # If an error occurred *within* the graph flow, error_handler_node sets the answer
    # If an error occurred invoking the graph, the except block sets the answer
    answer = final_state.get("final_answer", "Error: Final answer not found in state.")
    web_urls = final_state.get("web_source_urls", [])
    rag_paths = final_state.get("rag_source_paths", [])

    return answer, web_urls, rag_paths


# Make the function easily importable
__all__ = ['run_agent']