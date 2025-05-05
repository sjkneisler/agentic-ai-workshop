## 🧠 Deep Research Agent – Demo Repo Plan (v1.3 - Deep Research Loop)

This plan is for an AI coding agent (without autonomous web access) to bootstrap and maintain a public-facing repository implementing a recursive research agent. It combines symbolic reasoning structure with runnable modular code, designed to be extended incrementally. This version implements a "deep research" loop involving fetching full content, chunking, embedding, retrieval from a session store, summarization, and consolidation before final synthesis.

---

### 🎯 Purpose

Create a runnable Python project demonstrating a research agent pipeline:

*   **Interactive Clarifier:** Refines the user's question and generates a basic Markdown research outline.
*   **Iterative Research Loop:** Orchestrated by a central Reasoner node, the agent dynamically decides to:
    *   **Search:** Find relevant web pages.
    *   **Fetch:** Retrieve full content from URLs.
    *   **Chunk/Embed:** Process fetched content into a temporary session vector store.
    *   **Retrieve:** Query the session store for relevant chunks.
    *   **Summarize:** Create source-grounded notes from retrieved chunks.
*   **Consolidator:** Re-ranks notes for relevance before synthesis.
*   **Synthesizer:** Generates the final answer from curated notes, including formatted citations.
*   Designed to run in CLI with Serper search.
*   Includes an interactive clarification step using LangChain components.
*   Clear modularity using LangGraph nodes.
*   Low barrier to entry: one script, clearly segmented modules, `.env` / `config.yaml` driven config.

---

### 📂 Repo Layout (Updated)

```
/
├── README.md
├── requirements.txt                 # Python ≥3.10, includes langgraph, requests-html, sentence-transformers
├── .env.example                     # API Keys, RAG Path (RAG currently unused)
├── config.yaml                      # Agent behavior config (models, prompts, iterations, new components) - UPDATED
├── main.py                          # CLI entrypoint
├── agent/
│   ├── __init__.py                 # Defines LangGraph graph, imports nodes - UPDATED
│   ├── state.py                    # Defines AgentState TypedDict - UPDATED (session store, notes, etc.)
│   ├── utils.py                    # Shared utilities (logging, LLM init, etc.)
│   ├── config.py                   # Config loader - UPDATED (new component configs)
│   ├── search.py                   # serper_search() utility function
│   ├── rag.py                      # RAG interface (kept for future use)
│   ├── rag_utils/                  # RAG utilities (kept for future use)
│   │   ├── ...
│   ├── tools/                      # Directory for tools
│   │   └── fetch.py                # fetch_url() tool - NEW
│   └── nodes/                      # Directory for LangGraph nodes - NEW/REORGANIZED
│       ├── clarifier.py            # clarify_node() - MOVED
│       ├── reasoner.py             # reason_node() (Decision Maker) - MOVED & REFACTORED
│       ├── synthesizer.py          # synthesize_node() - MOVED & UPDATED (citations)
│       ├── search.py               # search_node() - NEW
│       ├── fetch.py                # fetch_node() - NEW
│       ├── chunk_embed.py          # chunk_and_embed_node() - NEW
│       ├── retrieve.py             # retrieve_relevant_chunks_node() - NEW
│       ├── summarize.py            # summarize_chunks_node() - NEW (with citations)
│       └── consolidate.py          # consolidate_notes_node() - NEW (with re-ranking)
└── tests/
    ├── mock_serper.json            # fixture
    └── test_agent.py               # Needs significant updates for new flow
```

---

### 🔑 Environment Variables

```
SERPER_API_KEY=...        # required for web search node
OPENAI_API_KEY=...        # required for LLMs (clarifier, reasoner, summarizer, synthesizer) & embeddings
RAG_DOC_PATH=./my_docs    # optional, currently unused by main loop
```

---

### 🚀 Agent Flow (LangGraph in agent/__init__.py) - UPDATED

1.  **`main.py`:** Prompts user, gets verbosity level, calls `agent.run_agent(question, verbosity_level)`.
2.  **`agent.run_agent()`:**
    *   Initializes the `AgentState` TypedDict (`agent/state.py`) including new fields like `session_vector_store`, `notes`, `current_iteration`, etc.
    *   Invokes the compiled LangGraph application (`app`) with the initial state.
