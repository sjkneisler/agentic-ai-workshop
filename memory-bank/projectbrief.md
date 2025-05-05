## 🧠 Deep Research Agent – Demo Repo Plan (v1.1 Final)

This plan is for an AI coding agent (without autonomous web access) to bootstrap and maintain a public-facing repository implementing a recursive research agent. It combines symbolic reasoning structure with runnable modular code, designed to be extended incrementally.

---

### 🎯 Purpose

Create a runnable Python project demonstrating a recursive research agent pipeline:

* Interactive Clarifier → Planner → Search → (Optional RAG) → Reason → Synthesize
* Designed to run in CLI with Serper search and optional Chroma-based RAG
* Includes an interactive clarification step using LangChain components and terminal input.
* Clear modularity for agents, extendability with LangGraph or MCP
* Low barrier to entry: one script, clearly segmented modules, `.env` driven config

---

### 📂 Repo Layout

```
/
├── README.md
├── requirements.txt                 # Python ≥3.10, includes langgraph
├── .env.example                     # API Keys, RAG Path
├── config.yaml                      # Agent behavior config (models, prompts, etc.)
├── main.py                          # CLI entrypoint
├── agent/
│   ├── __init__.py                 # Defines LangGraph graph, imports nodes
│   ├── state.py                    # Defines AgentState TypedDict - NEW
│   ├── utils.py                    # Shared utilities (logging, LLM init, etc.) - NEW
│   ├── config.py                   # Config loader
│   ├── clarifier.py                # clarify_question(), clarify_node()
│   ├── planner.py                  # plan_steps(), plan_node()
│   ├── search.py                   # serper_search(), search_node()
│   ├── rag.py                      # RAG interface (imports from rag_utils)
│   ├── rag_utils/                  # RAG utilities
│   │   ├── __init__.py
│   │   ├── ingestion.py            # Link parsing/resolution
│   │   ├── rag_initializer.py      # RAG setup/state
│   │   └── rag_query.py            # query_vector_store(), rag_node() - UPDATED
│   ├── reasoner.py                 # reason_over_sources(), reason_node()
│   └── synthesizer.py              # synthesize_answer(), synthesize_node()
└── tests/
    ├── mock_serper.json            # fixture
    └── test_agent.py               # Needs updates for LangGraph
```

---

### 🔑 Environment Variables

```
SERPER_API_KEY=...        # required for real search
OPENAI_API_KEY=...        # required for RAG and/or LLM-based clarification
RAG_DOC_PATH=./my_docs    # optional user-supplied local document directory
```

---

### 🚀 Agent Flow (LangGraph in agent/__init__.py)

1.  **`main.py`:** Prompts user, gets verbosity level, calls `agent.run_agent(question, verbosity_level)`.
2.  **`agent.run_agent()`:**
    *   Initializes the `AgentState` TypedDict (`agent/state.py`).
    *   Invokes the compiled LangGraph application (`app`) with the initial state.
3.  **LangGraph Execution (`app`):**
    *   **Entry Point:** `clarify_node` (`agent/clarifier.py`) - Uses LangChain (via `agent/utils.py`) and potentially user interaction to refine the question. Updates `clarified_question` in state.
    *   **Edge:** `clarify_node` -> `plan_node`.
    *   **Node:** `plan_node` (`agent/planner.py`) - Determines steps (e.g., `["search", "rag"]`). Updates `planned_steps` in state.
    *   **Conditional Edge:** Based on `planned_steps`:
        *   If "search": -> `search_node`.
        *   If only "rag": -> `rag_node`.
        *   If neither: -> `reason_node`.
        *   If error: -> `error_handler`.
    *   **Node:** `search_node` (`agent/search.py`) - Performs Serper search. Updates `search_results` and `web_source_urls` in state.
    *   **Conditional Edge:** After `search_node`:
        *   If "rag" in `planned_steps`: -> `rag_node`.
        *   Else: -> `reason_node`.
        *   If error: -> `error_handler`.
    *   **Node:** `rag_node` (`agent/rag_utils/rag_query.py`) - Performs RAG query. Updates `rag_context` and `rag_source_paths` in state.
    *   **Conditional Edge:** After `rag_node`: -> `reason_node` (or `error_handler` if error).
    *   **Node:** `reason_node` (`agent/reasoner.py`) - Combines search/RAG results. Updates `combined_context` in state.
    *   **Conditional Edge:** After `reason_node`: -> `synthesize_node` (or `error_handler` if error).
    *   **Node:** `synthesize_node` (`agent/synthesizer.py`) - Generates final answer using LLM (via `agent/utils.py`). Updates `final_answer` in state.
    *   **Conditional Edge:** After `synthesize_node`: -> `END` (or `error_handler` if error).
    *   **Node:** `error_handler` - Catches errors from nodes, sets error message in `final_answer`. -> `END`.
4.  **`agent.run_agent()`:** Extracts `final_answer`, `web_source_urls`, `rag_source_paths` from the final state returned by the graph invocation.
5.  **`main.py`:** Prints the final answer and sources based on the verbosity level.

---

### 🛠 Agent Implementation Rules

* All agent modules are standalone, with one clear job
* No license file (private/internal use only)
* If API keys are missing, script must fail gracefully with clear message
* All functions must include docstrings specifying I/O expectations
* Configuration primarily managed via `config.yaml` (behavior) and `.env` (secrets). Shared utilities (`agent/utils.py`) handle LLM initialization and logging based on config/env.
* Output verbosity controlled by `--quiet` (minimal), default (answer + sources), and `--verbose` (node execution logs + sources).

---

### 🧪 Tests (pytest)

* `test_agent.py` must include at least one test with `mock_serper.json`
* Test must pass with no API keys (mocked responses only)
* RAG module tests should skip gracefully if no `RAG_DOC_PATH` is available

---

### 📘 README Instructions

1. **Project Overview**

   > A small, recursive research agent that plans, searches, and synthesizes answers using LLMs.
2. **Quickstart**

```bash
git clone https://github.com/youruser/deep-research-agent.git
cd deep-research-agent
pip install -r requirements.txt
cp .env.example .env   # Fill in your SERPER and optionally OPENAI key
python main.py
```

3. **How It Works**: step-by-step diagram + explanation
4. **Configuration**: Explain `config.yaml` for tuning behavior - NEW
5. **Customize It**: Explain when to use `config.yaml` vs. editing Python code
6. **RAG Setup**: drop documents into `RAG_DOC_PATH` and rerun
7. **Verbosity Modes**: Explain `--quiet`, default, and `--verbose` - NEW
8. **Future Ideas**: LangGraph, FastAPI, MCP endpoints

---

### 🔌 Extension Hooks

* Plug `search.py` into other web APIs as desired
* Wrap `main.py` into a FastAPI service for web UI
* Convert the agent steps to LangGraph nodes with dynamic state edge control - **DONE**
* MCP endpoint wrapper for use in Cursor or other toolchains

---

### ✅ Success Definition

* `python main.py` must run a real Serper-based research loop
* `pytest` must pass with offline mock
* RAG activates if user supplies docs and `OPENAI_API_KEY`
* Users should be able to modify one module and see the agent change behavior in <10 minutes

---