Thought for a couple of seconds


### ✅ Deep-Research-Agent — To-Do Checklist

**Use this list directly in issues, PR checklists, or a project board. Mark each box when complete.**

---

#### ✅ Chunk 0 – Repo Bootstrap

* ✅ `git init` and create directory tree per plan
* ✅ Add `.env.example` with placeholder keys & comments
* ✅ Create empty `requirements.txt`
* ✅ Initial commit: **“Bootstrap repo structure”**

---

#### ✅ Chunk 1 – Core Runtime Skeleton

* ✅ Create `agent/` package with empty module stubs + docstrings
* ✅ Implement `main.py` CLI shell (`input()` prompt, `--verbose` flag stub)
* ✅ Add minimal deps to `requirements.txt` (`python-dotenv`, `rich`, `pytest`)
* ✅ Commit: **“Core skeleton with CLI shell”**

---

#### ✅ Chunk 2 – Serper Search Integration

* ✅ Add `requests` to requirements
* ✅ Implement `search.serper_search()` (env-key check, REST call, list\[dict] return)
* ✅ Graceful error if `SERPER_API_KEY` missing
* ✅ Commit: **“Working Serper search module”**

---


#### ✅ Chunk 3 – RAG Skeleton (Langchain Implementation)

* ✅ Add `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured` to requirements
* ✅ `rag.py`:
  * ✅ Detect `RAG_DOC_PATH`; skip gracefully if absent.
  * ✅ Load/create Chroma DB using Langchain (`Chroma`, `OpenAIEmbeddings`) under `.rag_store/`.
  * ✅ Implement document loading (`DirectoryLoader`, `TextLoader`, `UnstructuredMarkdownLoader`).
  * ✅ Implement link following logic (using `rag_utils.ingestion`).
  * ✅ Implement semantic chunking (`SemanticChunker`).
  * ✅ `query_vector_store()` returns `(context, source_paths)` using Langchain retriever.
  * ✅ Error message if `OPENAI_API_KEY` missing.
* ✅ Create `agent/rag_utils/ingestion.py` with link helpers.
* ✅ Commit: **“Refactor RAG to use Langchain Indexing API with link following”**

---
#### ✅ Chunk 4 – Reasoning + Synthesis

* ✅ `reasoner.reason_over_sources()` → merge snippets (search + rag)
* ✅ `synthesizer.synthesize_answer()`:

  * ✅ OpenAI call if key present, else fallback echo
  * ✅ Support verbose token count output
* ✅ Commit: **“Initial reasoning & synthesis”**

---

#### ✅ Chunk 5 – Planner & Clarifier

* ✅ `clarifier.clarify_question()` (identity or OpenAI re-ask)
* ✅ `planner.plan_steps()` rule: always `"search"`; add `"rag"` if docs exist
* ✅ Commit: **“Simple planner + clarifier defaults”**

---

#### ✅ Chunk 6 – CLI Wiring & Verbose Flag

* ✅ Wire full pipeline in `agent.run_agent()`
* ✅ Propagate `--verbose` flag to all modules
* ✅ Add friendly exception handling for missing keys / HTTP errors
* ✅ Commit: **“Agent flow end-to-end”**

---

#### ✅ Chunk 7 – Local Tests

* ✅ Create `mock_serper.json` fixture
* ✅ `test_agent.py` mocks search, validates answer string
* ✅ Skip RAG tests if no corpus
* ✅ Commit: **“Offline pytest coverage”**

---

#### ✅ Chunk 8 – README & Docs

* ✅ Populate all seven README sections (overview, quick-start, etc.)
* ✅ Include ASCII or image diagram of agent flow
* ✅ Commit: **“README v1”**

---

#### ✅ Chunk 9 – Polish Pass

* ✅ Pin package versions in `requirements.txt`
* ✅ Verify `.env.example` keys & comments
* ✅ Refine log styles; ensure verbose works with `rich` if present
* ✅ Tag release `v0.1.0`
* ✅ Commit: **“Polish & version bump”**

---

**Done?** The repo should:

* run `python main.py` with real Serper search,
* support RAG if user supplies docs + key,
* pass `pytest` offline,
* and let users tweak any single module in < 10 minutes.
---

#### ✅ Post-v0.1.0 Fixes & Enhancements

* ✅ Fixed SSL certificate verification errors on macOS (`SSLError`).
* ✅ Corrected `rich.Panel` printing in `main.py` for non-verbose modes.
* ✅ Adjusted synthesizer prompt for more detailed answers.
* ✅ Implemented `config.yaml` for agent behavior configuration (`PyYAML` added).
* ✅ Refactored synthesizer and search modules to use `config.yaml`.
* ✅ Implemented verbosity levels (`--quiet`, default, `--verbose`) in `main.py` and `agent/__init__.py`.
* ✅ Updated `README.md` and Memory Bank files to reflect recent changes.
* ✅ Implemented automatic RAG corpus embedding in `agent/rag.py` (processes `.txt`/`.md` files from `RAG_DOC_PATH` on init if DB is empty).
* ✅ Added RAG link following (`[[WikiLinks]]`, `[Markdown](link.md)`) up to configurable depth.
* ✅ Added display of RAG source documents to `main.py` output.
* ✅ Refactored RAG implementation to use Langchain Indexing API (`DirectoryLoader`, `OpenAIEmbeddings`, `Chroma`).
* ✅ Addressed Langchain/Chroma deprecation warning (`langchain-chroma`).
* ✅ Added `unstructured` dependency for Markdown loading.
* ✅ Switched RAG text splitting from `RecursiveCharacterTextSplitter` to `SemanticChunker`.
* ✅ Restored RAG link following logic after Langchain refactor.
* ✅ Added RAG external web link following (configurable via `config.yaml`).