3.  **LangGraph Execution (`app`):**
    *   **Entry Point:** `clarify_node` (`agent/nodes/clarifier.py`) - Refines question and generates `plan_outline`.
    *   **Edge:** `clarify_node` -> `reason_node`.
    *   **Node:** `reason_node` (`agent/nodes/reasoner.py`) - The core decision loop. Uses an LLM to analyze state (question, outline, notes, iteration) and decides the `next_action` (SEARCH, FETCH, RETRIEVE_CHUNKS, CONSOLIDATE, STOP). Sets `current_query` or `url_to_fetch` if needed. Increments `current_iteration`.
    *   **Conditional Edges from `reason_node`:** Routes to the node corresponding to `next_action`.
        *   `-> search_node` (`agent/nodes/search.py`): Executes web search using `serper_search` based on `current_query`. Updates `search_results`. -> `reason_node`.
        *   `-> fetch_node` (`agent/nodes/fetch.py`): Fetches content from `url_to_fetch` using `fetch_url` tool. Updates `fetched_docs`. -> `chunk_and_embed_node`.
        *   `-> retrieve_relevant_chunks_node` (`agent/nodes/retrieve.py`): Queries `session_vector_store` based on `current_query`. Updates `retrieved_chunks`. -> `summarize_chunks_node`.
        *   `-> consolidate_notes_node` (`agent/nodes/consolidate.py`): If reasoner decides CONSOLIDATE or STOP. Re-ranks `notes` using cross-encoder. Updates `combined_context` with curated notes. -> `synthesize_node`.
    *   **Node:** `chunk_and_embed_node` (`agent/nodes/chunk_embed.py`): Takes `fetched_docs`, chunks/embeds content, adds to `session_vector_store`. Clears `fetched_docs`. -> `reason_node`.
    *   **Node:** `summarize_chunks_node` (`agent/nodes/summarize.py`): Takes `retrieved_chunks`, uses small LLM to generate a note with detailed embedded citations. Appends to `notes`. Clears `retrieved_chunks`. -> `reason_node`.
    *   **Node:** `synthesize_node` (`agent/nodes/synthesizer.py`): Takes `combined_context` (curated notes), generates final answer using LLM, preserving detailed citations. Performs post-processing to create numbered reference list. Updates `final_answer`. -> `END`.
    *   **Error Handling:** Any node can route to `error_handler` on failure. -> `END`.
4.  **`agent.run_agent()`:** Extracts `final_answer` from the final state. (Source URLs are now embedded in the answer's reference list).
5.  **`main.py`:** Prints the final answer.

---

### 🛠 Agent Implementation Rules

*   All agent logic implemented as LangGraph nodes in `agent/nodes/` or tools in `agent/tools/`.
*   No license file (private/internal use only).
*   If API keys are missing, script must fail gracefully with clear message.
*   All functions must include docstrings specifying I/O expectations.
*   Configuration managed via `config.yaml` (behavior, models, prompts, thresholds) and `.env` (secrets). Shared utilities (`agent/utils.py`) handle LLM/embedding initialization and logging.
*   Output verbosity controlled by `--quiet`, default, and `--verbose`. Source display is handled via post-processing in the synthesizer.

---

### 🧪 Tests (pytest)

*   `test_agent.py` needs significant updates to mock the new nodes and graph flow.
*   Tests must pass with no API keys (mocked responses only).
*   RAG module tests (if kept/updated) should skip gracefully if no `RAG_DOC_PATH` is available.

---

### 📘 README Instructions

1.  **Project Overview**: Update to describe the deep research loop.
2.  **Quickstart**: Update dependencies (`requests-html`, `lxml`, `sentence-transformers`).
3.  **How It Works**: Update diagram + explanation for the new graph flow.
4.  **Configuration**: Explain `config.yaml` including new sections (`embedding`, `summarizer`, `retriever`, `consolidator`).
5.  **Customize It**: Explain modifying nodes, prompts in config.
6.  **RAG Setup**: Mention RAG code exists but is not currently used in the main loop.
7.  **Verbosity Modes**: Explain `--quiet`, default, and `--verbose`.
8.  **Future Ideas**: Add RAG as a retrieval option, improve content extraction/cleaning, FastAPI, MCP.

---

### 🔌 Extension Hooks

*   Integrate the existing RAG (`agent/rag.py`, `agent/rag_utils/`) as an alternative retrieval source decided by the `reason_node`.
*   Improve HTML cleaning in `fetch_url` tool (e.g., using `trafilatura`).
*   Wrap `main.py` into a FastAPI service.
*   MCP endpoint wrapper.

---

### ✅ Success Definition (Updated)

*   `python main.py` must run the deep research loop (fetch, chunk, embed, retrieve, summarize, consolidate, synthesize).
*   The agent must produce answers with formatted citations based on fetched web content.
*   `pytest` must pass with offline mock (tests need update).
*   Users should be able to modify prompts/models for different nodes via `config.yaml`.

---