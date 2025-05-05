"""
LangGraph node for consolidating and re-ranking generated notes
before final synthesis.
"""
import warnings
from typing import Dict, Any, List, Tuple

# State and Config
from agent.state import AgentState
from agent.config import get_consolidator_config # Need to add this to config.py

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

    notes: List[str] = state.get('notes', [])
    question: str = state['clarified_question']

    if not notes:
        if is_verbose: print_verbose("No notes to consolidate.", style="dim blue")
        # Pass empty context to synthesizer? Or signal an issue?
        return {"combined_context": "No information gathered during research.", "error": None}

    consolidator_config = get_consolidator_config()
    rerank = consolidator_config.get('rerank', True) # Default to re-ranking
    top_n = consolidator_config.get('top_n', 20) # Default top N notes
    model_name = consolidator_config.get('cross_encoder_model', 'cross-encoder/ms-marco-MiniLM-L-12-v2')

    ranked_notes = notes # Default to original order if no re-ranking

    if rerank and SENTENCE_TRANSFORMERS_AVAILABLE and len(notes) > 1:
        if is_verbose: print_verbose(f"Re-ranking {len(notes)} notes using cross-encoder: {model_name}", style="dim blue")
        try:
            # Prepare pairs for the cross-encoder: (query, note)
            query_note_pairs: List[Tuple[str, str]] = [(question, note) for note in notes]

            # Initialize the cross-encoder model
            # Consider caching this model initialization if called frequently
            cross_encoder = CrossEncoder(model_name)

            # Predict scores
            scores = cross_encoder.predict(query_note_pairs)

            # Combine notes with scores and sort
            notes_with_scores = list(zip(notes, scores))
            notes_with_scores.sort(key=lambda x: x[1], reverse=True) # Sort descending by score

            # Select top N notes
            ranked_notes = [note for note, score in notes_with_scores[:top_n]]

            if is_verbose:
                print_verbose(f"Selected top {len(ranked_notes)} notes after re-ranking.", style="green")
                # Optionally print scores or top notes for debugging
                # for i, (note, score) in enumerate(notes_with_scores[:5]):
                #     print_verbose(f"  Rank {i+1} (Score: {score:.4f}): {note[:100]}...", style="dim")

        except Exception as e:
            warnings.warn(f"Cross-encoder re-ranking failed: {e}. Using original note order.")
            if is_verbose: print_verbose(f"Cross-encoder re-ranking failed: {e}", style="red")
            ranked_notes = notes[:top_n] # Fallback to top N of original order

    elif not SENTENCE_TRANSFORMERS_AVAILABLE and rerank:
         if is_verbose: print_verbose("Sentence-transformers library not found. Skipping re-ranking.", style="yellow")
         ranked_notes = notes[:top_n] # Apply top_n even without ranking
    else:
         # No re-ranking requested or only one note
         ranked_notes = notes[:top_n]
         if is_verbose: print_verbose(f"Selecting top {len(ranked_notes)} notes (re-ranking skipped or not needed).", style="dim blue")


    # Format the final context for the synthesizer
    # Using Markdown format as suggested in the plan ("curated_notes.md")
    final_context = f"# Curated Research Notes for: {question}\n\n"
    final_context += "Based on the research, here are the key points:\n\n"
    final_context += "\n\n".join(f"## Note {i+1}\n{note}" for i, note in enumerate(ranked_notes))
    final_context += "\n\n---\nEnd of Notes."

    # Update state with the consolidated context
    # The synthesizer will now use 'combined_context' which contains the curated notes.
    return {"combined_context": final_context, "error": None}


# Example of how to add consolidator config to config.yaml
# consolidator:
#   rerank: true
#   top_n: 20
#   cross_encoder_model: 'cross-encoder/ms-marco-MiniLM-L-12-v2'