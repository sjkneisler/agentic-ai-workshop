# Active Context

## Current Work Focus

The primary focus remains on verifying and refining the **Deep Research Loop** architecture. Recent testing revealed several issues requiring debugging:

- **Repetitive Actions:** The `reason_node` initially got stuck in loops, repeatedly suggesting the same SEARCH query or FETCH URL.
- **State Persistence:** Key pieces of state were not being correctly passed between nodes or iterations, specifically:
    - The query used for search wasn't available for retrieval after fetching/embedding.
    - Search results were being cleared prematurely, preventing the reasoner from considering alternative URLs from the same search.
- **Incorrect Graph Flow:** The graph initially routed back to the `reason_node` after embedding, skipping the crucial retrieval and summarization steps.

Current efforts are focused on:
- **Debugging Loop Logic:** Ensuring the `reason_node` uses state effectively (like `seen_queries`, `seen_urls`, `notes`, persistent `search_results`) to make better decisions and avoid redundant actions.
- **Verifying State Updates:** Confirming that state variables (`query_for_retrieval`, `seen_urls`, `search_results`) are correctly updated and preserved by each node and the LangGraph framework.
- **Testing Corrected Flow:** Running the agent to confirm the intended `Embed -> Retrieve -> Summarize -> Reasoner` flow is now executing.
- **Refinement:** Further tuning of the `reasoner_node` prompt might be needed if suboptimal decisions persist.
- **Testing:** Updating `pytest` tests remains a pending task.

## Recent Changes (Deep Research Loop Implementation & Debugging)

**Initial Implementation:**
- **New Graph Structure:** Defined in `agent/__init__.py`.
- **Reasoner Refactor:** `agent/nodes/reasoner.py` became a decision-making LLM call.
- **New Nodes Added:** `search`, `fetch`, `chunk_embed`, `retrieve`, `summarize`, `consolidate` nodes created in `agent/nodes/`.
- **New Tool Added:** `fetch_url` tool in `agent/tools/fetch.py`.
- **State Update:** Added fields to `agent/state.py` for loop control and data handling.
- **Synthesizer Update:** Modified for citation handling.
- **Configuration Update:** Added sections to `config.yaml` / `agent/config.py`.
- **Dependencies Update:** Added `requests-html`, `lxml[html_clean]`, `sentence-transformers`.
- **File Organization:** Nodes moved into `agent/nodes/`.

**Debugging Fixes (This Session):**
- **`reasoner.py`:**
    - Added tracking of `seen_queries` to state and prompt to prevent repeating exact searches.
    - Added tracking of `seen_urls` to state and prompt to prevent repeating exact fetches.
    - Strengthened prompt instructions to avoid fetching seen URLs and consider alternatives.
    - Corrected logic to stop clearing `search_results` prematurely, allowing results to persist across iterations.
    - Introduced `query_for_retrieval` state variable to correctly pass the relevant query from SEARCH through FETCH/EMBED to RETRIEVE. Updated state update logic accordingly.
- **`chunk_embed.py`:**
    - Implemented batching for `vector_store.add_documents()` to handle OpenAI token limits for large pages.
    - Corrected state update logic to preserve `query_for_retrieval` (previously tried preserving `current_query` incorrectly).
- **`state.py`:**
    - Added `query_for_retrieval: Optional[str]` field.
    - Added `seen_urls: Set[str]` field.
- **`__init__.py`:**
    - Corrected graph flow: Added conditional edge logic (`route_after_chunk_embed`) to route from `chunk_and_embed_node` -> `retrieve_relevant_chunks_node` (using `query_for_retrieval`) instead of back to `reason_node`.
    - Fixed `ImportError` for `AgentState`.
- **`retrieve.py`:**
    - Modified to use `query_for_retrieval` from state for vector store query instead of `current_query`.

*(Previous changes like initial LangGraph adoption, RAG implementation, Clarifier implementation, etc., are documented below)*

--- (Previous Change Log Snippets for Context) ---

- **Refactored Reasoner to Iterative Agent:** ... (details omitted for brevity - superseded by Deep Research Loop) ...
- **Refactored Agent Pipeline to LangGraph:** ... (details omitted for brevity) ...
- **Centralized Shared Utilities:** ... (details omitted for brevity) ...
- *(... and so on for other previous changes ...)*

## Next Steps

1.  **Verify Current Fixes:**
    *   Run the agent again (`python3 main.py "..." --verbose`) to confirm that:
        *   `search_results` persist across iterations.
        *   The agent attempts to fetch *different* URLs from the search results if the first is already seen.
        *   The flow correctly proceeds `Embed -> Retrieve -> Summarize`.
2.  **Refine Reasoner (If Needed):** If the agent still makes suboptimal choices (e.g., unnecessary searches when unseen URLs are available), further refine the `reasoner.py` system prompt or logic.
3.  **Run/Update Automated Tests:**
    *   Execute `python3 -m pytest`. Tests will need significant updates for the new architecture and state variables.
4.  **Update README & Docs:**
    *   Ensure README reflects the corrected flow and new state variables (`query_for_retrieval`, `seen_urls`).
5.  **Polish Pass:**
    *   Pin requirements, validate configs, review outputs, address TODOs.

## Active Decisions & Considerations

- **Agent Architecture:** Confirmed as explicit "Deep Research Loop" graph. Flow corrected to `Embed -> Retrieve -> Summarize -> Reasoner`.
- **Reasoner:** Remains central decision-maker. Prompt strengthened to handle `seen_urls` and persistent `search_results`.
- **State Management:**
    - Introduced `query_for_retrieval` to pass the correct context from Search to Retrieve.
    - Introduced `seen_urls` to prevent redundant fetches.
    - Modified `reasoner.py` to persist `search_results` across iterations until consolidation/stop.
- **Content Handling:** Fetch -> Chunk/Batch Embed -> Retrieve -> Summarize flow implemented. Batching added to embedding for large documents.
- **Vector Store:** Still ephemeral in-memory Chroma per run.
- **Summarization/Consolidation/Source Tracking:** No changes in this session.
- **Configuration/File Structure:** No changes in this session.
- **Testing:** Still requires significant updates.