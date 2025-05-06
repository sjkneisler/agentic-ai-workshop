Below is a **two-tier implementation roadmap** reflecting the current agent architecture (Deep Research Loop):

*Tier 1* = discrete “work chunks” the coding agent can tackle sequentially.
*Tier 2* = fine-grained steps inside each chunk.

---

## 📊 Tier 1 — Work Chunks (macro tasks) - REVISED for Deep Research Loop

| Chunk # | Deliverable                                  | Purpose                                                                                                                               | Status |
| ------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **0**   | *Repo Bootstrap*                             | Git repo initialized with layout skeleton, config, and minimal tooling.                                                               | ✅     |
| **1**   | *Core Runtime Skeleton*                      | `main.py` CLI shell + `agent/` package with initial `utils.py`, `state.py`.                                                           | ✅     |
| **2**   | *Serper Search Utility*                      | Working `search.py` (`serper_search`) utility function.                                                                               | ✅     |
| **3**   | *RAG Functionality (Langchain)*              | `rag_utils` (`initializer`, `query`) using Langchain. `rag.py` interface. (Kept but unused by main loop).                              | ✅     |
| **4**   | *Initial Synthesis Module*                   | Implement initial `synthesizer.py` (`synthesize_node`).                                                                               | ✅     |
| **5**   | *Initial Clarifier Module*                   | Implement initial `clarifier.py` (`clarify_node`) including outline generation.                                                       | ✅     |
| **6**   | *Initial Reasoner Agent Module*              | Implement initial `reasoner.py` (`reason_node`) with iterative tool-using agent (Search/RAG). (Superseded by Deep Loop).               | ✅     |
| **7**   | *Initial LangGraph Wiring*                   | Define & compile `StateGraph` in `agent/__init__.py`, connecting `clarify`->`reason(agent)`->`synthesize`. (Superseded by Deep Loop). | ✅     |
| **8**   | **Deep Research Loop Implementation**        | Refactor graph for Fetch->Chunk/Embed->Retrieve->Summarize loop, new nodes, refactored reasoner, citation handling.                    | ✅     |
| **9**   | *Local Tests*                                | `pytest` with mocks (needs significant update for new flow).                                                                          | ⏳     |
| **10**  | *README & Docs*                              | Populate README reflecting new architecture. Update Memory Bank (this process).                                                       | ⏳     |
| **11**  | *Polish Pass*                                | Verify `.env.example`, `config.yaml`, print-styles, error messages, requirements pinning.                                             | ⏳     |
| **12**  | *Prompt Logging System*                      | Implement configurable logging for LLM prompts and responses to aid debugging and analysis.                                             | ✅     |
| **13**  | *OpenAI API Cost Tracking*                   | Implement tracking and display of estimated OpenAI API costs per run.                                                                 | ✅     |

---

## 🔍 Tier 2 — Detailed Steps per Chunk - REVISED for Deep Research Loop

*(Chunks 0-7 represent the previous state before the Deep Research Loop refactor and are omitted here for brevity, assuming they were completed as documented previously)*

### **Chunk 8 – Deep Research Loop Implementation** (✅)

1.  **Dependencies:** Add `requests-html`, `lxml[html_clean]`, `sentence-transformers` to `requirements.txt`. Install.
2.  **Fetch Tool:** Create `agent/tools/fetch.py` with `fetch_url` tool using `requests-html`.
3.  **State Update:** Add `session_vector_store`, `notes`, `fetched_docs`, `retrieved_chunks`, `current_iteration`, `next_action`, etc., to `agent/state.py`.
4.  **New Nodes:** Create node files in `agent/nodes/`:
    *   `chunk_embed.py`: `chunk_and_embed_node` (uses Chroma in-memory, OpenAI embeddings).
    *   `retrieve.py`: `retrieve_relevant_chunks_node` (queries session store).
    *   `summarize.py`: `summarize_chunks_node` (uses small LLM, embeds detailed citations).
    *   `consolidate.py`: `consolidate_notes_node` (uses cross-encoder for re-ranking).
    *   `search.py`: `search_node` (calls `serper_search` utility).
    *   `fetch.py`: `fetch_node` (calls `fetch_url` tool).
5.  **Reasoner Refactor:** Rewrite `agent/reasoner.py` (`reason_node`) to be the decision-making LLM call, outputting `next_action` and arguments.
6.  **Synthesizer Update:** Modify `agent/synthesizer.py` (`synthesize_node`) prompt to preserve detailed citations; add post-processing regex logic for reference list generation.
7.  **Config Update:** Add default sections and getters for `embedding`, `summarizer`, `retriever`, `consolidator` to `agent/config.py`. Update `reasoner` and `synthesizer` prompts/defaults. Ensure `config.yaml` can override these.
8.  **File Organization:** Move `clarifier.py`, `reasoner.py`, `synthesizer.py` to `agent/nodes/`. Remove old `search_node` from `agent/search.py`.
9.  **Graph Wiring:** Rewrite `agent/__init__.py` to import all nodes, define conditional routing logic (`route_after_reasoning`, `route_after_chunk_embed`), and connect the full graph flow (Clarify -> Reason -> [Search | Fetch -> Embed -> Retrieve -> Summarize] -> Reason -> ... -> Consolidate -> Synthesize -> END). Update initial state in `run_agent`.
10. **Commit:** "Implement deep research loop architecture."

