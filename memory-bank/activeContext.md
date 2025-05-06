# Active Context

## Current Work Focus

The primary focus is on **Enhancing Agent Observability and Efficiency**.
Current efforts are focused on:
- Implementing **Prompt Logging** (Complete for core LLM nodes). This allows for better debugging, analysis of LLM interactions, and data collection.
- Preparing for the implementation of **Persistent Website Caching** with ChromaDB and a Time-To-Live (TTL) mechanism to avoid redundant web fetches and indexing.
- Ongoing **Testing and Refinement** of the Deep Research Loop architecture.

## Recent Changes

**Prompt Logging Implementation (This Session):**
- **Configuration:**
    - Added a `prompt_logging` section to `config.yaml` with `enabled` and `log_file_path` options.
    - Updated `agent/config.py` with `prompt_logging` in `DEFAULT_CONFIG` and a `get_prompt_logging_config()` getter.
- **Utility:**
    - Created `log_prompt_data` function in `agent/utils.py` to handle writing timestamped prompt, response, and metadata to a JSONL file.
- **Node Integration:**
    - Integrated `log_prompt_data` into the following LLM-interacting nodes:
        - `agent/nodes/clarifier.py` (for both clarification check and refinement/outline generation calls)
        - `agent/nodes/reasoner.py` (for the decision-making call)
        - `agent/nodes/summarize.py` (for the summarization call)
        - `agent/nodes/synthesizer.py` (for the final answer synthesis call)
- **Bug Fixes during Logging Implementation:**
    - Resolved `NameError: name 'Dict' is not defined` in `agent/utils.py` by adding `Dict` to `typing` imports.
    - Resolved `AttributeError: 'ChatOpenAI' object has no attribute 'model'` in `agent/nodes/clarifier.py` by correcting access to `model_name` and `temperature` on LangChain LLM objects for logging.

**(Previous Session: Deep Research Loop Implementation & Debugging)**
- **Initial Implementation:**
    - New Graph Structure: Defined in `agent/__init__.py`.
    - Reasoner Refactor: `agent/nodes/reasoner.py` became a decision-making LLM call.
    - New Nodes Added: `search`, `fetch`, `chunk_embed`, `retrieve`, `summarize`, `consolidate` nodes created in `agent/nodes/`.
    - New Tool Added: `fetch_url` tool in `agent/tools/fetch.py`.
    - State Update: Added fields to `agent/state.py` for loop control and data handling.
    - Synthesizer Update: Modified for citation handling.
    - Configuration Update: Added sections to `config.yaml` / `agent/config.py`.
    - Dependencies Update: Added `requests-html`, `lxml[html_clean]`, `sentence-transformers`.
    - File Organization: Nodes moved into `agent/nodes/`.
- **Debugging Fixes (Previous Session):**
    - `reasoner.py`: Added `seen_queries`, `seen_urls`; strengthened prompt; corrected `search_results` persistence; introduced `query_for_retrieval`.
    - `chunk_embed.py`: Implemented batching; corrected `query_for_retrieval` preservation.
    - `state.py`: Added `query_for_retrieval`, `seen_urls`.
    - `__init__.py`: Corrected graph flow (`route_after_chunk_embed`); fixed `ImportError`; made recursion limit configurable.
    - `retrieve.py`: Modified to use `query_for_retrieval`.
    - `agent/tools/fetch.py`: Fixed `NameError: name 'requests_html' is not defined`.
    - `agent/config.py`: Added `graph` section and getter.
    - `config.yaml`: Added `graph` section.

--- (Previous Change Log Snippets for Context) ---

- **Refactored Reasoner to Iterative Agent:** ... (details omitted for brevity - superseded by Deep Research Loop) ...
- **Refactored Agent Pipeline to LangGraph:** ... (details omitted for brevity) ...
- **Centralized Shared Utilities:** ... (details omitted for brevity) ...
- *(... and so on for other previous changes ...)*

## Next Steps

1.  **Implement Persistent Website Caching:**
    *   Upgrade `session_vector_store` (ChromaDB) to be persistent.
    *   Implement a TTL mechanism, potentially using SQLite to track URL indexing timestamps.
    *   Modify `reasoner_node` to consider these timestamps.
    *   Update `chunk_embed_node` to record successful indexing timestamps.
    *   Make ChromaDB path and TTL configurable.
2.  **Verify Prompt Logging:**
    *   Run the agent with logging enabled (`config.yaml`).
    *   Inspect the generated log file (`logs/prompt_logs.jsonl` by default) to ensure correct format and content.
3.  **Verify Deep Research Loop Fixes (If not already confirmed):**
    *   Run the agent again (`python3 main.py "..." --verbose`) to confirm:
        *   `search_results` persist.
        *   Agent attempts different URLs if first is seen.
        *   Flow correctly proceeds `Embed -> Retrieve -> Summarize`.
4.  **Refine Reasoner (If Needed):** If suboptimal choices persist.
5.  **Run/Update Automated Tests:**
    *   Execute `python3 -m pytest`. Tests will need significant updates for new architecture, state variables, and new features like logging and caching.
6.  **Update README & Docs:**
    *   Reflect prompt logging feature.
    *   Reflect persistent caching feature (once implemented).
    *   Ensure README reflects corrected flow, state variables, and configuration options.
7.  **Polish Pass:**
    *   Pin requirements, validate all configs, review outputs, address TODOs.

## Active Decisions & Considerations

- **Agent Architecture:** Confirmed as explicit "Deep Research Loop" graph. Flow corrected to `Embed -> Retrieve -> Summarize -> Reasoner`.
- **Observability:** Implemented prompt logging to `agent/utils.py` and integrated into core LLM nodes (`clarifier`, `reasoner`, `summarizer`, `synthesizer`) for better insight into LLM interactions. Configurable via `config.yaml`.
- **Reasoner:** Remains central decision-maker. Prompt strengthened to handle `seen_urls` and persistent `search_results`.
- **State Management:**
    - Introduced `query_for_retrieval` to pass the correct context from Search to Retrieve.
    - Introduced `seen_urls` to prevent redundant fetches.
    - Modified `reasoner.py` to persist `search_results` across iterations until consolidation/stop.
- **Content Handling:** Fetch -> Chunk/Batch Embed -> Retrieve -> Summarize flow implemented. Batching added to embedding for large documents.
- **Vector Store:** Currently ephemeral in-memory Chroma per run. Next step is to make this persistent with TTL.
- **Summarization/Consolidation/Source Tracking:** No changes in this session beyond integrating prompt logging.
- **Configuration/File Structure:**
    - Added `graph` section to `config.yaml` and `agent/config.py` for `recursion_limit`.
    - Added `prompt_logging` section to `config.yaml` and `agent/config.py`.
    - Added `log_prompt_data` utility to `agent/utils.py`.
    - Fetch tool (`agent/tools/fetch.py`) import corrected in previous session.
- **Testing:** Still requires significant updates. Prompt logging and upcoming caching will require new test considerations.