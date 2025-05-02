"""
Core agent package initialization.

Exposes the main entry point for running the agent pipeline and orchestrates
the calls to individual agent modules.
"""

# Import agent modules
from . import clarifier
from . import planner
from . import search
from . import rag
from . import reasoner
from . import synthesizer

# For type hinting
from typing import List, Dict, Any

def run_agent(question: str, verbose: bool = False) -> str:
    """
    Main entry point to run the full agent pipeline.

    Orchestrates the flow: Clarify -> Plan -> Execute Steps -> Reason -> Synthesize.

    Args:
        question: The user's input question.
        verbose: Whether to print detailed intermediate steps.

    Returns:
        The final synthesized answer string. Returns an error message if
        a critical step fails (e.g., missing required API key).
    """
    if verbose:
        print("--- Starting Agent Pipeline ---")
        print(f"Initial Question: {question}")

    final_answer = "Agent pipeline encountered an unexpected issue." # Default error message

    try:
        # 1. Clarify Question
        clarified_question = clarifier.clarify_question(question, verbose=verbose)

        # 2. Plan Steps
        planned_steps = planner.plan_steps(clarified_question, verbose=verbose)

        # 3. Execute Steps (Search, RAG)
        search_results: List[Dict[str, Any]] = []
        rag_context: str = ""

        if "search" in planned_steps:
            # Note: search.serper_search raises RuntimeError if key is missing
            search_results = search.serper_search(clarified_question, verbose=verbose)
        else:
             if verbose: print("Skipping search step based on plan.")

        if "rag" in planned_steps:
            # Note: rag.query_vector_store handles missing key/path internally
            # but _initialize_rag might raise RuntimeError if key missing when path IS set.
            rag_context = rag.query_vector_store(clarified_question, verbose=verbose)
        else:
             if verbose: print("Skipping RAG step based on plan.")

        # 4. Reason Over Sources
        combined_context = reasoner.reason_over_sources(search_results, rag_context, verbose=verbose)

        # 5. Synthesize Answer
        # Note: synthesizer handles missing key internally with fallback
        final_answer = synthesizer.synthesize_answer(clarified_question, combined_context, verbose=verbose)

        if verbose:
            print("--- Agent Pipeline Finished ---")

    except RuntimeError as e:
        # Catch critical errors like missing API keys required for a step
        print(f"\n❌ Critical Error: {e}")
        final_answer = f"Agent stopped due to a configuration error: {e}"
    except Exception as e:
        # Catch any other unexpected errors during the flow
        print(f"\n❌ Unexpected Error during agent execution: {e}")
        final_answer = f"Agent encountered an unexpected error: {e}"
        if verbose:
            import traceback
            traceback.print_exc()

    return final_answer

# Make the function easily importable
__all__ = ['run_agent']