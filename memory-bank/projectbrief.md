## 🧠 Deep Research Agent – Demo Repo Plan (v1.2 - Reasoner Agent Refactor)

This plan is for an AI coding agent (without autonomous web access) to bootstrap and maintain a public-facing repository implementing a recursive research agent. It combines symbolic reasoning structure with runnable modular code, designed to be extended incrementally.

---

### 🎯 Purpose

Create a runnable Python project demonstrating a research agent pipeline:

*   **Interactive Clarifier:** Refines the user's question and generates a basic Markdown research outline.
*   **Iterative Reasoner:** Uses Search and RAG as tools to gather information based on the question and outline.
*   **Synthesizer:** Generates the final answer from the gathered context.
*   Designed to run in CLI with Serper search and optional Chroma-based RAG.
*   Includes an interactive clarification step using LangChain components and terminal input.
*   Clear modularity for agents, extendability with LangGraph or MCP.
*   Low barrier to entry: one script, clearly segmented modules, `.env` driven config.

---

### 📂 Repo Layout

```
/
├── README.md
├── requirements.txt                 # Python ≥3.10, includes langgraph, langchain-agents
├── .env.example                     # API Keys, RAG Path
├── config.yaml                      # Agent behavior config (models, prompts, reasoner iterations, etc.) - UPDATED
├── main.py                          # CLI entrypoint
├── agent/
│   ├── __init__.py                 # Defines LangGraph graph, imports nodes - UPDATED
│   ├── state.py                    # Defines AgentState TypedDict - UPDATED (plan_outline)
│   ├── utils.py                    # Shared utilities (logging, LLM init, etc.)
│   ├── config.py                   # Config loader - UPDATED (reasoner config)
│   ├── clarifier.py                # clarify_question(), clarify_node() - UPDATED (generates outline)
│   # ├── planner.py                # REMOVED
│   ├── search.py                   # serper_search() - Now used as a tool by Reasoner
│   ├── rag.py                      # RAG interface (imports from rag_utils)
│   ├── rag_utils/                  # RAG utilities
│   │   ├── __init__.py
│   │   ├── ingestion.py            # Link parsing/resolution
│   │   ├── rag_initializer.py      # RAG setup/state
│   │   └── rag_query.py            # query_vector_store() - Now used as a tool by Reasoner
│   ├── reasoner.py                 # Iterative tool-using agent, reason_node() - REFACTORED
│   └── synthesizer.py              # synthesize_answer(), synthesize_node()
└── tests/
    ├── mock_serper.json            # fixture
    └── test_agent.py               # Needs updates for LangGraph & new flow
```

---

### 🔑 Environment Variables

```
SERPER_API_KEY=...        # required for real search (used by Reasoner tool)
OPENAI_API_KEY=...        # required for RAG, LLM clarification, Reasoner agent, and Synthesis
RAG_DOC_PATH=./my_docs    # optional user-supplied local document directory
```

---

### 🚀 Agent Flow (LangGraph in agent/__init__.py) - UPDATED

1.  **`main.py`:** Prompts user, gets verbosity level, calls `agent.run_agent(question, verbosity_level)`.
2.  **`agent.run_agent()`:**
    *   Initializes the `AgentState` TypedDict (`agent/state.py`) including `plan_outline`.
    *   Invokes the compiled LangGraph application (`app`) with the initial state.
3.  **LangGraph Execution (`app`):**
    *   **Entry Point:** `clarify_node` (`agent/clarifier.py`) - Uses LangChain (via `agent/utils.py`) and potentially user interaction to refine the question and generate a Markdown `plan_outline`. Updates `clarified_question` and `plan_outline` in state.
    *   **Edge:** `clarify_node` -> `reason_node` (if no error).
    *   **Node:** `reason_node` (`agent/reasoner.py`) - Initializes and runs an iterative LangChain agent (e.g., OpenAI Tools Agent).
        *   The agent receives the `clarified_question` and `plan_outline`.
        *   It uses `web_search` and `local_document_search` (RAG) as tools.
        *   It iteratively calls tools based on the question/outline to gather information, using intermediate results (via `agent_scratchpad`).
        *   Continues up to `max_iterations` (from `config.yaml`).
        *   The agent's final output (synthesized context) updates `combined_context` in state.
    *   **Edge:** `reason_node` -> `synthesize_node` (if no error).
    *   **Node:** `synthesize_node` (`agent/synthesizer.py`) - Generates final answer using an LLM (via `agent/utils.py`) based on the `clarified_question` and the `combined_context` from the reasoner. Updates `final_answer` in state.
    *   **Edge:** `synthesize_node` -> `END` (if no error).
    *   **Node:** `error_handler` - Catches errors from nodes, sets error message in `final_answer`. -> `END`.
4.  **`agent.run_agent()`:** Extracts `final_answer`, `web_source_urls` (currently lost in reasoner refactor - TODO), `rag_source_paths` (currently lost - TODO) from the final state.
5.  **`main.py`:** Prints the final answer (and potentially sources later) based on the verbosity level.

---

### 🛠 Agent Implementation Rules

*   All agent modules are standalone, with one clear job (except Reasoner which now orchestrates tool use).
*   No license file (private/internal use only).
*   If API keys are missing, script must fail gracefully with clear message.
*   All functions must include docstrings specifying I/O expectations.
*   Configuration primarily managed via `config.yaml` (behavior, including reasoner iterations) and `.env` (secrets). Shared utilities (`agent/utils.py`) handle LLM initialization and logging.
*   Output verbosity controlled by `--quiet` (minimal), default (answer), and `--verbose` (node execution logs). Source display needs review after reasoner refactor.

---

### 🧪 Tests (pytest)

*   `test_agent.py` must include at least one test (needs significant updates).
*   Test must pass with no API keys (mocked responses only).
*   RAG module tests should skip gracefully if no `RAG_DOC_PATH` is available.

---

### 📘 README Instructions

1.  **Project Overview**
    > A small research agent that clarifies, plans (implicitly via outline), uses tools (Search/RAG) iteratively, and synthesizes answers using LLMs and LangGraph.
2.  **Quickstart**
    ```bash
    git clone https://github.com/youruser/deep-research-agent.git
    cd deep-research-agent
    pip install -r requirements.txt
    cp .env.example .env   # Fill in your SERPER and OPENAI keys
    python main.py
    ```
3.  **How It Works**: Update diagram + explanation for new flow.
4.  **Configuration**: Explain `config.yaml` including `reasoner` section.
5.  **Customize It**: Explain when to use `config.yaml` vs. editing Python code.
6.  **RAG Setup**: drop documents into `RAG_DOC_PATH` and rerun.
7.  **Verbosity Modes**: Explain `--quiet`, default, and `--verbose`.
8.  **Future Ideas**: Improve source tracking, FastAPI, MCP endpoints.

---

### 🔌 Extension Hooks

*   Plug `search.py` into other web APIs as desired (tool definition needs update).
*   Wrap `main.py` into a FastAPI service for web UI.
*   MCP endpoint wrapper for use in Cursor or other toolchains.
*   Add more tools to the Reasoner agent.

---

### ✅ Success Definition

*   `python main.py` must run a research loop using the iterative reasoner agent.
*   `pytest` must pass with offline mock (tests need update).
*   RAG activates as a tool if user supplies docs and `OPENAI_API_KEY`.
*   Users should be able to modify one module (e.g., synthesizer prompt) and see the agent change behavior.

---