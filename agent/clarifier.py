import os
import warnings
import json
from typing import List, Dict, Any, Optional

# LangChain components
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
    from langchain_core.pydantic_v1 import BaseModel, Field
    LANGCHAIN_AVAILABLE = True
except ImportError:
    warnings.warn("LangChain components (langchain-openai, langchain-core) not found. LLM clarification disabled.")
    LANGCHAIN_AVAILABLE = False

# Config and Rich for printing
try:
    from agent.config import load_config
    config = load_config()
except ImportError:
    config = {} # Provide empty config if agent.config fails
    warnings.warn("agent.config not found. Using default models for clarification.")

try:
    from rich import print as rich_print
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    def rich_print(*args, **kwargs): print(*args, **kwargs)
    class Panel:
        def __init__(self, content, title="", **kwargs):
            self.content = content
            self.title = title
        def __str__(self):
            header = f"--- {self.title} ---" if self.title else "---"
            return f"{header}\n{self.content}\n---"

# --- Helper Functions ---

def _print_verbose(message: str, title: str = "", style: str = "blue"):
    """Helper function for verbose printing, using rich if available."""
    if RICH_AVAILABLE:
        rich_print(Panel(message, title=title, border_style=style, title_align="left"))
    else:
        if title: print(f"\n--- {title} ---")
        print(message)
        if title: print("---")

# --- Pydantic Model for JSON Output ---

class ClarificationCheckOutput(BaseModel):
    """Structure for the clarification check LLM response."""
    needs_clarification: bool = Field(description="True if the question needs clarification, False otherwise.")
    questions_to_ask: List[str] = Field(description="List of specific questions to ask the user if clarification is needed.")

# --- LangChain Setup ---

def _initialize_langchain_components():
    """Initializes LangChain components if available and configured."""
    if not LANGCHAIN_AVAILABLE:
        return None, None, None, False # Added None for parser, False for success

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        warnings.warn("OPENAI_API_KEY not found. LLM clarification disabled.")
        return None, None, None, False # Added None for parser, False for success

    try:
        # Models from config
        clarification_model_name = config.get('clarification_model', 'gpt-4o-mini')
        clarification_temp = config.get('clarification_temperature', 0.2)
        refinement_model_name = config.get('refinement_model', 'gpt-4o-mini')
        refinement_temp = config.get('refinement_temperature', 0.5)

        # LLM Instances
        clarification_llm = ChatOpenAI(model=clarification_model_name, temperature=clarification_temp, api_key=openai_api_key)
        refinement_llm = ChatOpenAI(model=refinement_model_name, temperature=refinement_temp, api_key=openai_api_key)

        # --- Clarification Check Chain ---
        # Template strings with placeholders
        clarification_check_system_prompt_template = """You are an assistant that determines if a user's research question needs clarification for a research agent.
Respond ONLY with a JSON object matching the following schema:
{json_schema}"""
        clarification_check_human_template = "Analyze the following user question:\n\n{question}"

        # Parser remains the same
        json_parser = JsonOutputParser(pydantic_object=ClarificationCheckOutput)

        # Create prompt template expecting 'json_schema' and 'question'
        clarification_check_prompt = ChatPromptTemplate.from_messages([
            ("system", clarification_check_system_prompt_template),
            ("human", clarification_check_human_template)
        ])

        # Chain definition remains the same, but invocation will change
        clarification_check_chain = clarification_check_prompt | clarification_llm | json_parser

        # --- Refinement Chain ---
        refinement_system_prompt = """You are an assistant that refines a user's research question based on a clarifying conversation.
Given the original question and the subsequent Q&A, synthesize a single, clear, and focused question suitable for a research agent.
Output ONLY the refined question."""
        refinement_human_template = "{conversation_history}" # Input will be the formatted history

        refinement_prompt = ChatPromptTemplate.from_messages([
            ("system", refinement_system_prompt),
            ("human", refinement_human_template)
        ])

        refinement_chain = refinement_prompt | refinement_llm | StrOutputParser()

        # Return the parser along with the chains and success flag
        return clarification_check_chain, refinement_chain, json_parser, True

    except Exception as e:
        warnings.warn(f"Failed to initialize LangChain components for clarification: {e}")
        # Return None for parser on failure
        return None, None, None, False

# Initialize chains globally or within the function?
# Global initialization might be slightly more efficient if called multiple times,
# but requires careful handling of potential init failures. Let's init inside.

# --- Main Clarifier Function ---

