"""
Agent module for synthesizing the final answer.

Uses the reasoned context (from search, RAG, etc.) and the original
question to generate a final, coherent answer, using OpenAI's GPT models
if an API key is available. Falls back to echoing context otherwise.
"""

import os
import warnings
from typing import Dict, Any # Added for node function

# Shared Utilities (Logging, LLM Init, Token Counting)
# Import initialize_llm and count_tokens as well
from .utils import print_verbose, initialize_llm, count_tokens, OPENAI_AVAILABLE

# Config
from .config import get_synthesizer_config # Import config loader

# Agent State (for LangGraph node)
from agent.state import AgentState # Import the shared state

# LangChain core components needed for invoke
try:
    from langchain_core.messages import SystemMessage, HumanMessage
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False
    warnings.warn("langchain-core not found. LLM synthesis might be affected.")
    class SystemMessage: pass
    class HumanMessage: pass


def synthesize_answer(question: str, context: str, verbose: bool = False) -> str:
    """
    Synthesizes the final answer based on the provided context.

    Attempts to use OpenAI API if the key is set and libraries are installed.
    Otherwise, returns a formatted string containing the context.

    Args:
        question: The original (clarified) user question.
        context: The combined context string from the reasoner module.
        verbose: Flag for detailed output, including token counts if possible.

    Returns:
        A string containing the final synthesized answer.
    """
    if verbose:
        print_verbose(f"Synthesizing for question: {question}", title="Synthesizing Answer")

    final_answer = ""
    synth_config = get_synthesizer_config() # Load config

    # Use shared initialize_llm function
    llm = initialize_llm(
        model_config_key='model', # Key within synthesizer config section
        temp_config_key='temperature',
        default_model=synth_config.get('model', 'gpt-4o-mini'), # Pass defaults from synth_config
        default_temp=synth_config.get('temperature', 0.7)
    )

    # Check if LLM initialized successfully and core components are available
    if llm and LANGCHAIN_CORE_AVAILABLE:
        model_name = llm.model_name # Get model name from the initialized LLM
        if verbose:
            print_verbose(f"Attempting synthesis using initialized LLM: {model_name}", style="dim blue")
        try:
            system_prompt = synth_config.get('system_prompt', 'Synthesize a concise answer.')
            user_prompt = f"Question: {question}\n\nContext:\n{context}"

            # Use shared count_tokens function
            prompt_tokens = count_tokens(system_prompt + user_prompt, model=model_name)
            if verbose:
                print_verbose(f"Estimated prompt tokens: {prompt_tokens}", style="dim blue")

            # Use the .invoke method for LangChain ChatModels
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = llm.invoke(messages) # No need for max_tokens here, handled by model defaults or specific invoke args if needed

            # Extract content from the AIMessage response object
            final_answer = response.content if hasattr(response, 'content') else str(response)

            # Token usage might not be directly available in the basic invoke response.
            # For detailed usage, you might need callbacks or specific model provider features.
            if verbose:
                 # We can't easily get token counts from basic invoke, so report success
                 print_verbose(f"LLM invocation successful.", style="dim blue")


        except Exception as e:
            warnings.warn(f"LLM invocation failed: {e}. Falling back to context echo.")
            final_answer = f"Could not generate an answer using AI due to an error.\n\nRaw Context Provided:\n{context}"

    else:
        # Fallback if LLM init failed or core components missing
        if verbose:
            if not OPENAI_AVAILABLE:
                print_verbose("OpenAI/LangChain libraries not installed. Falling back to context echo.", style="yellow")
            elif not LANGCHAIN_CORE_AVAILABLE:
                 print_verbose("LangChain core components not available. Falling back to context echo.", style="yellow")
            elif not os.getenv("OPENAI_API_KEY"):
                 print_verbose("OPENAI_API_KEY not set. Falling back to context echo.", style="yellow")
            else:
                 print_verbose("LLM initialization failed. Falling back to context echo.", style="yellow")

        final_answer = f"AI synthesis requires OpenAI libraries, LangChain core, and an API key.\n\nRaw Context Provided:\n{context}"


    if verbose and not (final_answer and final_answer.strip()):
         print_verbose("Warning: Synthesized answer is empty.", style="yellow")

    return final_answer.strip() if final_answer else "Synthesis failed or produced no output."

# --- LangGraph Node ---

def synthesize_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to synthesize the final answer."""
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping synthesis due to previous error.", style="yellow")
         return {"final_answer": f"Agent stopped before synthesis due to error: {state.get('error')}"}

    if is_verbose: print_verbose("Entering Synthesis Node", style="magenta")

    try:
        answer = synthesize_answer(
            state['clarified_question'],
            state['combined_context'],
            verbose=is_verbose
        )
        # Verbose printing is handled within synthesize_answer
        return {"final_answer": answer, "error": None}
    except Exception as e:
        error_msg = f"Synthesis step failed: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "final_answer": f"Synthesis failed: {e}"}

# __all__ = ['synthesize_answer', 'synthesize_node']