### **Chunk 9 – Local Tests** (⏳)

1.  Update `test_agent.py`:
    *   Mock new nodes (`fetch_node`, `chunk_embed_node`, etc.).
    *   Test graph invocation with different paths based on mocked reasoner decisions.
    *   Test citation post-processing logic in isolation.
2.  Commit: “Update pytest coverage for deep research loop.”

### **Chunk 10 – README & Docs** (⏳)

1.  Update README sections (How it Works, Config, etc.) for the deep research loop.
2.  Update Memory Bank files (this process).
3.  Commit: “Update documentation for deep research loop.”

### **Chunk 11 – Polish Pass** (⏳)

1.  Pin package versions in `requirements.txt`.
2.  Validate `.env.example` and `config.yaml` defaults and structure.
3.  Review print styles (`print_verbose`) and error messages across all nodes.
4.  Address any remaining TODOs.
5.  Commit: “Final polish and documentation update.”

### **Chunk 12 – Prompt Logging System** (✅)

1.  **Configuration:** Add `prompt_logging` section to `config.yaml` (with `enabled`, `log_file_path`) and to `DEFAULT_CONFIG` in `agent/config.py` with a corresponding getter function.
2.  **Utility Function:** Create `log_prompt_data(node_name, prompt, response, additional_info)` in `agent/utils.py` to handle JSONL file writing, directory creation, and timestamping.
3.  **Node Integration:** Import and call `log_prompt_data` in `agent/nodes/clarifier.py`, `agent/nodes/reasoner.py`, `agent/nodes/summarize.py`, and `agent/nodes/synthesizer.py` after LLM invocations.
4.  **Bug Fixing:**
*   Resolve `NameError: name 'Dict' is not defined` in `agent/utils.py` by importing `Dict` from `typing`.
*   Resolve `AttributeError: 'ChatOpenAI' object has no attribute 'model'` in `agent/nodes/clarifier.py` by using `model_name` for LangChain objects.
5.  **Commit:** "Implement prompt logging system for LLM interactions."

### **Chunk 13 – OpenAI API Cost Tracking** (✅)

1.  **State Update:** Add `total_openai_cost: float` to `AgentState` in `agent/state.py`.
2.  **Configuration:**
*   Add `openai_pricing` section to `config.yaml` with model costs.
*   Update `agent/config.py` to load pricing and add `get_openai_pricing_config()` getter.
3.  **Node Integration (Cost Calculation - Refined Approach):**
*   Modify `agent/nodes/clarifier.py`, `reasoner.py`, `chunk_embed.py`, `summarize.py`, `synthesizer.py`.
*   Import `get_openai_callback` (from `langchain_community.callbacks.manager`) and `get_openai_pricing_config` (from `agent.config`).
*   **LLM Nodes (`clarifier.py`, `reasoner.py`, `summarize.py`, `synthesizer.py`):**
    *   Wrap LLM invocations with `get_openai_callback`.
    *   Calculate cost using `cb.total_cost` from the callback handler (relies on Langchain's internal pricing and handles cached prompt tokens).
*   **Embedding Node (`chunk_embed.py`):**
    *   Does not use `get_openai_callback` for cost calculation due to unreliability in capturing embedding token data.
    *   Manually counts tokens for each document batch using `agent.utils.count_tokens(text, model=embedding_model_name)`.
    *   Calculates cost for these manually counted tokens using `cost_per_million_tokens` from the `openai_pricing` section of `config.yaml` (via `get_openai_pricing_config`).
    *   Corrected `TypeError` in `chunk_embed.py` calls to `count_tokens` (changed `model_name=` to `model=`).
*   All nodes update `total_openai_cost` in the state returned by each node.
4.  **Agent Runner Update:** Modify `run_agent` in `agent/__init__.py` to initialize `total_openai_cost` in `AgentState` and return it.
5.  **Display Cost:** Update `main.py` to receive and print the `total_openai_cost`.
6.  **Commit:** "Implement OpenAI API cost tracking and display."

---

### 🏁 Handoff Instructions for Coding Agent

*   Work through remaining chunks (Tests, Docs, Polish).
*   After each commit, run `python main.py` (with mocks/keys) and `pytest`.
*   Do **not** introduce new dependencies unless specified.
*   Keep logs concise unless `--verbose`.
*   Ask for clarification only if blocking specification gaps remain.

---