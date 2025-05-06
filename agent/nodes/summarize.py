"""
LangGraph node for summarizing retrieved document chunks into source-grounded notes.
"""
import warnings
from typing import Dict, Any, List

# State and Config
from agent.state import AgentState
from agent.config import get_summarizer_config, get_openai_pricing_config # Need to add this to config.py

# Langchain callbacks for token usage
try:
    from langchain_community.callbacks.manager import get_openai_callback
    LANGCHAIN_CALLBACKS_AVAILABLE = True
except ImportError:
    warnings.warn("LangChain callbacks not found. Cost calculation via get_openai_callback will be disabled for summarize.")
    LANGCHAIN_CALLBACKS_AVAILABLE = False

# LangChain components
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage

# Shared Utilities
from agent.utils import print_verbose, initialize_llm, count_tokens, OPENAI_AVAILABLE, log_prompt_data

# --- LangGraph Node ---

def summarize_chunks_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarizes chunks retrieved from the vector store (expected in state['retrieved_chunks'])
    into a concise note with embedded source citations and appends it to state['notes'].
    """
    is_verbose = state['verbosity_level'] == 2
    current_total_openai_cost = state.get('total_openai_cost', 0.0) # Get existing cost

    if state.get("error"):
        if is_verbose: print_verbose("Skipping summarization due to previous error.", style="yellow")
        return {"total_openai_cost": current_total_openai_cost} # Preserve cost

    if is_verbose: print_verbose("Entering Summarize Chunks Node", style="magenta")
    
    current_node_call_cost = 0.0
    pricing_config = get_openai_pricing_config().get('models', {})

    retrieved_chunks: List[Document] = state.get('retrieved_chunks', [])
    if not retrieved_chunks:
        if is_verbose: print_verbose("No retrieved chunks to summarize.", style="dim blue")
        return {"retrieved_chunks": [], "total_openai_cost": current_total_openai_cost} # Clear field, nothing to do

    # 1. Initialize Summarizer LLM
    summarizer_config = get_summarizer_config()
    summarizer_llm = initialize_llm(
        model_config_key='model',
        temp_config_key='temperature',
        default_model=summarizer_config.get('model', 'gpt-4o-mini'),
        default_temp=summarizer_config.get('temperature', 0.0)
    )

    if not summarizer_llm:
        error_msg = "Failed to initialize LLM for Summarizer Node."
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "retrieved_chunks": [], "total_openai_cost": current_total_openai_cost}

    # 2. Format Chunks and Prompt with Detailed Citations
    formatted_chunks = ""
    for i, chunk in enumerate(retrieved_chunks):
        url = chunk.metadata.get('url', 'Unknown Source')
        title = chunk.metadata.get('title', 'Unknown Title').replace("'", "").replace('"', '') # Clean title for citation
        chunk_idx = chunk.metadata.get('chunk_index', 'N/A')
        # Create a detailed, parsable citation string
        citation_tag = f"[Source URL='{url}', Title='{title}', Chunk={chunk_idx}]"

        formatted_chunks += f"--- Source Citation: {citation_tag} ---\n"
        # Optionally include URL/Title again for LLM context, but citation tag is key
        # formatted_chunks += f"URL: {url}\n"
        # formatted_chunks += f"Title: {title}\n"
        formatted_chunks += f"Content:\n{chunk.page_content}\n\n"

    # Updated prompts to use the new citation format
    system_prompt = summarizer_config.get(
        'system_prompt',
        "You are an efficient assistant. Summarize the key facts from the following passages in bullet points (maximum 120 words total). Focus on information relevant to the original query. Keep exact numbers/quotes where possible. **Cite each claim meticulously using the EXACT source citation tag provided with each passage, like [Source URL='...', Title='...', Chunk=...]. Do NOT alter the citation tag format.**"
    )
    user_prompt = f"Original Query (for context): {state['clarified_question']}\n\nPassages to Summarize:\n{formatted_chunks}\n\nInstructions: Provide a concise bullet-point summary (max 120 words) citing sources using the full [Source URL='...', Title='...', Chunk=...] tag format provided above."

    # 3. Invoke LLM
    if is_verbose:
        model_name = getattr(summarizer_llm, 'model_name', 'Unknown')
        print_verbose(f"Invoking summarizer LLM ({model_name})...", style="dim blue")

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        if LANGCHAIN_CALLBACKS_AVAILABLE and summarizer_llm:
            with get_openai_callback() as cb:
                response = summarizer_llm.invoke(messages)
                summary_note = response.content if hasattr(response, 'content') else str(response)
                
                prompt_tokens = cb.prompt_tokens
                completion_tokens = cb.completion_tokens
                model_name = summarizer_llm.model_name if hasattr(summarizer_llm, 'model_name') else summarizer_config.get('model')

                model_pricing_info = pricing_config.get(model_name)
                if model_pricing_info:
                    input_cost = model_pricing_info.get('input_cost_per_million_tokens', 0)
                    output_cost = model_pricing_info.get('output_cost_per_million_tokens', 0)
                    call_cost_iter = (prompt_tokens / 1_000_000 * input_cost) + \
                                     (completion_tokens / 1_000_000 * output_cost)
                    current_node_call_cost += call_cost_iter
                    if is_verbose: print_verbose(f"Summarizer call cost: ${call_cost_iter:.6f}", style="dim yellow")
        else:
            response = summarizer_llm.invoke(messages)
            summary_note = response.content if hasattr(response, 'content') else str(response)
            if is_verbose and not LANGCHAIN_CALLBACKS_AVAILABLE: print_verbose("Langchain callbacks unavailable, skipping cost calculation for summarizer.", style="dim yellow")

        # Log prompt and response
        log_prompt_data(
            node_name="summarize_chunks_node",
            prompt={"system_prompt": system_prompt, "user_prompt": user_prompt},
            response=summary_note,
            additional_info={
                "model": summarizer_llm.model_name if summarizer_llm else summarizer_config.get('model'),
                "temperature": summarizer_llm.temperature if summarizer_llm else summarizer_config.get('temperature'),
                "clarified_question_for_context": state['clarified_question']
            }
        )

        if not summary_note or not summary_note.strip():
             warnings.warn("Summarizer LLM returned an empty note.")
             summary_note = "[Summary generation failed or produced no output]"
             if is_verbose: print_verbose("Summarizer returned empty output.", style="yellow")
        elif is_verbose:
             print_verbose("Summarizer LLM finished.", style="green")

        # Append the generated note (with embedded citations) to the list
        current_notes = state.get('notes', [])
        current_notes.append(summary_note.strip())

        updated_total_openai_cost = current_total_openai_cost + current_node_call_cost
        if is_verbose:
            print_verbose(f"Summarizer node cost: ${current_node_call_cost:.6f}", style="yellow")
            print_verbose(f"Total OpenAI cost updated: ${current_total_openai_cost:.6f} -> ${updated_total_openai_cost:.6f}", style="yellow")

        return {
            "notes": current_notes,
            "retrieved_chunks": [], # Clear processed chunks
            "total_openai_cost": updated_total_openai_cost, # Include updated cost
            "error": None
        }

    except Exception as e:
        error_msg = f"Summarizer LLM invocation failed: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "retrieved_chunks": [], "total_openai_cost": current_total_openai_cost}

# Example config remains the same
# summarizer:
#   model: gpt-4o-mini
#   temperature: 0.0
#   system_prompt: "..." # Optional override