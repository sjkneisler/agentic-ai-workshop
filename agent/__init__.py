"""
Core agent package initialization.

Exposes the main entry point for running the agent pipeline.
"""

def run_agent(question: str, verbose: bool = False):
    """
    Main entry point to run the full agent pipeline.

    Args:
        question: The user's input question.
        verbose: Whether to print detailed intermediate steps.

    Returns:
        The final synthesized answer (currently a placeholder).

    Raises:
        NotImplementedError: This is a stub function.
    """
    print(f"Received question: {question}")
    if verbose:
        print("Verbose mode enabled.")
    # TODO: Implement the actual agent pipeline logic here
    raise NotImplementedError("Agent pipeline not yet implemented.")

# Make the function easily importable
__all__ = ['run_agent']