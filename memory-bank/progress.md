### ✅ Deep-Research-Agent — To-Do Checklist

**Use this list directly in issues, PR checklists, or a project board. Mark each box when complete.**

---

#### ✅ Chunk 0 – Repo Bootstrap

*   ✅ `git init` and create directory tree per plan
*   ✅ Add `.env.example` with placeholder keys & comments
*   ✅ Create empty `requirements.txt`
*   ✅ Initial commit: **“Bootstrap repo structure”**

---

#### ✅ Chunk 1 – Core Runtime Skeleton

*   ✅ Create `agent/` package with empty module stubs + docstrings
*   ✅ Implement `main.py` CLI shell (`input()` prompt, `--verbose` flag stub)
*   ✅ Add minimal deps to `requirements.txt` (`python-dotenv`, `rich`, `pytest`)
*   ✅ Commit: **“Core skeleton with CLI shell”**

---

#### ✅ Chunk 2 – Serper Search Functionality

*   ✅ Add `requests` to requirements
*   ✅ Implement `search.serper_search()` (env-key check, REST call, list\[dict] return)
*   ✅ Graceful error if `SERPER_API_KEY` missing
*   ✅ Commit: **“Working Serper search function”**

---

#### ✅ Chunk 3 – RAG Functionality (Langchain Implementation)

*   ✅ Add `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured`, `beautifulsoup4` to requirements
*   ✅ Implement RAG logic in `agent/rag_utils/` (`initializer`, `query`, `ingestion`).
*   ✅ Update `agent/rag.py` interface.
*   ✅ Commit: **“Implement RAG logic using Langchain in rag_utils.”**

---

#### ✅ Chunk 4 – Synthesis Module

*   ✅ Implement `synthesizer.synthesize_answer()`
*   ✅ Implement `synthesize_node()` wrapper.
*   ✅ Commit: **“Implement synthesis module with LangGraph node.”**

---

#### ✅ Chunk 5 – Clarifier Module (with Outline)

*   ✅ Implement `clarifier.clarify_question()` (interactive check, refine + outline generation)
*   ✅ Add `langchain-openai`, `pydantic` (v1) to requirements.
*   ✅ Implement `clarify_node()` wrapper.
*   ✅ Commit: **“Implement clarifier module with outline generation and LangGraph node.”**

---

#### ✅ Chunk 6 – Reasoner Agent Module (Iterative Tool User)

*   ✅ Add `langchain-agents` (implicitly or explicitly) to requirements.
*   ✅ Refactor `reasoner.py`: Define `web_search` & `local_document_search` tools.
*   ✅ Implement `reason_node()` with `AgentExecutor` running `create_openai_tools_agent`.
*   ✅ Agent uses tools based on question/outline up to `max_iterations`.
*   ✅ Add `reasoner` config to `config.yaml` and `agent/config.py`.
*   ✅ Commit: **“Implement iterative Reasoner agent with Search/RAG tools.”**

---

#### ✅ Chunk 7 – LangGraph Wiring (Clarify->Reason->Synthesize)

*   ✅ Update `agent/__init__.py`: Remove planner/search/rag nodes & edges.
*   ✅ Connect `clarify_node` -> `reason_node` -> `synthesize_node`.
*   ✅ Update `agent/state.py` (`plan_outline`).
*   ✅ Delete `agent/planner.py`.
*   ✅ Commit: **“Wire LangGraph for new Clarify->Reason->Synthesize flow.”**

---

#### ⏳ Chunk 8 – Local Tests

*   ⏳ Update `test_agent.py` for new architecture (mocking reasoner agent?).

---

#### ⏳ Chunk 9 – README & Docs

*   ⏳ Update README sections (How it Works, Config).
*   ✅ Update Memory Bank files (this update).

---

#### ⏳ Chunk 10 – Polish Pass

*   ⏳ Pin package versions in `requirements.txt`.
*   ⏳ Validate `.env.example` and `config.yaml`.
*   ⏳ Review print styles and error messages.
*   ⏳ Address TODOs (e.g., source tracking in reasoner).

---

**Done?** The repo should:

*   run `python main.py` with the new iterative reasoner flow,
*   support RAG as a tool if user supplies docs + key,
*   pass `pytest` offline (tests need update),
*   and let users tweak config or modules.

---

#### ✅ Post-v0.1.0 Fixes & Enhancements (Consolidated into above chunks where applicable)

*(Previous detailed list omitted for brevity, covered by the revised chunks)*

---

#### ✅ LangGraph & Utilities Refactor (Consolidated into above chunks)

*(Previous detailed list omitted for brevity, covered by the revised chunks)*