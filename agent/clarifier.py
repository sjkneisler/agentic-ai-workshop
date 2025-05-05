import os
import warnings
import json
from typing import List, Dict, Any, Optional, Tuple # Added Tuple

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

class RefinementOutput(BaseModel):
    """Structure for the refinement LLM response."""
    refined_question: str = Field(description="The single, clear, and focused question suitable for a research agent.")
    plan_outline: str = Field(description="A simple Markdown outline with a title and 3-5 relevant section headers based on the refined question.")


# --- LangChain Setup ---

def _initialize_langchain_components():
    """Initializes LangChain components using shared utility."""
    if not LANGCHAIN_AVAILABLE:
        return None, None, None, None, False # Added one None

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
        return None, None, None, None, False # Added one None

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
        refinement_system_prompt = """You are an assistant that refines a user's research question based on a clarifying conversation AND generates a basic Markdown research plan outline.
Given the original question and the subsequent Q&A, synthesize:
1. A single, clear, and focused question suitable for a research agent.
2. A simple Markdown outline containing a title (derived from the refined question) and 3-5 relevant section headers to guide the research.

Respond ONLY with a JSON object matching the following schema:
{refinement_json_schema}"""
        refinement_human_template = "{conversation_history}"

        refinement_json_parser = JsonOutputParser(pydantic_object=RefinementOutput)

        refinement_prompt = ChatPromptTemplate.from_messages([
            ("system", refinement_system_prompt),
            ("human", refinement_human_template)
        ])

        # Use the initialized LLM instance
        refinement_chain = refinement_prompt | refinement_llm | refinement_json_parser

        return clarification_check_chain, refinement_chain, json_parser, refinement_json_parser, True # Added refinement_json_parser

    except Exception as e:
        # Catch errors during chain setup specifically
        warnings.warn(f"Failed to set up LangChain chains for clarification: {e}")
        return None, None, None, None, False # Added one None

# --- Main Clarifier Function ---

def clarify_question(question: str, verbose: bool = False) -> Tuple[str, str]:
    """
    Clarifies the user's question using LangChain if needed and generates a plan outline.

    Returns:
        A tuple containing:
            - refined_question (str): The clarified question (or original if no clarification).
            - plan_outline (str): The generated Markdown outline (or a default if generation fails).
    """
    default_outline = f"# Research Plan: {question}\n\n## Overview\n\n## Key Aspects\n\n## Conclusion"
    if verbose:
        print_verbose(f"Original question: [cyan]'{question}'[/cyan]", title="Clarifying Question", style="magenta")

    clarification_check_chain, refinement_chain, json_parser, refinement_json_parser, lc_initialized = _initialize_langchain_components()

    if not lc_initialized or not json_parser or not refinement_json_parser:
        if verbose: print_verbose("LLM clarification/planning skipped (LangChain components failed to initialize, OpenAI key missing, or parsers unavailable).", style="yellow")
        return question, default_outline

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

    # If no clarification needed, still try to generate an outline from the original question
    if not needs_clarification or not questions_to_ask:
        if verbose: print_verbose("LLM determined no clarification needed or failed to provide questions. Attempting outline generation.", style="green")
        # Use the refinement chain directly with the original question
        conversation_history_str = f"Original Question: {question}\n(No clarification Q&A needed)"
        try:
            refinement_schema_instructions = refinement_json_parser.get_format_instructions()
            refinement_result: Dict = refinement_chain.invoke({
                "conversation_history": conversation_history_str,
                "refinement_json_schema": refinement_schema_instructions
            })
            refined_question = refinement_result.get('refined_question', question)
            plan_outline = refinement_result.get('plan_outline', default_outline)
            if verbose:
                 print_verbose(f"Generated outline for original question.", title="Outline Generation", style="green")
                 print_verbose(f"Refined Question (if changed): [cyan]'{refined_question}'[/cyan]", style="dim")
                 print_verbose(f"Plan Outline:\n{plan_outline}", style="dim")
            return refined_question, plan_outline
        except Exception as e:
            warnings.warn(f"LangChain refinement/outline chain failed even without Q&A: {e}")
            if verbose: print_verbose("Outline generation failed. Using original question and default outline.", style="red")
            return question, default_outline

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
         if verbose: print_verbose("\nUser cancelled clarification. Using original question and default outline.", style="bold red")
         return question, default_outline

    # --- LangChain Call 2: Refine the question ---
    conversation_history_str = "\n".join(conversation_lines)

    if verbose: print_verbose("Asking LLM (via LangChain) to refine question and generate outline based on conversation...", style="dim blue")

    try:
        refinement_schema_instructions = refinement_json_parser.get_format_instructions()
        refinement_result: Dict = refinement_chain.invoke({
            "conversation_history": conversation_history_str,
            "refinement_json_schema": refinement_schema_instructions
        })
        refined_question = refinement_result.get('refined_question')
        plan_outline = refinement_result.get('plan_outline')

    except Exception as e:
        warnings.warn(f"LangChain refinement/outline chain failed: {e}")
        refined_question = None
        plan_outline = None

    if not refined_question or not plan_outline:
        warnings.warn("LLM failed to provide a refined question or plan outline. Using original question and default outline.")
        if verbose: print_verbose("LLM refinement/planning failed. Using original question and default outline.", style="red")
        return question, default_outline

    if verbose:
        print_verbose(f"Refined question: [cyan]'{refined_question}'[/cyan]", title="Clarification & Planning Complete", style="green")
        print_verbose(f"Plan Outline:\n{plan_outline}", style="dim")

    return refined_question, plan_outline

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
        clarified_q, plan_out = clarify_question(state['original_question'], verbose=is_verbose)
        # Verbose printing happens inside clarify_question now
        return {"clarified_question": clarified_q, "plan_outline": plan_out, "error": None}
    except Exception as e:
        error_msg = f"Clarification/Planning step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg}

# __all__ = ['clarify_question', 'clarify_node']