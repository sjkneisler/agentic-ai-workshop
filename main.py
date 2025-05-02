import argparse
import agent  # Import the agent package (which includes __init__.py)
from dotenv import load_dotenv
import os
import sys

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


def main():
    """
    Main entry point for the Deep Research Agent CLI.
    """
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Deep Research Agent CLI")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output to see intermediate steps."
    )
    parser.add_argument(
        "question",
        nargs="?",  # Makes the question optional
        type=str,
        help="The research question to ask the agent. If omitted, you will be prompted."
    )

    args = parser.parse_args()

    # Use rich print if available and verbose
    print_func = rich_print if RICH_AVAILABLE and args.verbose else print

    # Get the question either from argument or prompt
    if args.question:
        question = args.question
    else:
        try:
            # Use rich prompt if available? For now, stick to input.
            question = input("🔍 Ask the research agent: ")
        except EOFError:
            print_func("\n[bold red]No input received. Exiting.[/bold red]" if RICH_AVAILABLE else "\nNo input received. Exiting.")
            return
        except KeyboardInterrupt:
             print_func("\n[bold yellow]Operation cancelled by user. Exiting.[/bold yellow]" if RICH_AVAILABLE else "\nOperation cancelled by user. Exiting.")
             sys.exit(0)


    if not question:
        print_func("[bold red]No question provided. Exiting.[/bold red]" if RICH_AVAILABLE else "No question provided. Exiting.")
        return

    print_func(Panel(f"[cyan]{question}[/cyan]", title="Processing Question", border_style="blue") if RICH_AVAILABLE else f"\nProcessing question: {question}\n")

    try:
        # Pass the chosen print function to the agent runner if needed,
        # or let the agent runner handle its own verbose printing.
        # For now, run_agent handles its internal prints.
        final_answer = agent.run_agent(question, verbose=args.verbose)

        # Print final answer using rich Panel
        print_func(Panel(final_answer, title="Final Answer", border_style="green", title_align="left") if RICH_AVAILABLE else f"\n--- Final Answer ---\n{final_answer}")

    except NotImplementedError:
         print_func(Panel("[yellow]Agent pipeline is not fully implemented yet.[/yellow]", title="Warning", border_style="yellow") if RICH_AVAILABLE else "\n⚠️ Agent pipeline is not fully implemented yet.")
    except RuntimeError as e:
        error_msg = f"Agent stopped due to a configuration error: {e}"
        print_func(Panel(f"[bold red]{error_msg}[/bold red]", title="Critical Error", border_style="red") if RICH_AVAILABLE else f"\n❌ Critical Error: {error_msg}")
    except Exception as e:
        error_msg = f"Agent encountered an unexpected error: {e}"
        print_func(Panel(f"[bold red]{error_msg}[/bold red]", title="Unexpected Error", border_style="red") if RICH_AVAILABLE else f"\n❌ Unexpected Error during agent execution: {error_msg}")
        if args.verbose:
            # Use rich traceback if available
            if RICH_AVAILABLE:
                console.print_exception(show_locals=True)
            else:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()