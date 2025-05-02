"""
Agent module for planning the research steps.

Determines the sequence of actions (e.g., search, RAG) based on the question
and available resources.
"""
from typing import List

def plan_steps(clarified_question: str, verbose: bool = False) -> List[str]:
    """
    Plans the necessary steps to answer the question.

    Args:
        clarified_question: The question after potential clarification.
        verbose: Flag for detailed output.

    Returns:
        A list of strings representing the planned steps (e.g., ["search", "rag"]).

    Raises:
        NotImplementedError: This is a stub function.
    """
    if verbose:
        print("--- Planning Steps ---")
        print(f"Planning for question: {clarified_question}")

    # TODO: Implement planning logic (e.g., check for RAG_DOC_PATH)
    # For now, return a default plan
    # raise NotImplementedError("Planner not yet implemented.")
    plan = ["search"] # Placeholder default plan
    if verbose:
        print(f"Planned steps: {plan}")
    return plan