"""
Agent module for synthesizing the final answer.

Uses the curated notes (from the consolidator node) and the original
question to generate a final, coherent answer, using OpenAI's GPT models.
Includes post-processing to format citations.
"""

import os
import re # Import regex for citation processing
import warnings
from typing import Dict, Any, List, Tuple

# Shared Utilities (Logging, LLM Init, Token Counting)
from agent.utils import print_verbose, initialize_llm, count_tokens, OPENAI_AVAILABLE, log_prompt_data # Use absolute import

# Langchain callbacks for token usage
try:
    from langchain_community.callbacks.manager import get_openai_callback
    LANGCHAIN_CALLBACKS_AVAILABLE = True
except ImportError:
    warnings.warn("LangChain callbacks not found. Cost calculation via get_openai_callback will be disabled for synthesizer.")
    LANGCHAIN_CALLBACKS_AVAILABLE = False

# Config
from agent.config import get_synthesizer_config, get_openai_pricing_config # Use absolute import

# Agent State (for LangGraph node)
from agent.state import AgentState # Use absolute import

# LangChain core components needed for invoke
try:
    from langchain_core.messages import SystemMessage, HumanMessage
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False
    warnings.warn("langchain-core not found. LLM synthesis might be affected.")
    class SystemMessage: pass
    class HumanMessage: pass


# --- Citation Post-Processing Helper ---

def _parse_citation_tag(tag: str) -> Dict[str, str]:
    """Parses the detailed citation tag into a dictionary."""
    data = {}
    # Regex to find key='value' pairs within the tag
    pattern = re.compile(r"(\w+)='([^']*)'")
    matches = pattern.findall(tag)
    for key, value in matches:
        data[key] = value
    return data

def _post_process_citations(text: str, verbose: bool = False) -> str:
    """
    Finds detailed citation tags, replaces them with numbers,
    and appends a numbered reference list.
    """
    if verbose: print_verbose("Post-processing citations...", style="dim blue")

    # Regex to find the detailed citation tags
    # Made more robust to handle variations in spacing and ensure it captures the full tag.
    # It looks for "[Source", then any characters (non-greedy) until "='", then any characters until "'",
    # and repeats this for key-value pairs, finally closing with "]".
    citation_pattern = re.compile(r"(\[Source\s+(?:\w+\s*=\s*'[^']*'(?:\s*,\s*|\s+)?)+\])")

    unique_citations = {} # Store unique tags and their assigned number
    reference_list_items = []
    current_ref_number = 1

    def replace_match(match):
        nonlocal current_ref_number
        tag = match.group(1)
        if tag not in unique_citations:
            unique_citations[tag] = current_ref_number
            
            # Parse the tag to create a nice reference list entry
            parsed_data = _parse_citation_tag(tag)
            title = parsed_data.get('Title', 'Unknown Title')
            url = parsed_data.get('URL', 'Unknown URL')
            # chunk = parsed_data.get('Chunk', 'N/A') # Chunk info might be too noisy for ref list
            
            reference_list_items.append(f"[{current_ref_number}] {title} ({url})")
            current_ref_number += 1
        
        # Replace the full tag with the reference number format
        return f"[ref:{unique_citations[tag]}]"

    # Replace citations in the main text
    processed_text = citation_pattern.sub(replace_match, text)

    # Append the reference list if citations were found
    if reference_list_items:
        reference_section = "\n\n---\nReferences:\n" + "\n".join(reference_list_items)
        processed_text += reference_section
        if verbose: print_verbose(f"Generated {len(reference_list_items)} references.", style="dim blue")
    elif verbose:
        print_verbose("No detailed citation tags found for post-processing.", style="dim blue")


    return processed_text


# --- Main Synthesis Function ---