def clarify_question(question: str, verbose: bool = False) -> str:
    """
    Clarifies the user's question using LangChain if needed.

    1. Uses a LangChain chain to check if clarification is needed and get questions.
    2. If needed, prompts the user for answers in the terminal.
    3. Uses another LangChain chain to refine the question based on the conversation.
    4. Returns the original or refined question.

    Args:
        question: The original user question.
        verbose: Flag for detailed output.

    Returns:
        The clarified (or original) question.
    """
    if verbose:
        _print_verbose(f"Original question: [cyan]'{question}'[/cyan]", title="Clarifying Question", style="magenta")

    # Unpack the json_parser as well
    clarification_check_chain, refinement_chain, json_parser, lc_initialized = _initialize_langchain_components()

    if not lc_initialized or not json_parser: # Check parser too
        if verbose: _print_verbose("LLM clarification skipped (LangChain components failed to initialize, OpenAI key missing, or parser unavailable).", style="yellow")
        return question

    # --- LangChain Call 1: Check if clarification is needed ---
    if verbose: _print_verbose("Asking LLM (via LangChain) if clarification is needed...", style="dim blue")

    try:
        # Get format instructions here
        json_schema_instructions = json_parser.get_format_instructions()
        # Invoke with both required variables
        clarification_info: Dict = clarification_check_chain.invoke({
            "question": question,
            "json_schema": json_schema_instructions
        })
        # Convert dict back to Pydantic model for easier access/validation if needed,
        # though JsonOutputParser already returns a dict matching the schema.
        # clarification_output = ClarificationCheckOutput(**clarification_info) # Optional
        needs_clarification = clarification_info.get('needs_clarification', False)
        questions_to_ask = clarification_info.get('questions_to_ask', [])
        if not isinstance(questions_to_ask, list):
             questions_to_ask = []
             needs_clarification = False
             warnings.warn("LLM returned invalid format for questions_to_ask.")

    except Exception as e:
        # Use the correct line number for the warning (should be around 172 now)
        warnings.warn(f"LangChain clarification check chain failed: {e}") # Note: Line number in warning might shift
        needs_clarification = False
        questions_to_ask = []

    if not needs_clarification or not questions_to_ask:
        if verbose: _print_verbose("LLM determined no clarification needed or failed to provide questions.", style="green")
        return question

    # --- User Interaction ---
    if verbose: _print_verbose(f"LLM suggests asking {len(questions_to_ask)} question(s) for clarification.", style="yellow")

    conversation_lines = [f"Original Question: {question}"]
    try:
        for i, q_to_ask in enumerate(questions_to_ask):
            prompt_prefix = f"Clarifying Question {i+1}/{len(questions_to_ask)}"
            if RICH_AVAILABLE:
                rich_print(Panel(f"[yellow]{q_to_ask}[/yellow]", title=prompt_prefix, border_style="yellow"))
                user_answer = input("Your Answer: ")
            else:
                print(f"\n--- {prompt_prefix} ---")
                print(q_to_ask)
                user_answer = input("Your Answer: ")

            conversation_lines.append(f"Question {i+1}: {q_to_ask}")
            conversation_lines.append(f"Answer {i+1}: {user_answer}")

    except (KeyboardInterrupt, EOFError):
         if verbose: _print_verbose("\nUser cancelled clarification. Using original question.", style="bold red")
         return question # Fallback to original question if user cancels

    # --- LangChain Call 2: Refine the question ---
    conversation_history_str = "\n".join(conversation_lines)

    if verbose: _print_verbose("Asking LLM (via LangChain) to refine the question based on conversation...", style="dim blue")

    try:
        refined_question = refinement_chain.invoke({"conversation_history": conversation_history_str})
    except Exception as e:
        warnings.warn(f"LangChain refinement chain failed: {e}")
        refined_question = "" # Indicate failure

    if not refined_question:
        warnings.warn("LLM failed to provide a refined question. Using original question.")
        if verbose: _print_verbose("LLM refinement failed. Using original question.", style="red")
        return question # Fallback to original

    if verbose:
        _print_verbose(f"Refined question: [cyan]'{refined_question}'[/cyan]", title="Clarification Complete", style="green")

    return refined_question

# Example usage (for testing purposes, not run by default)
if __name__ == '__main__':
    # Make sure .env is loaded if running directly
    from dotenv import load_dotenv
    import sys
    # Go up one level to find .env
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables.", file=sys.stderr)
        print("Please ensure it's set in your .env file in the parent directory.", file=sys.stderr)
        sys.exit(1)

    test_question = "Tell me about AI."
    print(f"Testing clarification for: '{test_question}'")
    clarified = clarify_question(test_question, verbose=True)
    print("\n--- Final Result ---")
    print(f"Original:    '{test_question}'")
    print(f"Clarified: '{clarified}'")

    test_question_clear = "What were the main causes of the French Revolution?"
    print(f"\nTesting clarification for: '{test_question_clear}'")
    clarified_clear = clarify_question(test_question_clear, verbose=True)
    print("\n--- Final Result ---")
    print(f"Original:    '{test_question_clear}'")
    print(f"Clarified: '{clarified_clear}'")