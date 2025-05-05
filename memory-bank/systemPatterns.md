Thought for a couple of seconds


Below is a **two-tier implementation roadmap**:

*Tier 1* = discrete “work chunks” the coding agent can tackle sequentially (or in short parallel bursts).
*Tier 2* = fine-grained steps inside each chunk, with tips and guard-rails so the agent stays on-track without external search.

---

## 📊 Tier 1 — Work Chunks (macro tasks)

| Chunk # | Deliverable                     | Purpose                                                                                      |
| ------- | ------------------------------- | -------------------------------------------------------------------------------------------- |
| **0**   | *Repo Bootstrap*                | Git repo initialized with layout skeleton, config, and minimal tooling.                      |
| **1**   | *Core Runtime Skeleton*         | `main.py` CLI shell + `agent/` package with module stubs & initial `utils.py`, `state.py`. |
| **2**   | *Serper Search Integration*     | Working `search.py` (`serper_search`, `search_node`) that calls Serper, env-driven.          |
| **3**   | *RAG Skeleton (Langchain)*      | `rag_utils` (`initializer`, `query` with `rag_node`) using Langchain. `rag.py` interface.    |
| **4**   | *Reasoning + Synthesis Modules* | Implement `reasoner.py` (`reason_node`) and `synthesizer.py` (`synthesize_node`).            |
| **5**   | *Planner & Clarifier*           | Implement `planner.py` (`plan_node`) and `clarifier.py` (`clarify_node`).                    |
| **6**   | *LangGraph Wiring*              | Define & compile `StateGraph` in `agent/__init__.py`, connecting nodes. `main.py` calls `run_agent`. |
| **7**   | *Local Tests*                   | `pytest` with mocked Serper fixture & RAG skip logic (needs update for LangGraph).           |
| **8**   | *README & Docs*                 | Populate README quick-start, how-it-works, customize, verbose, RAG setup.                    |
| **9**   | *Polish Pass*                   | Verify `.env.example`, print-styles, error messages, and requirements versions.              |

---

## 🔍 Tier 2 — Detailed Steps per Chunk

### **Chunk 0 – Repo Bootstrap**

1. `git init` (or assume fresh dir).
2. Create top-level tree exactly as in plan.
3. Add `.env.example` with placeholder keys + comments.
4. Create **empty** `requirements.txt` (to be filled later).
5. Commit: “Bootstrap repo structure.”

### **Chunk 1 – Core Runtime Skeleton**

1. Create `agent/utils.py` with initial logging setup (`print_verbose`, `RICH_AVAILABLE`, `Panel`).
2. Create `agent/state.py` with `AgentState` TypedDict definition.
3. `agent/__init__.py` → expose high-level `run_agent(question, verbosity_level)` stub. Import `AgentState`, `utils`.
4. In each logic module (`clarifier.py`, `planner.py`, etc.) add:

   ```python
   """Module purpose.

   TODO: implement.
   """
   def placeholder(*args, **kwargs):
       raise NotImplementedError
   ```
3. `main.py`:

   ```python
   import argparse, agent
   # parse --quiet/--verbose, prompt user, call agent.run_agent(), handle output based on verbosity
   ```
   4. Update `requirements.txt` with minimum essentials: `python-dotenv`, `rich`, `pytest`, `PyYAML`, `langgraph`, `langchain-core`.
5. Commit: “Core skeleton with LangGraph setup, state, utils.”

### **Chunk 2 – Serper Search Integration**

1. Add `requests` to requirements.
2. Implement `serper_search(query, n=None, verbose=False)` using `utils.print_verbose`.
3. Implement `search_node(state: AgentState)` wrapper using `serper_search`.

   * Read `SERPER_API_KEY` via `dotenv` or `os.getenv`.
   * If missing → `RuntimeError` with clear msg.
   * Use `n` if provided, otherwise get `num_results` from `config.yaml` via `agent/config.py`.
   * Build POST to `https://serpapi.serper.dev/search`.
   * Return list of dicts (`title`, `snippet`, `url`).
3. Add docstrings.
4. Commit: “Working Serper search module with LangGraph node.”

### **Chunk 3 – RAG Skeleton (Langchain Implementation)**

1. Add `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured`, `requests`, `beautifulsoup4` to requirements.
2. Create `agent/rag_utils/rag_initializer.py`:
   * Implement `initialize_rag()`:
     * Manage internal state (`_vector_store`, `_rag_initialized`, `_rag_enabled`).
     * Implement `is_rag_enabled()` and `get_vector_store()` helper functions.
     * Perform environment variable checks (`RAG_DOC_PATH`, `OPENAI_API_KEY`).
     * Initialize `OpenAIEmbeddings`.
     * Load or create the persistent Chroma store (`.rag_store/`).
     * **Indexing Logic (if creating store):**
        * Use `DirectoryLoader` with `TextLoader`/`UnstructuredMarkdownLoader` for initial load.
        * Implement internal document link-following loop (using helpers from `ingestion.py`) up to `rag_initial_link_follow_depth`.
        * Add internal link metadata (`internal_linked_paths_str`) to documents before chunking.
        * Use `SemanticChunker` to split documents.
        * Create store using `Chroma.from_documents(...)` and persist.
     * Update internal state based on success/failure.