def synthesize_answer(question: str, context: str, outline: str, verbose: bool = False) -> Tuple[str, float]:
    """
    Synthesizes the final answer based on the provided curated context (notes).
    Instructs the LLM to preserve detailed citations, then post-processes them.
    Returns the final answer string and the cost of the LLM call.
    """
    if verbose:
        print_verbose(f"Synthesizing for question: {question}", title="Synthesizing Answer")
        print_verbose(f"RAW COMBINED CONTEXT FED TO SYNTHESIZER LLM:\n---\n{context}\n---", style="dim") # Log full raw context if verbose

    final_answer_text = ""
    current_call_cost = 0.0
    pricing_config = get_openai_pricing_config().get('models', {})
    synth_config = get_synthesizer_config()

    llm = initialize_llm(
        model_config_key='model',
        temp_config_key='temperature',
        default_model=synth_config.get('model', 'o4-mini'), # Use a capable model for final synthesis
        default_temp=synth_config.get('temperature', 1)
    )

    if llm and LANGCHAIN_CORE_AVAILABLE:
        model_name = getattr(llm, 'model_name', 'Unknown')
        if verbose:
            print_verbose(f"Attempting synthesis using initialized LLM: {model_name}", style="dim blue")
        try:
            # Updated system prompt to handle new citation format
            system_prompt = synth_config.get('system_prompt', """
You are a research assistant. Your task is to synthesize a comprehensive and well-structured answer to the user's question.
You will be provided with:
1.  The User's Question.
2.  An Answer Outline (you should follow this structure, adding sub-headers if needed).
3.  Curated Research Information, which includes:
    *   Ranked Summary Notes.
    *   Supporting Raw Chunks for each summary note, containing more detailed information and the original citation tags.

**Instructions for Synthesizing the Answer:**
1.  Base your answer ONLY on the provided Curated Research Information. Do not use outside knowledge.
2.  Follow the provided Answer Outline. You may add more sub-headers if it helps structure your response.
3.  Use the Summary Notes as a primary guide for content and flow.
4.  Refer to the "Supporting Raw Chunks" for specific details, facts, figures, and to ensure comprehensive coverage of topics mentioned in the summaries. The raw chunks are the ultimate source of truth.
5.  Do not use a preamble or postamble - only output the synthesized response.

**EXTREMELY IMPORTANT CITATION PRESERVATION RULES:**
1.  The Supporting Raw Chunks contain citation tags in the format: `[Source URL='<URL>', Title='<TITLE>', Chunk=<CHUNK_INDEX>]`. These tags are associated with specific pieces of information within those chunks.
2.  When you use information from a raw chunk that has such a tag, you MUST include the citation tag VERBATIM AND UNALTERED in your synthesized answer, immediately following the information it supports.
3.  DO NOT summarize, paraphrase, reformat, or change these tags in ANY WAY. Copy them EXACTLY as they appear in the raw chunks.
4.  If a piece of information comes from a raw chunk, and that information is associated with a citation tag in the chunk, it MUST be followed by its original, complete citation tag in your answer.
Failure to preserve these tags perfectly will make the output unusable.

Structure your answer clearly. Do not invent facts or information not present in the provided information.
""").strip()
            # Context now comes from the consolidator node and includes summaries and raw chunks
            user_prompt = f"User Question: {question}\n\nAnswer Outline:\n{outline}\n\nCurated Research Information:\n{context}\n\nRemember to follow the synthesis instructions and EXTREMELY IMPORTANT CITATION PRESERVATION RULES from the system prompt, drawing details from raw chunks and citing accurately."

            # Estimate tokens (optional)
            # prompt_tokens = count_tokens(system_prompt + user_prompt, model=model_name)
            # if verbose: print_verbose(f"Estimated prompt tokens: {prompt_tokens}", style="dim blue")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            if LANGCHAIN_CALLBACKS_AVAILABLE and llm:
                with get_openai_callback() as cb:
                    response = llm.invoke(messages)
                    raw_answer = response.content if hasattr(response, 'content') else str(response)

                    # Cost is now directly from the callback handler
                    call_cost_iter = cb.total_cost
                    current_call_cost += call_cost_iter
                    if verbose: print_verbose(f"Synthesizer call cost: ${call_cost_iter:.6f}", style="dim yellow")
            else:
                response = llm.invoke(messages)
                raw_answer = response.content if hasattr(response, 'content') else str(response)
                if verbose and not LANGCHAIN_CALLBACKS_AVAILABLE: print_verbose("Langchain callbacks unavailable, skipping cost calculation for synthesizer.", style="dim yellow")

            # Log prompt and raw response
            log_prompt_data(
                node_name="synthesize_node",
                prompt={"system_prompt": system_prompt, "user_prompt": user_prompt},
                response=raw_answer, # Log the raw answer before citation processing
                additional_info={
                    "model": llm.model_name if llm else synth_config.get('model'),
                    "temperature": llm.temperature if llm else synth_config.get('temperature')
                }
            )

            if verbose: print_verbose("LLM invocation successful. Raw answer received.", style="dim blue")

            # Post-process the raw answer for citations
            final_answer_text = _post_process_citations(raw_answer, verbose=verbose)

        except Exception as e:
            warnings.warn(f"LLM invocation or citation processing failed: {e}")
            final_answer_text = f"Could not generate an answer using AI due to an error: {e}\n\nRaw Context Provided:\n{context}"

    else:
        # Fallback if LLM init failed or core components missing
        fallback_reason = "OpenAI/LangChain libraries not installed." if not OPENAI_AVAILABLE \
                     else "LangChain core components not available." if not LANGCHAIN_CORE_AVAILABLE \
                     else "OPENAI_API_KEY not set." if not os.getenv("OPENAI_API_KEY") \
                     else "LLM initialization failed."
        if verbose: print_verbose(f"{fallback_reason} Falling back to context echo.", style="yellow")
        final_answer_text = f"AI synthesis requires prerequisites ({fallback_reason}).\n\nRaw Context Provided:\n{context}"


    if verbose and not (final_answer_text and final_answer_text.strip()):
         print_verbose("Warning: Synthesized answer is empty.", style="yellow")

    return (final_answer_text.strip() if final_answer_text else "Synthesis failed or produced no output."), current_call_cost

