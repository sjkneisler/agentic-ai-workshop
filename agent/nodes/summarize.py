"""
LangGraph node for summarizing retrieved document chunks into source-grounded notes.
"""
import warnings
from typing import Dict, Any, List

# State and Config
from agent.state import AgentState
from agent.config import get_summarizer_config # Need to add this to config.py

# LangChain components
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage

# Shared Utilities
from agent.utils import print_verbose, initialize_llm, count_tokens, OPENAI_AVAILABLE

# --- LangGraph Node ---

def summarize_chunks_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarizes chunks retrieved from the vector store (expected in state['retrieved_chunks'])
    into a concise note with embedded source citations and appends it to state['notes'].
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"):
        if is_verbose: print_verbose("Skipping summarization due to previous error.", style="yellow")
        return {}

    if is_verbose: print_verbose("Entering Summarize Chunks Node", style="magenta")

    retrieved_chunks: List[Document] = state.get('retrieved_chunks', [])
    if not retrieved_chunks:
        if is_verbose: print_verbose("No retrieved chunks to summarize.", style="dim blue")
        return {"retrieved_chunks": []} # Clear field, nothing to do

    # 1. Initialize Summarizer LLM
    summarizer_config = get_summarizer_config()
    summarizer_llm = initialize_llm(
        model_config_key='model',
        temp_config_key='temperature',
        default_model=summarizer_config.get('model', 'gpt-3.5-turbo'),
        default_temp=summarizer_config.get('temperature', 0.0)
    )

    if not summarizer_llm:
        error_msg = "Failed to initialize LLM for Summarizer Node."
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "retrieved_chunks": []}

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
        response = summarizer_llm.invoke(messages)
        summary_note = response.content if hasattr(response, 'content') else str(response)

        if not summary_note or not summary_note.strip():
             warnings.warn("Summarizer LLM returned an empty note.")
             summary_note = "[Summary generation failed or produced no output]"
             if is_verbose: print_verbose("Summarizer returned empty output.", style="yellow")
        elif is_verbose:
             print_verbose("Summarizer LLM finished.", style="green")

        # Append the generated note (with embedded citations) to the list
        current_notes = state.get('notes', [])
        current_notes.append(summary_note.strip())

        return {
            "notes": current_notes,
            "retrieved_chunks": [], # Clear processed chunks
            "error": None
        }

    except Exception as e:
        error_msg = f"Summarizer LLM invocation failed: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "retrieved_chunks": []}

# Example config remains the same
# summarizer:
#   model: gpt-3.5-turbo
#   temperature: 0.0
#   system_prompt: "..." # Optional override