3. Create `agent/rag_utils/rag_query.py`:
   * Implement `query_vector_store(query, n_results, verbose)` using `utils.print_verbose`:
     * Use `is_rag_enabled()` and `get_vector_store()` from `rag_initializer`.
     * **Retrieval Logic (as before):**
        * Perform initial semantic search using the vector store retriever.
        * **(Optional) Internal Chunk Traversal:** If enabled, use `internal_linked_paths_str` metadata, deserialize, perform filtered searches, collect linked chunks.
        * **(Optional) External Web Fetching:** If enabled, extract web links from all collected chunks, fetch content using `requests`/`BeautifulSoup`.
        * Combine context from all sources (initial chunks, linked chunks, web pages).
        * Extract and return unique source paths/URLs.
4. Implement `rag_node(state: AgentState)` wrapper using `query_vector_store`.
5. Create `agent/rag_utils/ingestion.py` (if not already present) with link helpers.
6. Update `agent/rag.py` to be an interface (imports `query_vector_store`, `is_rag_enabled`, `initialize_rag`).
7. Commit: “Refactor RAG logic into rag_utils with LangGraph node.”

### **Chunk 4 – Reasoning + Synthesis**

1. `reasoner.py`: Implement `reason_over_sources()` using `utils.print_verbose`. Implement `reason_node()` wrapper.
2. `synthesizer.py`: Implement `synthesize_answer()` using `utils.initialize_llm`, `utils.count_tokens`, `utils.print_verbose`. Implement `synthesize_node()` wrapper.

   * Single OpenAI call (model, prompt, temp, max_tokens from `config.yaml` via `agent/config.py` unless key missing → fallback to echo).
   * If no key: return formatted bullet list of sources as placeholder.
3. Provide `synthesize_answer(question, context, verbose=False)`; if verbose print token counts.
3. Commit: “Implement reasoning & synthesis modules with LangGraph nodes.”

### **Chunk 5 – Planner & Clarifier**

1. `clarifier.py` → Implement `clarify_question()` using `utils.initialize_llm`, `utils.print_verbose`:
   * Check for `OPENAI_API_KEY` via `initialize_llm`. Skip if missing/fails.
   * Use LangChain chains (`ChatPromptTemplate`, `JsonOutputParser`, `StrOutputParser`) with initialized LLMs to check clarification needs and refine question.
   * If clarification needed:
       * Loop through questions, prompt user via `input()` in the terminal.
       * Collect user answers.
       * Use another LangChain chain (`ChatOpenAI`, `ChatPromptTemplate`, `StrOutputParser`) with the original question + Q&A to synthesize a refined question (model/temp from `config.yaml`).
   * Return the refined question, or the original if clarification skipped/failed/cancelled.
   * Add `langchain-openai`, `langchain-core`, `pydantic` (v1 namespace used) to requirements.
   * Implement `clarify_node()` wrapper.
2. `planner.py`:
   * Implement `plan_steps()` using `utils.print_verbose`.
   * Implement `plan_node()` wrapper.
3. Commit: “Implement planner and clarifier modules with LangGraph nodes.”

### **Chunk 6 – LangGraph Wiring**

1. In `agent/__init__.py`:
   * Import `AgentState`, node functions, `StateGraph`, `END`, `utils.print_verbose`.
   * Define conditional edge logic (`should_execute_step`, `after_search_decision`, `after_rag_decision`).
   * Define `error_handler_node`.
   * Build `workflow = StateGraph(AgentState)`.
   * Add all imported nodes and the error handler node.
   * Define entry point and all edges (including conditional).
   * Compile the graph: `app = workflow.compile()`.
2. Update `agent.run_agent()`:
   * Prepare initial `AgentState`.
   * Invoke `app.invoke(initial_state)`.
   * Handle potential graph execution errors.
   * Extract results from final state.
   * Return `(answer, web_urls, rag_paths)`.
3. Update `main.py` to call the (now LangGraph-based) `agent.run_agent()`.
4. Commit: “Wire LangGraph agent flow in __init__.py.”

### **Chunk 7 – Local Tests**

1. Fixture `mock_serper.json` with 2 fake results.
2. In `test_agent.py`:

   * Update tests to potentially mock node functions or test the graph invocation with specific initial states. (Significant changes likely needed).
   * Pass dummy question → ensure final answer string present in final state.
3. Skip RAG test if no docs folder.
4. Commit: “Update pytest coverage for LangGraph structure (initial).”

### **Chunk 8 – README & Docs**

1. Populate sections per plan.
2. Include ASCII diagram or link to image for agent flow.
3. Commit: “README v1.”

### **Chunk 9 – Polish Pass**

1. Pin package versions (`requests>=2.31`, `chromadb>=0.4.14`, etc.).
2. Validate `.env.example` and create initial `config.yaml`.
3. Ensure `--quiet`, default, and `--verbose` modes produce the correct output levels via `utils.print_verbose` and `main.py` logic.
4. Update `README.md` to reflect LangGraph architecture and `utils.py`.
5. Commit: “Final polish and documentation update for LangGraph refactor.”

---

### 🏁 Handoff Instructions for Coding Agent

* Work through chunks in order.
* After each commit, run `python main.py` (with mocks/keys) and `pytest`.
* Do **not** introduce new dependencies unless specified.
* Keep logs concise unless `--verbose`.
* Ask for clarification only if blocking specification gaps remain.

---

That breakdown should let your AI coding agent implement the repo confidently, chunk by chunk, without web search.