# --- LangGraph Node ---

def synthesize_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to synthesize the final answer using the curated context."""
    is_verbose = state['verbosity_level'] == 2
    # Check for error from previous steps (like consolidation)
    current_total_openai_cost = state.get('total_openai_cost', 0.0) # Get existing cost

    if state.get("error"):
         if is_verbose: print_verbose("Skipping synthesis due to previous error.", style="yellow")
         # Ensure final_answer reflects the error state
         error_msg = state.get('error', 'Unknown error before synthesis')
         return {"final_answer": f"Agent stopped before synthesis due to error: {error_msg}", "total_openai_cost": current_total_openai_cost}

    if is_verbose: print_verbose("Entering Synthesis Node", style="magenta")

    try:
        # Call the updated synthesize_answer function
        answer_text, node_cost = synthesize_answer(
            state['clarified_question'],
            state['combined_context'], # This now contains curated notes from consolidator
            state['plan_outline'],
            verbose=is_verbose
        )
        updated_total_openai_cost = current_total_openai_cost + node_cost
        if is_verbose:
            print_verbose(f"Synthesizer node cost: ${node_cost:.6f}", style="yellow")
            print_verbose(f"Total OpenAI cost updated: ${current_total_openai_cost:.6f} -> ${updated_total_openai_cost:.6f}", style="yellow")
        
        # Verbose printing is handled within synthesize_answer and _post_process_citations
        return {"final_answer": answer_text, "total_openai_cost": updated_total_openai_cost, "error": None} # Clear error on success
    except Exception as e:
        error_msg = f"Synthesis step failed unexpectedly: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Return error and a failure message in final_answer
        return {"error": error_msg, "final_answer": f"Synthesis failed: {e}", "total_openai_cost": current_total_openai_cost}

# __all__ = ['synthesize_node'] # Keep node as main export