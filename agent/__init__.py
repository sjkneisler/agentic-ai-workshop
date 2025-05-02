"""
Core agent package initialization.

Exposes the main entry point for running the agent pipeline and orchestrates
the calls to individual agent modules. Uses 'rich' for verbose logging if available.
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
import sys
import traceback

# Attempt to import rich for enhanced output
try:
    from rich import print as rich_print
    from rich.panel import Panel
    from rich.console import Console
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback print function
    def rich_print(*args, **kwargs):
        print(*args, **kwargs)
    # Dummy Panel class if rich is not available
    class Panel:
        def __init__(self, content, title="", **kwargs):
            self.content = content
            self.title = title
        def __str__(self):
            header = f"--- {self.title} ---" if self.title else "---"
            return f"{header}\n{self.content}\n---"

def _print_verbose(message: str, title: str = "", style: str = "blue"):
    """Helper function for verbose printing, using rich if available."""
    if RICH_AVAILABLE:
        if title:
            rich_print(Panel(message, title=title, border_style=style, title_align="left"))
        else:
            rich_print(f"[{style}]{message}[/{style}]")
    else:
        if title:
            print(f"\n--- {title} ---")
            print(message)
            print("---")
        else:
            print(message)


def run_agent(question: str, verbose: bool = False) -> str:
    """
    Main entry point to run the full agent pipeline.

    Orchestrates the flow: Clarify -> Plan -> Execute Steps -> Reason -> Synthesize.

    Args:
        question: The user's input question.
        verbose: Whether to print detailed intermediate steps using rich formatting if available.

    Returns:
        The final synthesized answer string. Returns an error message if
        a critical step fails (e.g., missing required API key).
    """
    if verbose:
        _print_verbose(f"Agent received question: [cyan]'{question}'[/cyan]", title="Starting Agent Pipeline", style="bold blue")


    final_answer = "Agent pipeline encountered an unexpected issue." # Default error message

    try:
        # --- Pass verbose flag to each module ---
        # Modules themselves should handle internal printing based on the flag.
        # We print major step transitions here.

        # 1. Clarify Question
        if verbose: _print_verbose("Step 1: Clarifying Question", style="magenta")
        clarified_question = clarifier.clarify_question(question, verbose=verbose)

        # 2. Plan Steps
        if verbose: _print_verbose("Step 2: Planning Steps", style="magenta")
        planned_steps = planner.plan_steps(clarified_question, verbose=verbose)

        # 3. Execute Steps (Search, RAG)
        if verbose: _print_verbose(f"Step 3: Executing Planned Steps ({', '.join(planned_steps)})", style="magenta")
        search_results: List[Dict[str, Any]] = []
        rag_context: str = ""

        if "search" in planned_steps:
            search_results = search.serper_search(clarified_question, verbose=verbose)
        else:
             if verbose: _print_verbose("Skipping search step based on plan.", style="yellow")

        if "rag" in planned_steps:
            rag_context = rag.query_vector_store(clarified_question, verbose=verbose)
        else:
             if verbose: _print_verbose("Skipping RAG step based on plan.", style="yellow")

        # 4. Reason Over Sources
        if verbose: _print_verbose("Step 4: Reasoning Over Sources", style="magenta")
        combined_context = reasoner.reason_over_sources(search_results, rag_context, verbose=verbose)

        # 5. Synthesize Answer
        if verbose: _print_verbose("Step 5: Synthesizing Answer", style="magenta")
        final_answer = synthesizer.synthesize_answer(clarified_question, combined_context, verbose=verbose)

        if verbose:
             _print_verbose("Agent Pipeline Finished Successfully", style="bold green")


    except RuntimeError as e:
        # Catch critical errors like missing API keys required for a step
        error_msg = f"Critical Error: {e}"
        if verbose:
             _print_verbose(error_msg, title="Pipeline Error", style="bold red")
        else:
             print(f"\n❌ {error_msg}") # Print basic error if not verbose
        final_answer = f"Agent stopped due to a configuration error: {e}"
    except Exception as e:
        # Catch any other unexpected errors during the flow
        error_msg = f"Unexpected Error: {e}"
        if verbose:
            _print_verbose(error_msg, title="Pipeline Exception", style="bold red")
            # Use rich traceback if available
            if RICH_AVAILABLE:
                console.print_exception(show_locals=True)
            else:
                traceback.print_exc()
        else:
             print(f"\n❌ {error_msg}") # Print basic error if not verbose
        final_answer = f"Agent encountered an unexpected error: {e}"


    return final_answer

# Make the function easily importable
__all__ = ['run_agent']