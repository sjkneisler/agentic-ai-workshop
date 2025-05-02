import argparse
import agent  # Import the agent package (which includes __init__.py)
from dotenv import load_dotenv
import os

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

    # Get the question either from argument or prompt
    if args.question:
        question = args.question
    else:
        try:
            question = input("🔍 Ask the research agent: ")
        except EOFError:
            print("\nNo input received. Exiting.")
            return

    if not question:
        print("No question provided. Exiting.")
        return

    print(f"\nProcessing question: {question}\n")

    try:
        # Call the main agent function from the package
        final_answer = agent.run_agent(question, verbose=args.verbose)
        print("\n--- Final Answer ---")
        print(final_answer)
    except NotImplementedError:
        print("\n⚠️ Agent pipeline is not fully implemented yet.")
        # In a real scenario, you might want more specific error handling
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc() # Print full traceback in verbose mode

if __name__ == "__main__":
    main()