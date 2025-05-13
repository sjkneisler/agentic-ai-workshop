"""
LangGraph node for consolidating and re-ranking generated notes
before final synthesis.
"""
import warnings
from typing import Dict, Any, List, Tuple

# State and Config
from agent.state import AgentState, StructuredNote # Import StructuredNote
from agent.config import get_consolidator_config
from langchain_core.documents import Document # Import Document for type hinting

# Sentence Transformers for re-ranking
try:
    from sentence_transformers.cross_encoder import CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    warnings.warn("sentence-transformers library not found. Consolidation re-ranking will be skipped.")
    class CrossEncoder: # Dummy class
        def __init__(self, model_name): pass
        def predict(self, pairs): return [0.0] * len(pairs)


# Shared Utilities
from agent.utils import print_verbose

# --- LangGraph Node ---

def consolidate_notes_node(state: AgentState) -> Dict[str, Any]:
    """
    Consolidates notes, optionally re-ranks them using a cross-encoder
    against the original question, and prepares the final context
    for the synthesizer node.
    """
    is_verbose = state['verbosity_level'] == 2
    # Don't check for error here? If reasoning finished, consolidation should run.
    # If a prior node errored, the graph should handle routing. Let's proceed.
    # if state.get("error"):
    #     if is_verbose: print_verbose("Skipping consolidation due to previous error.", style="yellow")
    #     return {} # Or return the error state?

    if is_verbose: print_verbose("Entering Consolidate Notes Node", style="magenta")

    structured_notes: List[StructuredNote] = state.get('notes', []) # Now expects List[StructuredNote]
    question: str = state['clarified_question']

    if not structured_notes:
        if is_verbose: print_verbose("No notes to consolidate.", style="dim blue")
        return {"combined_context": "No information gathered during research.", "error": None}

    consolidator_config = get_consolidator_config()
    rerank = consolidator_config.get('rerank', True) # Default to re-ranking
    top_n = consolidator_config.get('top_n', 20) # Default top N notes
    model_name = consolidator_config.get('cross_encoder_model', 'cross-encoder/ms-marco-MiniLM-L-12-v2')

    # Extract summaries for ranking, but keep structured_notes intact
    summaries_for_ranking = [sn['summary'] for sn in structured_notes]
    ranked_structured_notes = structured_notes # Default to original order

    if rerank and SENTENCE_TRANSFORMERS_AVAILABLE and len(structured_notes) > 1:
        if is_verbose: print_verbose(f"Re-ranking {len(structured_notes)} notes using cross-encoder: {model_name}", style="dim blue")
        try:
            # Prepare pairs for the cross-encoder: (query, summary_text)
            query_summary_pairs: List[Tuple[str, str]] = [(question, sn['summary']) for sn in structured_notes]

            cross_encoder = CrossEncoder(model_name)
            scores = cross_encoder.predict(query_summary_pairs)

            # Combine structured_notes with scores and sort
            # We sort the original structured_notes list based on these scores
            # to keep the source_chunks associated with their summaries.
            scored_structured_notes = sorted(
                zip(structured_notes, scores),
                key=lambda x: x[1],
                reverse=True
            )

            # Select top N structured notes
            ranked_structured_notes = [sn_with_score[0] for sn_with_score in scored_structured_notes[:top_n]]

            if is_verbose:
                print_verbose(f"Selected top {len(ranked_structured_notes)} structured notes after re-ranking.", style="green")
                # for i, (sn, score) in enumerate(scored_structured_notes[:5]):
                #     print_verbose(f"  Rank {i+1} (Score: {score:.4f}): {sn['summary'][:100]}...", style="dim")

        except Exception as e:
            warnings.warn(f"Cross-encoder re-ranking failed: {e}. Using original note order.")
            if is_verbose: print_verbose(f"Cross-encoder re-ranking failed: {e}", style="red")
            ranked_structured_notes = structured_notes[:top_n] # Fallback to top N of original order

    elif not SENTENCE_TRANSFORMERS_AVAILABLE and rerank:
         if is_verbose: print_verbose("Sentence-transformers library not found. Skipping re-ranking.", style="yellow")
         ranked_structured_notes = structured_notes[:top_n] # Apply top_n even without ranking
    else:
         # No re-ranking requested or only one note
         ranked_structured_notes = structured_notes[:top_n]
         if is_verbose: print_verbose(f"Selecting top {len(ranked_structured_notes)} notes (re-ranking skipped or not needed).", style="dim blue")


    # Format the final context for the synthesizer
    # Using Markdown format as suggested in the plan ("curated_notes.md")
    final_context_parts = [f"# Curated Research Information for: {question}\n"]
    final_context_parts.append("## Summarized Notes (Ranked):\n")

    for i, structured_note_item in enumerate(ranked_structured_notes):
        final_context_parts.append(f"### Summary Note {i+1}:\n{structured_note_item['summary']}")
        final_context_parts.append(f"\n#### Supporting Raw Chunks for Summary Note {i+1}:\n")
        for chunk_idx, chunk_doc in enumerate(structured_note_item['source_chunks']):
            url = chunk_doc.metadata.get('url', 'Unknown Source')
            title = chunk_doc.metadata.get('title', 'Unknown Title')
            original_chunk_idx = chunk_doc.metadata.get('chunk_index', 'N/A')
            final_context_parts.append(f"##### Chunk {chunk_idx+1} (Original Index: {original_chunk_idx}, From: {title} - {url}):\n{chunk_doc.page_content}\n")
        final_context_parts.append("\n---\n")

    final_context_parts.append("\nEnd of Curated Information.")
    final_context = "\n".join(final_context_parts)

    return {"combined_context": final_context, "error": None}


# Example of how to add consolidator config to config.yaml
# consolidator:
#   rerank: true
#   top_n: 20
#   cross_encoder_model: 'cross-encoder/ms-marco-MiniLM-L-12-v2'