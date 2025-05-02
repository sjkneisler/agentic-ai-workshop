"""
Agent module for planning the research steps.

Determines the sequence of actions (e.g., "search", "rag") based on the
question and available resources (specifically, the RAG_DOC_PATH env var).
"""
import os
from pathlib import Path
from typing import List

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
        print("--- Planning Steps ---")
        print(f"Planning based on configuration (question: '{clarified_question}')")

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
                print(f"RAG_DOC_PATH ('{rag_doc_path_str}') exists and is a directory. Adding 'rag' to plan.")
        elif verbose:
            print(f"RAG_DOC_PATH ('{rag_doc_path_str}') is set but not a valid directory. Skipping 'rag' step.")
    elif verbose:
        print("RAG_DOC_PATH not set. Skipping 'rag' step.")

    if rag_enabled_for_plan:
        plan.append("rag")

    if verbose:
        print(f"Final planned steps: {plan}")

    return plan