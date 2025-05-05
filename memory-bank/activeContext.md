# Active Context

## Current Work Focus

The agent pipeline has undergone a major refactoring to implement a **Deep Research Loop** architecture. This replaces the previous iterative LangChain Agent-based reasoner with a more explicit, multi-node graph structure.

The current focus is on:
- **Verification:** Testing this new Clarify -> [Reason -> Search/Fetch/Embed/Retrieve/Summarize]* -> Consolidate -> Synthesize flow. Ensuring the reasoner node makes sensible decisions and the loop progresses correctly.
- **Refinement:** Tuning prompts (Reasoner decision, Summarizer, Synthesizer), component settings (chunk size, retriever K, consolidator top_n), and iteration limits (`config.yaml`).
- **Citation Handling:** Verifying the accuracy and formatting of the citation post-processing in the synthesizer.
- **Testing:** Updating `pytest` tests to reflect the new graph structure and node interactions.

## Recent Changes (Deep Research Loop Implementation)

- **New Graph Structure:** Defined in `agent/__init__.py`, orchestrating a loop involving fetching, chunking, embedding, retrieving, and summarizing web content.
- **Reasoner Refactor:** `agent/nodes/reasoner.py` (`reason_node`) no longer runs a self-contained agent. It now uses an LLM call to analyze state (question, outline, notes, iteration) and decide the `next_action` (SEARCH, FETCH, RETRIEVE_CHUNKS, CONSOLIDATE, STOP), directing the graph flow.
- **New Nodes Added (`agent/nodes/`):**
    - `search.py`: Executes web search based on reasoner query.
    - `fetch.py`: Fetches URL content using the new `fetch_url` tool.
    - `chunk_embed.py`: Chunks/embeds fetched HTML into a session vector store (in-memory Chroma).
    - `retrieve.py`: Retrieves relevant chunks from the session store based on reasoner query.
    - `summarize.py`: Summarizes retrieved chunks into notes with detailed embedded citations.
    - `consolidate.py`: Re-ranks notes using a cross-encoder and prepares context for synthesis.
- **New Tool Added (`agent/tools/`):**
    - `fetch.py`: `fetch_url` tool using `requests-html` to get page content.
- **State Update (`agent/state.py`):** Added fields for `session_vector_store`, `notes`, `fetched_docs`, `retrieved_chunks`, `current_iteration`, `next_action`, `current_query`, `url_to_fetch`.
- **Synthesizer Update (`agent/nodes/synthesizer.py`):** Modified prompts to preserve detailed citations; added post-processing step to create a numbered reference list.
- **Configuration Update (`agent/config.py`):** Added default configs and getters for `embedding`, `summarizer`, `retriever`, `consolidator`. Updated `reasoner` and `synthesizer` defaults/prompts.
- **Dependencies Update (`requirements.txt`):** Added `requests-html`, `lxml[html_clean]`, `sentence-transformers`.
- **File Organization:** Moved `clarifier.py`, `reasoner.py`, `synthesizer.py` into `agent/nodes/`. Removed old `search_node` from `agent/search.py`.

*(Previous changes like initial LangGraph adoption, RAG implementation, Clarifier implementation, etc., are documented below)*

--- (Previous Change Log Snippets for Context) ---

- **Refactored Reasoner to Iterative Agent:** ... (details omitted for brevity - superseded by Deep Research Loop) ...
- **Refactored Agent Pipeline to LangGraph:** ... (details omitted for brevity) ...
- **Centralized Shared Utilities:** ... (details omitted for brevity) ...
- *(... and so on for other previous changes ...)*

## Next Steps

1.  **Install/Update Dependencies:**
    *   Run `python3 -m pip install -r requirements.txt` (ensure `requests-html`, `lxml[html_clean]`, `sentence-transformers` are installed).
2.  **Configure Environment & Config:**
    *   Ensure `.env` has valid `SERPER_API_KEY` and `OPENAI_API_KEY`.
    *   Review/modify `config.yaml`, especially the sections for `reasoner`, `embedding`, `summarizer`, `retriever`, `consolidator`, `synthesizer`. Pay attention to model choices, prompts, and thresholds (e.g., `max_iterations`, `top_n`).
3.  **Manual Testing (Focus on New Deep Research Loop):**
    *   Run with verbose mode: `python3 main.py "Your question here" --verbose`
    *   **Test Clarifier:** Verify outline generation.
    *   **Test Research Loop:**
        *   Observe `reason_node` decisions (`next_action`).
        *   Check if `search_node` runs with the correct query.
        *   Check if `fetch_node` gets the right URL.
        *   Check if `chunk_and_embed_node` processes content and adds to the (transient) store.
        *   Check if `retrieve_relevant_chunks_node` gets chunks based on reasoner query.
        *   Check if `summarize_chunks_node` creates notes with correct citation format.
        *   Verify loop continues up to `max_iterations` or until `CONSOLIDATE`/`STOP` is decided.
    *   **Test Consolidation:** Examine `combined_context` passed to synthesizer (in verbose logs) - does it contain ranked notes?
    *   **Test Synthesizer:** Does the final answer make sense? Are citations correctly formatted with a reference list?
4.  **Run/Update Automated Tests:**
    *   Execute `python3 -m pytest`. Tests will need significant updates to mock the new graph structure and node interactions.
5.  **Address Issues:** Fix bugs identified during testing (e.g., prompt tuning, node logic errors, citation formatting).
6.  **Consider Enhancements:** Improve HTML cleaning (`trafilatura`), add RAG integration, refine reasoner decision logic.

## Active Decisions & Considerations

- **Agent Architecture:** Shifted to an explicit, multi-node "Deep Research Loop" graph controlled by a central `reason_node`.
- **Reasoner:** Now a decision-making node, not a self-contained agent executor. Uses LLM to choose next step (SEARCH, FETCH, RETRIEVE_CHUNKS, CONSOLIDATE, STOP).
- **Content Handling:** Agent now fetches full HTML, chunks/embeds into a session store, retrieves, and summarizes before final synthesis.
- **Vector Store:** Uses an ephemeral, in-memory Chroma store (`session_vector_store`) for each run, managed via `chunk_and_embed_node`. Persistent RAG store (`agent/rag.py`, `agent/rag_utils/`) is currently unused by the main loop.
- **Summarization:** Happens per retrieval step, generating source-grounded notes using a smaller LLM.
- **Consolidation:** Notes are re-ranked using a cross-encoder before final synthesis.
- **Source Tracking:** Implemented via detailed embedded citations in notes and post-processing in the synthesizer to create a reference list.
- **Configuration:** Added sections and getters in `config.yaml`/`agent/config.py` for new components.
- **File Structure:** Core nodes (`clarifier`, `reasoner`, `synthesizer`) moved to `agent/nodes/`. New nodes and tools placed in `agent/nodes/` and `agent/tools/`.
- **Testing:** Automated tests require significant updates.