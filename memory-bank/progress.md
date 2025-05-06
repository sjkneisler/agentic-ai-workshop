### ✅ Deep-Research-Agent — To-Do Checklist (Deep Research Loop Version)

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

#### ✅ Chunk 2 – Serper Search Utility
*   ✅ Add `requests` to requirements
*   ✅ Implement `search.serper_search()` utility function
*   ✅ Graceful error if `SERPER_API_KEY` missing
*   ✅ Commit: **“Working Serper search function”**

---

#### ✅ Chunk 3 – RAG Functionality (Langchain Implementation)
*   ✅ Add `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured`, `beautifulsoup4` to requirements
*   ✅ Implement RAG logic in `agent/rag_utils/` (`initializer`, `query`, `ingestion`).
*   ✅ Update `agent/rag.py` interface.
*   ✅ Commit: **“Implement RAG logic using Langchain in rag_utils.”**
*   *Note: RAG components are currently unused by the main deep research loop.*

---

#### ✅ Chunk 4 – Initial Synthesis Module
*   ✅ Implement `synthesizer.synthesize_answer()`
*   ✅ Implement `synthesize_node()` wrapper.
*   ✅ Commit: **“Implement synthesis module with LangGraph node.”**

---

#### ✅ Chunk 5 – Initial Clarifier Module (with Outline)
*   ✅ Implement `clarifier.clarify_question()` (interactive check, refine + outline generation)
*   ✅ Add `langchain-openai`, `pydantic` (v1) to requirements.
*   ✅ Implement `clarify_node()` wrapper.
*   ✅ Commit: **“Implement clarifier module with outline generation and LangGraph node.”**

---

#### ✅ Chunk 6 – Initial Reasoner Agent Module (Iterative Tool User)
*   ✅ Add `langchain-agents` (implicitly or explicitly) to requirements.
*   ✅ Refactor `reasoner.py`: Define `web_search` & `local_document_search` tools.
*   ✅ Implement `reason_node()` with `AgentExecutor` running `create_openai_tools_agent`.
*   ✅ Agent uses tools based on question/outline up to `max_iterations`.
*   ✅ Add `reasoner` config to `config.yaml` and `agent/config.py`.
*   ✅ Commit: **“Implement iterative Reasoner agent with Search/RAG tools.”**
*   *Note: This iterative agent approach was superseded by the Deep Research Loop.*

---

#### ✅ Chunk 7 – Initial LangGraph Wiring (Clarify->Reason->Synthesize)
*   ✅ Update `agent/__init__.py`: Remove planner/search/rag nodes & edges.
*   ✅ Connect `clarify_node` -> `reason_node` -> `synthesize_node`.
*   ✅ Update `agent/state.py` (`plan_outline`).
*   ✅ Delete `agent/planner.py`.
*   ✅ Commit: **“Wire LangGraph for new Clarify->Reason->Synthesize flow.”**
*   *Note: This wiring was superseded by the Deep Research Loop.*

---

#### ✅ Chunk 8 – Deep Research Loop Implementation
*   ✅ Add dependencies (`requests-html`, `lxml[html_clean]`, `sentence-transformers`).
*   ✅ Create `fetch_url` tool (`agent/tools/fetch.py`).
*   ✅ Update `agent/state.py` with new fields.
*   ✅ Create new nodes (`search`, `fetch`, `chunk_embed`, `retrieve`, `summarize`, `consolidate`) in `agent/nodes/`.
*   ✅ Refactor `reasoner_node` (`agent/nodes/reasoner.py`) to be decision-maker.
*   ✅ Update `synthesizer_node` (`agent/nodes/synthesizer.py`) for citation handling.
*   ✅ Update `agent/config.py` with new component configs/getters.
*   ✅ Reorganize node files (`clarifier`, `reasoner`, `synthesizer`) into `agent/nodes/`.
*   ✅ Rewire graph in `agent/__init__.py` for the new loop.
*   ✅ Commit: **“Implement deep research loop architecture.”**
*   *Note: Significant debugging performed on state persistence (`seen_queries`, `seen_urls`, `query_for_retrieval`, `search_results`), graph routing (`Embed->Retrieve`), reasoner logic/prompting, and fetch tool error handling. Graph recursion limit made configurable.*

---

#### ⏳ Chunk 9 – Local Tests
*   ⏳ Update `test_agent.py` for new architecture (mocking new nodes, graph paths).

---

#### ⏳ Chunk 10 – README & Docs
*   ⏳ Update README sections (How it Works, Config) for deep research loop.
*   ✅ Update Memory Bank files (this update).

---

#### ⏳ Chunk 11 – Polish Pass
*   ⏳ Pin package versions in `requirements.txt`.
*   ⏳ Validate `.env.example` and `config.yaml`.
*   ⏳ Review print styles and error messages.
*   ⏳ Address TODOs.

---

#### ✅ Chunk 12 – Prompt Logging System
*   ✅ Add `prompt_logging` config to `config.yaml` and `agent/config.py`.
*   ✅ Create `log_prompt_data` utility in `agent/utils.py`.
*   ✅ Integrate logging into `clarifier`, `reasoner`, `summarize`, `synthesizer` nodes.
*   ✅ Fix associated bugs (`NameError` in `utils.py`, `AttributeError` in `clarifier.py`).
*   ✅ Commit: **"Implement prompt logging system for LLM interactions."**

---

#### ✅ Chunk 13 – OpenAI API Cost Tracking
*   ✅ Add `total_openai_cost` to `agent/state.py`.
*   ✅ Add `openai_pricing` section to `config.yaml`.
*   ✅ Update `agent/config.py` to load pricing and add getter.
*   ✅ Integrate cost calculation into `clarifier`, `reasoner`, `chunk_embed`, `summarize`, `synthesizer` nodes.
*   ✅ Update `agent/__init__.py` for `run_agent` to return total cost.
*   ✅ Update `main.py` to display estimated cost.
*   ✅ Commit: **"Implement OpenAI API cost tracking and display."**

---

**Done?** The repo should:

*   run `python main.py` with the new deep research loop flow,
*   produce answers with formatted citations based on fetched web content,
*   display an estimated cost for OpenAI API calls,
*   pass `pytest` offline (tests need update for cost tracking),
*   and let users tweak config or modules.

---