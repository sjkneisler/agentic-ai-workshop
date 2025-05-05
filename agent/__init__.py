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
from typing import List, Dict, Any, Tuple
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


def run_agent(question: str, verbosity_level: int = 1) -> Tuple[str, List[str], List[str]]:
    """
    Main entry point to run the full agent pipeline.

    Orchestrates the flow: Clarify -> Plan -> Execute Steps -> Reason -> Synthesize.

    Args:
        question: The user's input question.
        verbosity_level: Controls output detail (0=quiet, 1=default, 2=verbose).

    Returns:
        A tuple containing:
            - The final synthesized answer string.
            - A list of web source URLs used (from search results).
            - A list of local RAG source file paths used.
        Returns an error message and empty lists if a critical step fails.
    """
    is_verbose = verbosity_level == 2 # Check if we are in verbose mode

    if is_verbose:
        _print_verbose(f"Agent received question: [cyan]'{question}'[/cyan]", title="Starting Agent Pipeline", style="bold blue")


    final_answer = "Agent pipeline encountered an unexpected issue." # Default error message
    web_source_urls: List[str] = [] # Initialize list for URLs
    rag_source_paths: List[str] = [] # Initialize list for RAG file paths

    try:
        # --- Pass verbose flag to each module ---
        # Modules themselves should handle internal printing based on the flag.
        # We print major step transitions only if verbose.

        # 1. Clarify Question
        if is_verbose: _print_verbose("Step 1: Clarifying Question", style="magenta")
        # Pass is_verbose down to modules that support it
        clarified_question = clarifier.clarify_question(question, verbose=is_verbose)

        # 2. Plan Steps
        if is_verbose: _print_verbose("Step 2: Planning Steps", style="magenta")
        planned_steps = planner.plan_steps(clarified_question, verbose=is_verbose)

        # 3. Execute Steps (Search, RAG)
        if is_verbose: _print_verbose(f"Step 3: Executing Planned Steps ({', '.join(planned_steps)})", style="magenta")
        search_results: List[Dict[str, Any]] = []
        rag_context: str = ""
        # web_source_urls and rag_source_paths initialized above

        if "search" in planned_steps:
            search_results = search.serper_search(clarified_question, verbose=is_verbose)
            # --- Extract URLs ---
            web_source_urls = [result.get("link", "N/A") for result in search_results if result.get("link")]
            # ---
        else:
             if is_verbose: _print_verbose("Skipping search step based on plan.", style="yellow")

        if "rag" in planned_steps:
            # query_vector_store now returns (context, source_paths)
            rag_context, rag_source_paths = rag.query_vector_store(clarified_question, verbose=is_verbose)
        else:
             if is_verbose: _print_verbose("Skipping RAG step based on plan.", style="yellow")

        # 4. Reason Over Sources
        if is_verbose: _print_verbose("Step 4: Reasoning Over Sources", style="magenta")
        combined_context = reasoner.reason_over_sources(search_results, rag_context, verbose=is_verbose)

        # 5. Synthesize Answer
        if is_verbose: _print_verbose("Step 5: Synthesizing Answer", style="magenta")
        final_answer = synthesizer.synthesize_answer(clarified_question, combined_context, verbose=is_verbose)

        if is_verbose:
             _print_verbose("Agent Pipeline Finished Successfully", style="bold green")


    except RuntimeError as e:
        # Catch critical errors like missing API keys required for a step
        error_msg = f"Critical Error: {e}"
        # Print error only if default or verbose
        if verbosity_level >= 1:
             _print_verbose(error_msg, title="Pipeline Error", style="bold red")
        final_answer = f"Agent stopped due to a configuration error: {e}"
        web_source_urls = [] # Ensure empty list on error
        rag_source_paths = [] # Ensure empty list on error
    except Exception as e:
        # Catch any other unexpected errors during the flow
        error_msg = f"Unexpected Error: {e}"
        # Print error only if default or verbose
        if verbosity_level >= 1:
            _print_verbose(error_msg, title="Pipeline Exception", style="bold red")
            # Only show traceback if verbose
            if is_verbose:
                if RICH_AVAILABLE:
                    console.print_exception(show_locals=True)
                else:
                    traceback.print_exc()
        final_answer = f"Agent encountered an unexpected error: {e}"
        web_source_urls = [] # Ensure empty list on error
        rag_source_paths = [] # Ensure empty list on error


    return final_answer, web_source_urls, rag_source_paths

# Make the function easily importable
__all__ = ['run_agent']