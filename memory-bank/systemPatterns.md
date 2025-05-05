Thought for a couple of seconds


Below is a **two-tier implementation roadmap**:

*Tier 1* = discrete “work chunks” the coding agent can tackle sequentially (or in short parallel bursts).
*Tier 2* = fine-grained steps inside each chunk, with tips and guard-rails so the agent stays on-track without external search.

---

## 📊 Tier 1 — Work Chunks (macro tasks)

| Chunk # | Deliverable                     | Purpose                                                                                      |
| ------- | ------------------------------- | -------------------------------------------------------------------------------------------- |
| **0**   | *Repo Bootstrap*                | Git repo initialized with layout skeleton, config, and minimal tooling.                      |
| **1**   | *Core Runtime Skeleton*         | `main.py` CLI shell + `agent/` package with empty module stubs & docstrings.                 |
| **2**   | *Serper Search Integration*     | Working `search.py` that calls Serper, env-driven.                                           |
| **3**   | *RAG Skeleton (Langchain)*      | `rag.py` using Langchain (Loaders, Splitter, Embeddings, Chroma) to load/query corpus.       |
| **4**   | *Reasoning + Synthesis Modules* | Implement `reasoner.py` and `synthesizer.py` (single-pass, concise default / verbose trace). |
| **5**   | *Planner & Clarifier*           | Simple rule-based planner + optional clarifier prompt.                                       |
| **6**   | *CLI Wiring & Verbose Flag*     | Connect modules in `main.py`; add `--verbose` option; integrate error handling.              |
| **7**   | *Local Tests*                   | `pytest` with mocked Serper fixture & RAG skip logic.                                        |
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

1. `agent/__init__.py` → expose high-level `run_agent(question, verbosity_level)` stub (returns answer, urls).
2. In each empty module (`clarifier.py`, `planner.py`, etc.) add:

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
   4. Update `requirements.txt` with minimum essentials: `python-dotenv`, `rich` (for color logs), `pytest`, `PyYAML`.
5. Commit: “Core skeleton with CLI shell.”

### **Chunk 2 – Serper Search Integration**

1. Add `requests` to requirements.
2. Implement `serper_search(query, n=None, verbose=False)`:

   * Read `SERPER_API_KEY` via `dotenv` or `os.getenv`.
   * If missing → `RuntimeError` with clear msg.
   * Use `n` if provided, otherwise get `num_results` from `config.yaml` via `agent/config.py`.
   * Build POST to `https://serpapi.serper.dev/search`.
   * Return list of dicts (`title`, `snippet`, `url`).
3. Add docstring with API reference.
4. Commit: “Working Serper search module.”

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
   * Implement `query_vector_store(query, n_results, verbose)`:
     * Use `is_rag_enabled()` and `get_vector_store()` from `rag_initializer`.
     * **Retrieval Logic:**
        * Perform initial semantic search using the vector store retriever.
        * **(Optional) Internal Chunk Traversal:** If enabled, use `internal_linked_paths_str` metadata, deserialize, perform filtered searches, collect linked chunks.
        * **(Optional) External Web Fetching:** If enabled, extract web links from all collected chunks, fetch content using `requests`/`BeautifulSoup`.
        * Combine context from all sources (initial chunks, linked chunks, web pages).
        * Extract and return unique source paths/URLs.
4. Create `agent/rag_utils/ingestion.py` (if not already present) with `extract_links`, `is_web_link`, `resolve_link`.
5. Update `agent/rag.py` to be an interface:
   * Import `initialize_rag`, `is_rag_enabled` from `agent.rag_utils.rag_initializer`.
   * Import `query_vector_store` from `agent.rag_utils.rag_query`.
   * Expose these functions using `__all__`.
6. Commit: “Refactor RAG logic into rag_utils initializer and query modules.”

### **Chunk 4 – Reasoning + Synthesis**

1. `reasoner.py`: simple concatenation of snippets + optional RAG text into “context” string.
2. `synthesizer.py`:

   * Single OpenAI call (model, prompt, temp, max_tokens from `config.yaml` via `agent/config.py` unless key missing → fallback to echo).
   * If no key: return formatted bullet list of sources as placeholder.
3. Provide `synthesize_answer(question, context, verbose=False)`; if verbose print token counts.
4. Commit: “Initial reasoning & synthesis.”

### **Chunk 5 – Planner & Clarifier**

1. `clarifier.py` → Implement interactive LangChain clarification:
   * Check for `OPENAI_API_KEY`. Skip if missing or LangChain components fail to initialize.
   * Use a LangChain chain (`ChatOpenAI`, `ChatPromptTemplate`, `JsonOutputParser` with Pydantic model) to check if the question needs clarification and get specific questions to ask (model/temp from `config.yaml`).
   * If clarification needed:
       * Loop through questions, prompt user via `input()` in the terminal.
       * Collect user answers.
       * Use another LangChain chain (`ChatOpenAI`, `ChatPromptTemplate`, `StrOutputParser`) with the original question + Q&A to synthesize a refined question (model/temp from `config.yaml`).
   * Return the refined question, or the original if clarification skipped/failed/cancelled.
   * Add `langchain-openai`, `langchain-core` to requirements.
2. `planner.py`:
   * Rule: always `"search"`; add `"rag"` if `RAG_DOC_PATH` exists and is a directory.
   * Use the (potentially refined) question from the clarifier (though the content isn't used for planning *yet*).
   * Return list of steps.
3. Commit: “Implement interactive LangChain clarifier and simple planner.”

### **Chunk 6 – CLI Wiring & Verbose Flag**

1. Wire modules in `agent.run_agent(question, verbosity_level)`.
2. Propagate `is_verbose` flag (derived from `verbosity_level`) to each module call.
3. `run_agent` returns `(answer, urls)`.
4. `main.py` handles printing based on `verbosity_level`.
5. Exit nicely on exceptions (missing keys, HTTP errors).
4. Commit: “Agent flow end-to-end.”

### **Chunk 7 – Local Tests**

1. Fixture `mock_serper.json` with 2 fake results.
2. In `test_agent.py`:

   * Monkeypatch `search.serper_search` to return mock.
   * Pass dummy question → ensure final answer string present.
3. Skip RAG test if no docs folder.
4. Commit: “Offline pytest coverage.”

### **Chunk 8 – README & Docs**

1. Populate sections per plan.
2. Include ASCII diagram or link to image for agent flow.
3. Commit: “README v1.”

### **Chunk 9 – Polish Pass**

1. Pin package versions (`requests>=2.31`, `chromadb>=0.4.14`, etc.).
2. Validate `.env.example` and create initial `config.yaml`.
3. Ensure `--quiet`, default, and `--verbose` modes produce the correct output levels.
4. Tag release `v0.1.0`. (Note: This chunk description is historical; config/verbosity added post-v0.1.0).
5. Commit: “Polish & version bump.”

---

### 🏁 Handoff Instructions for Coding Agent

* Work through chunks in order.
* After each commit, run `python main.py` (with mocks/keys) and `pytest`.
* Do **not** introduce new dependencies unless specified.
* Keep logs concise unless `--verbose`.
* Ask for clarification only if blocking specification gaps remain.

---

That breakdown should let your AI coding agent implement the repo confidently, chunk by chunk, without web search.