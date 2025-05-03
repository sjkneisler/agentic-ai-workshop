import argparse
import agent  # Import the agent package (which includes __init__.py)
from dotenv import load_dotenv
import os
import sys
import certifi # Added import

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

    # --- SSL Certificate Fix ---
    # Set environment variables to point to certifi's certificate bundle
    # This helps libraries like requests and httpx (used by openai) find the correct CAs.
    certifi_path = certifi.where()
    os.environ['SSL_CERT_FILE'] = certifi_path
    os.environ['REQUESTS_CA_BUNDLE'] = certifi_path
    # --- End SSL Certificate Fix ---

    parser = argparse.ArgumentParser(description="Deep Research Agent CLI")
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose",
        action="store_const",
        dest="verbosity_level",
        const=2, # Level 2 for verbose
        help="Enable verbose output to see all intermediate steps."
    )
    verbosity_group.add_argument(
        "-q", "--quiet",
        action="store_const",
        dest="verbosity_level",
        const=0, # Level 0 for quiet
        help="Suppress informational output, showing only the final answer."
    )
    parser.set_defaults(verbosity_level=1) # Level 1 for default

    parser.add_argument(
        "question",
        nargs="?",  # Makes the question optional
        type=str,
        help="The research question to ask the agent. If omitted, you will be prompted."
    )

    args = parser.parse_args()

    # Get the question either from argument or prompt
    if args.question:
        question = args.question
    else:
        try:
            # Use rich prompt if available? For now, stick to input.
            question = input("🔍 Ask the research agent: ")
        except EOFError:
            (rich_print("\n[bold red]No input received. Exiting.[/bold red]") if RICH_AVAILABLE else print("\nNo input received. Exiting."))
            return
        except KeyboardInterrupt:
             (rich_print("\n[bold yellow]Operation cancelled by user. Exiting.[/bold yellow]") if RICH_AVAILABLE else print("\nOperation cancelled by user. Exiting."))
             sys.exit(0)


    if not question:
        # Always print this error regardless of verbosity
        (rich_print("[bold red]No question provided. Exiting.[/bold red]") if RICH_AVAILABLE else print("No question provided. Exiting."))
        return

    # --- Print Processing Question Panel (Default & Verbose only) ---
    if args.verbosity_level >= 1:
        (rich_print(Panel(f"[cyan]{question}[/cyan]", title="Processing Question", border_style="blue")) if RICH_AVAILABLE else print(f"\n--- Processing Question ---\n{question}\n---"))

    try:
        # Pass the verbosity level to the agent runner
        # run_agent will now return (final_answer, source_urls)
        final_answer, source_urls = agent.run_agent(question, verbosity_level=args.verbosity_level)

        # --- Print Source URLs (Default & Verbose only) ---
        if args.verbosity_level >= 1 and source_urls:
             url_list_str = "\n".join([f"- {url}" for url in source_urls])
             (rich_print(Panel(url_list_str, title="Sources Used (URLs)", border_style="yellow", title_align="left")) if RICH_AVAILABLE else print(f"\n--- Sources Used (URLs) ---\n{url_list_str}"))

        # --- Print Final Answer Panel (All modes) ---
        (rich_print(Panel(final_answer, title="Final Answer", border_style="green", title_align="left")) if RICH_AVAILABLE else print(f"\n--- Final Answer ---\n{final_answer}"))

    except NotImplementedError:
         # Always print this error
         (rich_print(Panel("[yellow]Agent pipeline is not fully implemented yet.[/yellow]", title="Warning", border_style="yellow")) if RICH_AVAILABLE else print("\n⚠️ Agent pipeline is not fully implemented yet."))
    except RuntimeError as e:
        error_msg = f"Agent stopped due to a configuration error: {e}"
        # Always print critical errors
        (rich_print(Panel(f"[bold red]{error_msg}[/bold red]", title="Critical Error", border_style="red")) if RICH_AVAILABLE else print(f"\n❌ Critical Error: {error_msg}"))
    except Exception as e:
        error_msg = f"Agent encountered an unexpected error: {e}"
        # Always print unexpected errors
        (rich_print(Panel(f"[bold red]{error_msg}[/bold red]", title="Unexpected Error", border_style="red")) if RICH_AVAILABLE else print(f"\n❌ Unexpected Error during agent execution: {error_msg}"))
        # Show traceback only in verbose mode
        if args.verbosity_level == 2:
            if RICH_AVAILABLE:
                console.print_exception(show_locals=True)
            else:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()