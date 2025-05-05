"""
Agent module for planning the research steps.

Determines the sequence of actions (e.g., "search", "rag") based on the
question and available resources (specifically, the RAG_DOC_PATH env var).
"""
import os
from pathlib import Path
from typing import List, Dict, Any # Added Dict, Any for node

# Shared Utilities (Logging)
from .utils import print_verbose # Import shared logging

# Agent State
from agent.state import AgentState # Import the shared state


def plan_steps(clarified_question: str, verbose: bool = False) -> List[str]:
    """
    Plans the necessary steps to answer the question based on configuration.

    Rule: Always include "search". Include "rag" if RAG_DOC_PATH is set
          and points to an existing directory.

    Args:
        clarified_question: The question after potential clarification (currently unused).
        verbose: Flag for detailed output.

    Returns:
        A list of strings representing the planned steps (e.g., ["search"] or ["search", "rag"]).
    """
    if verbose:
        # Use imported print_verbose
        print_verbose(f"Planning based on configuration (question: '{clarified_question}')", title="Planning Steps")

    # Start with the mandatory step
    plan = ["search"]

    # Check if RAG should be included
    rag_doc_path_str = os.getenv("RAG_DOC_PATH")
    rag_enabled_for_plan = False
    if rag_doc_path_str:
        rag_doc_path = Path(rag_doc_path_str)
        if rag_doc_path.is_dir():
            rag_enabled_for_plan = True
            if verbose:
                # Use imported print_verbose
                print_verbose(f"RAG_DOC_PATH ('{rag_doc_path_str}') exists and is a directory. Adding 'rag' to plan.", style="dim blue")
        elif verbose:
            # Use imported print_verbose
            print_verbose(f"RAG_DOC_PATH ('{rag_doc_path_str}') is set but not a valid directory. Skipping 'rag' step.", style="yellow")
    elif verbose:
        # Use imported print_verbose
        print_verbose("RAG_DOC_PATH not set. Skipping 'rag' step.", style="yellow")

    if rag_enabled_for_plan:
        plan.append("rag")

    if verbose:
        # Use imported print_verbose
        print_verbose(f"Final planned steps: {plan}", style="green")

    return plan

# --- LangGraph Node ---

def plan_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to plan the research steps."""
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping planning due to previous error.", style="yellow")
         return {}

    if is_verbose: print_verbose("Entering Planning Node", style="magenta")

    try:
        # Call the main logic function from this module
        steps = plan_steps(state['clarified_question'], verbose=is_verbose)
        # Verbose printing is handled within plan_steps now
        # Update the state
        return {"planned_steps": steps, "error": None}
    except Exception as e:
        error_msg = f"Planning step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Update state with error
        return {"error": error_msg}

# Optional: Add plan_node to __all__
# __all__ = ['plan_steps', 'plan_node']