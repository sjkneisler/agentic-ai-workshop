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
2. In `rag.py`:
   * Implement `_initialize_rag()`:
     * Check `RAG_DOC_PATH` and `OPENAI_API_KEY`.
     * Initialize `OpenAIEmbeddings`.
     * Check if persistent Chroma store exists at `.rag_store/`.
     * If exists: Load using `Chroma(persist_directory=..., embedding_function=...)`.
     * If not exists (Indexing):
        * Use `DirectoryLoader` with `TextLoader`/`UnstructuredMarkdownLoader` for initial load from `RAG_DOC_PATH`.
        * Implement internal document link-following loop (using helpers from `rag_utils`) up to `rag_initial_link_follow_depth` from config.
        * **NEW:** Before chunking, iterate through loaded docs, extract internal links, resolve target file paths.
        * **FIX:** Store the list of paths as a serialized string (`internal_linked_paths_str`, joined by `;;`) in metadata for Chroma compatibility.
        * Use `SemanticChunker` to split all collected local documents.
        * Create store using `Chroma.from_documents(..., persist_directory=...)`, ensuring metadata (including `internal_linked_paths_str`) is preserved on chunks.
   * Implement `query_vector_store(query)` (Retrieval):
     * Ensure RAG is initialized.
     * Perform initial semantic search: `retriever.invoke(query)` to get `initial_chunks`.
     * **NEW (Optional Internal Traversal):** If `rag_follow_internal_chunk_links` is true:
         * Perform breadth-first search starting from `initial_chunks`.
         * Use `internal_linked_paths_str` metadata on chunks, deserialize the string back into a list of target file paths.
         * For each target path, perform filtered similarity search: `vector_store.similarity_search(query, k=rag_internal_link_k, filter={'source': target_path})`.
         * Collect unique linked chunks up to `rag_internal_link_depth`.
     * **NEW (Optional External Fetching):** If `rag_follow_external_links` is true:
         * Extract all `http/https` links from the content of *all* collected chunks (initial + linked).
         * Fetch unique URLs using `requests`, parse with `BeautifulSoup`.
     * Combine context from local chunks, linked chunks, and fetched web content.
     * Extract and return unique source paths/URLs.
3. Create `agent/rag_utils/ingestion.py` with `extract_links`, `is_web_link`, `resolve_link`.
4. Commit: “Implement combined RAG: internal link metadata (serialized) indexing + retrieval-time chunk traversal & web fetching.”

### **Chunk 4 – Reasoning + Synthesis**

1. `reasoner.py`: simple concatenation of snippets + optional RAG text into “context” string.
2. `synthesizer.py`:

   * Single OpenAI call (model, prompt, temp, max_tokens from `config.yaml` via `agent/config.py` unless key missing → fallback to echo).
   * If no key: return formatted bullet list of sources as placeholder.
3. Provide `synthesize_answer(question, context, verbose=False)`; if verbose print token counts.
4. Commit: “Initial reasoning & synthesis.”

### **Chunk 5 – Planner & Clarifier**

1. `clarifier.py` → echo input or re-ask clarifying Q via OpenAI if key exists.
2. `planner.py`:

   * Rule: always `"search"`; add `"rag"` if docs exist.
   * Return list of steps.
3. Commit: “Simple planner + clarifier defaults.”

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