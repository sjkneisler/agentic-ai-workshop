Below is a **two-tier implementation roadmap** reflecting the refactored agent architecture:

*Tier 1* = discrete “work chunks” the coding agent can tackle sequentially.
*Tier 2* = fine-grained steps inside each chunk.

---

## 📊 Tier 1 — Work Chunks (macro tasks) - REVISED

| Chunk # | Deliverable                     | Purpose                                                                                                | Status |
| ------- | ------------------------------- | ------------------------------------------------------------------------------------------------------ | ------ |
| **0**   | *Repo Bootstrap*                | Git repo initialized with layout skeleton, config, and minimal tooling.                                | ✅     |
| **1**   | *Core Runtime Skeleton*         | `main.py` CLI shell + `agent/` package with module stubs & initial `utils.py`, `state.py`.             | ✅     |
| **2**   | *Serper Search Functionality*   | Working `search.py` (`serper_search`) that calls Serper, env-driven. (Node removed)                    | ✅     |
| **3**   | *RAG Functionality (Langchain)* | `rag_utils` (`initializer`, `query`) using Langchain. `rag.py` interface. (Node removed)               | ✅     |
| **4**   | *Synthesis Module*              | Implement `synthesizer.py` (`synthesize_node`).                                                        | ✅     |
| **5**   | *Clarifier Module*              | Implement `clarifier.py` (`clarify_node`) including outline generation.                                | ✅     |
| **6**   | *Reasoner Agent Module*         | Implement `reasoner.py` (`reason_node`) with iterative tool-using agent (Search/RAG).                  | ✅     |
| **7**   | *LangGraph Wiring*              | Define & compile `StateGraph` in `agent/__init__.py`, connecting `clarify`->`reason`->`synthesize`. | ✅     |
| **8**   | *Local Tests*                   | `pytest` with mocks (needs significant update for new flow & reasoner).                                | ⏳     |
| **9**   | *README & Docs*                 | Populate README reflecting new architecture.                                                           | ⏳     |
| **10**  | *Polish Pass*                   | Verify `.env.example`, `config.yaml`, print-styles, error messages, requirements.                      | ⏳     |

---

## 🔍 Tier 2 — Detailed Steps per Chunk - REVISED

### **Chunk 0 – Repo Bootstrap** (✅)

1.  `git init`.
2.  Create top-level tree.
3.  Add `.env.example`.
4.  Create empty `requirements.txt`.
5.  Commit: “Bootstrap repo structure.”

### **Chunk 1 – Core Runtime Skeleton** (✅)

1.  Create `agent/utils.py` (logging).
2.  Create `agent/state.py` (`AgentState`).
3.  `agent/__init__.py` → `run_agent()` stub.
4.  Add module stubs (`clarifier.py`, `reasoner.py`, `synthesizer.py`, `search.py`, `rag.py`, `rag_utils/*`).
5.  `main.py` CLI shell.
6.  Update `requirements.txt` (essentials: `python-dotenv`, `rich`, `pytest`, `PyYAML`, `langgraph`, `langchain-core`).
7.  Commit: “Core skeleton with LangGraph setup, state, utils.”

### **Chunk 2 – Serper Search Functionality** (✅)

1.  Add `requests`, `certifi` to requirements.
2.  Implement `serper_search(query, n=None, verbose=False)` in `search.py`.
3.  Handle `SERPER_API_KEY`.
4.  Commit: “Working Serper search function.”

### **Chunk 3 – RAG Functionality (Langchain Implementation)** (✅)

1.  Add `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured`, `beautifulsoup4` to requirements.
2.  Implement `agent/rag_utils/rag_initializer.py` (`initialize_rag`, indexing logic).
3.  Implement `agent/rag_utils/rag_query.py` (`query_vector_store`, retrieval logic).
4.  Implement `agent/rag_utils/ingestion.py` (link helpers).
5.  Update `agent/rag.py` interface.
6.  Commit: “Implement RAG logic using Langchain in rag_utils.”

### **Chunk 4 – Synthesis Module** (✅)

1.  Implement `synthesize_answer()` in `synthesizer.py` using `utils.initialize_llm`.
2.  Implement `synthesize_node()` wrapper.
3.  Commit: “Implement synthesis module with LangGraph node.”

### **Chunk 5 – Clarifier Module** (✅)

1.  Implement `clarify_question()` in `clarifier.py` using LangChain for check, user interaction, and refinement + outline generation.
2.  Add `langchain-openai`, `pydantic` (v1) to requirements.
3.  Implement `clarify_node()` wrapper.
4.  Commit: “Implement clarifier module with outline generation and LangGraph node.”

### **Chunk 6 – Reasoner Agent Module** (✅)

1.  Add `langchain-agents` (or ensure core includes necessary agent parts) to requirements.
2.  In `reasoner.py`:
    *   Define `@tool` wrappers for `serper_search` and `query_vector_store`.
    *   Implement `reason_node()`:
        *   Initialize agent LLM (`utils.initialize_llm`).
        *   Define tools list (conditionally include RAG tool).
        *   Define `ChatPromptTemplate` for the tool-using agent (including question, outline, tool info, instructions).
        *   Create agent (e.g., `create_openai_tools_agent`).
        *   Create `AgentExecutor`, passing agent, tools, verbosity, and `max_iterations` from config.
        *   Invoke `agent_executor` with correctly formatted input dictionary.
        *   Return final context in state.
3.  Add `reasoner` section to `config.yaml` defaults and `agent/config.py`.
4.  Commit: “Implement iterative Reasoner agent with Search/RAG tools.”

### **Chunk 7 – LangGraph Wiring** (✅)

1.  In `agent/__init__.py`:
    *   Remove imports for `plan_node`, `search_node`, `rag_node`.
    *   Remove corresponding `add_node` calls.
    *   Update graph edges: `clarify_node` -> `reason_node` -> `synthesize_node`.
    *   Remove old conditional edge logic.
2.  Update `agent.run_agent()` initial state (`plan_outline`).
3.  Delete `agent/planner.py`.
4.  Commit: “Wire LangGraph for new Clarify->Reason->Synthesize flow.”

### **Chunk 8 – Local Tests** (⏳)

1.  Update `test_agent.py`:
    *   Mock `clarify_node`, `reason_node`, `synthesize_node` or test graph invocation.
    *   Focus tests on individual tool functions (`serper_search`, `query_vector_store`) if possible.
    *   Testing the full `reason_node` agent loop might require more complex mocking.
2.  Commit: “Update pytest coverage for new architecture (initial).”

### **Chunk 9 – README & Docs** (⏳)

1.  Update README sections (How it Works, Config, etc.).
2.  Update Memory Bank files (this process).
3.  Commit: “Update documentation for Reasoner Agent refactor.”

### **Chunk 10 – Polish Pass** (⏳)

1.  Pin package versions in `requirements.txt`.
2.  Validate `.env.example` and `config.yaml`.
3.  Review print styles and error messages.
4.  Address TODOs (e.g., source tracking in reasoner).
5.  Commit: “Final polish and documentation update.”

---

### 🏁 Handoff Instructions for Coding Agent

*   Work through remaining chunks (Tests, Docs, Polish).
*   After each commit, run `python main.py` (with mocks/keys) and `pytest`.
*   Do **not** introduce new dependencies unless specified.
*   Keep logs concise unless `--verbose`.
*   Ask for clarification only if blocking specification gaps remain.

---