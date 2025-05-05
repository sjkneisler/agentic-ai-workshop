"""
Agent module for synthesizing the final answer.

Uses the reasoned context (from search, RAG, etc.) and the original
question to generate a final, coherent answer, using OpenAI's GPT models
if an API key is available. Falls back to echoing context otherwise.
"""

import os
import warnings
from .config import get_synthesizer_config # Import config loader

try:
    import openai
    import tiktoken
    openai_available = True
except ImportError:
    openai_available = False
    warnings.warn("OpenAI libraries ('openai', 'tiktoken') not found. Synthesizer will fall back to basic context echo.")

# --- Constants ---
# Model and other settings are now loaded from config.py

def _count_tokens(text: str, model: str) -> int: # Model passed as argument now
    """Counts tokens using tiktoken."""
    if not openai_available:
        return 0 # Cannot count tokens without tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        warnings.warn(f"Could not count tokens for model {model}: {e}")
        return 0

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
        print("--- Synthesizing Answer ---")
        print(f"Synthesizing for question: {question}")
        # print(f"Using context:\n{context}") # Potentially too verbose

    openai_api_key = os.getenv("OPENAI_API_KEY")
    final_answer = ""
    synth_config = get_synthesizer_config() # Load config

    if openai_available and openai_api_key:
        model_name = synth_config.get('model', 'gpt-4o-mini') # Get model from config
        if verbose:
            print(f"Attempting synthesis using OpenAI model: {model_name}")
        try:
            # Initialize OpenAI client (consider doing this once globally if performance matters)
            client = openai.OpenAI(api_key=openai_api_key)

            system_prompt = synth_config.get('system_prompt', 'Synthesize a concise answer.') # Get prompt from config
            user_prompt = f"Question: {question}\n\nContext:\n{context}"

            prompt_tokens = _count_tokens(system_prompt + user_prompt, model=model_name) # Pass model name
            if verbose:
                print(f"Estimated prompt tokens: {prompt_tokens}")

            response = client.chat.completions.create(
                model=model_name, # Use model from config
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=synth_config.get('temperature', 0.7), # Use temp from config
                max_tokens=synth_config.get('max_tokens', 500)   # Use max_tokens from config
            )

            final_answer = response.choices[0].message.content

            if verbose:
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                print(f"OpenAI API call successful. Completion tokens: {completion_tokens}, Total tokens: {total_tokens}")

        except Exception as e:
            warnings.warn(f"OpenAI API call failed: {e}. Falling back to context echo.")
            # Fallback if API call fails
            final_answer = f"Could not generate an answer using AI due to an error.\n\nRaw Context Provided:\n{context}"

    else:
        if verbose:
            if not openai_available:
                print("OpenAI libraries not installed. Falling back to context echo.")
            else:
                print("OPENAI_API_KEY not set. Falling back to context echo.")
        # Fallback if key is missing or libraries not installed
        final_answer = f"AI synthesis requires an OpenAI API key (OPENAI_API_KEY environment variable).\n\nRaw Context Provided:\n{context}"


    if verbose and not final_answer.strip():
         print("Warning: Synthesized answer is empty.")

    return final_answer.strip() if final_answer else "Synthesis failed or produced no output."