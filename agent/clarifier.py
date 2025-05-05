import os
import warnings
import json
from typing import List, Dict, Any, Optional

# LangChain components
try:
    # No longer need ChatOpenAI here directly
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
    from pydantic.v1 import BaseModel, Field # Use pydantic v1 compatibility namespace
    LANGCHAIN_AVAILABLE = True
except ImportError:
    warnings.warn("LangChain components (langchain-core) not found. LLM clarification disabled.")
    LANGCHAIN_AVAILABLE = False

# Shared Utilities (Logging, LLM Init)
# Import initialize_llm as well
from .utils import print_verbose, RICH_AVAILABLE, Panel, rich_print, initialize_llm

# --- Pydantic Model for JSON Output ---

class ClarificationCheckOutput(BaseModel):
    """Structure for the clarification check LLM response."""
    needs_clarification: bool = Field(description="True if the question needs clarification, False otherwise.")
    questions_to_ask: List[str] = Field(description="List of specific questions to ask the user if clarification is needed.")

# --- LangChain Setup ---

def _initialize_langchain_components():
    """Initializes LangChain components using shared utility."""
    if not LANGCHAIN_AVAILABLE:
        return None, None, None, False

    # Use the shared initializer function
    clarification_llm = initialize_llm(
        model_config_key='clarification_model',
        temp_config_key='clarification_temperature',
        default_model='gpt-4o-mini',
        default_temp=0.2
    )
    refinement_llm = initialize_llm(
        model_config_key='refinement_model',
        temp_config_key='refinement_temperature',
        default_model='gpt-4o-mini',
        default_temp=0.5
    )

    # Check if LLMs initialized successfully
    if not clarification_llm or not refinement_llm:
        warnings.warn("Failed to initialize one or both LLMs for clarification.")
        return None, None, None, False

    try:
        # --- Clarification Check Chain ---
        clarification_check_system_prompt_template = """You are an assistant that determines if a user's research question needs clarification for a research agent.
Respond ONLY with a JSON object matching the following schema:
{json_schema}"""
        clarification_check_human_template = "Analyze the following user question:\n\n{question}"

        json_parser = JsonOutputParser(pydantic_object=ClarificationCheckOutput)

        clarification_check_prompt = ChatPromptTemplate.from_messages([
            ("system", clarification_check_system_prompt_template),
            ("human", clarification_check_human_template)
        ])

        # Use the initialized LLM instance
        clarification_check_chain = clarification_check_prompt | clarification_llm | json_parser

        # --- Refinement Chain ---
        refinement_system_prompt = """You are an assistant that refines a user's research question based on a clarifying conversation.
Given the original question and the subsequent Q&A, synthesize a single, clear, and focused question suitable for a research agent.
Output ONLY the refined question."""
        refinement_human_template = "{conversation_history}"

        refinement_prompt = ChatPromptTemplate.from_messages([
            ("system", refinement_system_prompt),
            ("human", refinement_human_template)
        ])

        # Use the initialized LLM instance
        refinement_chain = refinement_prompt | refinement_llm | StrOutputParser()

        return clarification_check_chain, refinement_chain, json_parser, True

    except Exception as e:
        # Catch errors during chain setup specifically
        warnings.warn(f"Failed to set up LangChain chains for clarification: {e}")
        return None, None, None, False

# --- Main Clarifier Function ---

def clarify_question(question: str, verbose: bool = False) -> str:
    """
    Clarifies the user's question using LangChain if needed.
    """
    if verbose:
        print_verbose(f"Original question: [cyan]'{question}'[/cyan]", title="Clarifying Question", style="magenta")

    clarification_check_chain, refinement_chain, json_parser, lc_initialized = _initialize_langchain_components()

    if not lc_initialized or not json_parser:
        if verbose: print_verbose("LLM clarification skipped (LangChain components failed to initialize, OpenAI key missing, or parser unavailable).", style="yellow")
        return question

    # --- LangChain Call 1: Check if clarification is needed ---
    if verbose: print_verbose("Asking LLM (via LangChain) if clarification is needed...", style="dim blue")

    try:
        json_schema_instructions = json_parser.get_format_instructions()
        clarification_info: Dict = clarification_check_chain.invoke({
            "question": question,
            "json_schema": json_schema_instructions
        })
        needs_clarification = clarification_info.get('needs_clarification', False)
        questions_to_ask = clarification_info.get('questions_to_ask', [])
        if not isinstance(questions_to_ask, list):
             questions_to_ask = []
             needs_clarification = False
             warnings.warn("LLM returned invalid format for questions_to_ask.")

    except Exception as e:
        warnings.warn(f"LangChain clarification check chain failed: {e}")
        needs_clarification = False
        questions_to_ask = []

    if not needs_clarification or not questions_to_ask:
        if verbose: print_verbose("LLM determined no clarification needed or failed to provide questions.", style="green")
        return question

    # --- User Interaction ---
    if verbose: print_verbose(f"LLM suggests asking {len(questions_to_ask)} question(s) for clarification.", style="yellow")

    conversation_lines = [f"Original Question: {question}"]
    try:
        for i, q_to_ask in enumerate(questions_to_ask):
            prompt_prefix = f"Clarifying Question {i+1}/{len(questions_to_ask)}"
            if RICH_AVAILABLE:
                rich_print(Panel(f"[yellow]{q_to_ask}[/yellow]", title=prompt_prefix, border_style="yellow")) # Use rich_print here
                user_answer = input("Your Answer: ")
            else:
                print(f"\n--- {prompt_prefix} ---")
                print(q_to_ask)
                user_answer = input("Your Answer: ")

            conversation_lines.append(f"Question {i+1}: {q_to_ask}")
            conversation_lines.append(f"Answer {i+1}: {user_answer}")

    except (KeyboardInterrupt, EOFError):
         if verbose: print_verbose("\nUser cancelled clarification. Using original question.", style="bold red")
         return question

    # --- LangChain Call 2: Refine the question ---
    conversation_history_str = "\n".join(conversation_lines)

    if verbose: print_verbose("Asking LLM (via LangChain) to refine the question based on conversation...", style="dim blue")

    try:
        refined_question = refinement_chain.invoke({"conversation_history": conversation_history_str})
    except Exception as e:
        warnings.warn(f"LangChain refinement chain failed: {e}")
        refined_question = ""

    if not refined_question:
        warnings.warn("LLM failed to provide a refined question. Using original question.")
        if verbose: print_verbose("LLM refinement failed. Using original question.", style="red")
        return question

    if verbose:
        print_verbose(f"Refined question: [cyan]'{refined_question}'[/cyan]", title="Clarification Complete", style="green")

    return refined_question

# Example usage (for testing purposes, not run by default)
if __name__ == '__main__':
    from dotenv import load_dotenv
    import sys
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

# --- LangGraph Node ---

from agent.state import AgentState # Import the shared state

def clarify_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to clarify the user's question."""
    is_verbose = state['verbosity_level'] == 2

    if is_verbose: print_verbose("Entering Clarification Node", style="magenta")

    try:
        clarified = clarify_question(state['original_question'], verbose=is_verbose)
        if is_verbose: print_verbose(f"Clarification resulted in: [cyan]'{clarified}'[/cyan]", style="green")
        return {"clarified_question": clarified, "error": None}
    except Exception as e:
        error_msg = f"Clarification step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg}

# __all__ = ['clarify_question', 'clarify_node']