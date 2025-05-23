## 🧠 Deep Research Agent – Demo Repo Plan (v1.1 Final)

This plan is for an AI coding agent (without autonomous web access) to bootstrap and maintain a public-facing repository implementing a recursive research agent. It combines symbolic reasoning structure with runnable modular code, designed to be extended incrementally.

---

### 🎯 Purpose

Create a runnable Python project demonstrating a recursive research agent pipeline:

* Clarifier → Planner → Search → (Optional RAG) → Reason → Synthesize
* Designed to run in CLI with Serper search and optional Chroma-based RAG
* Clear modularity for agents, extendability with LangGraph or MCP
* Low barrier to entry: one script, clearly segmented modules, `.env` driven config

---

### 📂 Repo Layout

```
/
├── README.md
├── requirements.txt                 # Python ≥3.10, no poetry
├── .env.example                     # SERPER_API_KEY, OPENAI_API_KEY, RAG_DOC_PATH
├── main.py                          # CLI entrypoint
├── agent/
│   ├── __init__.py
│   ├── clarifier.py                # clarify_question()
│   ├── planner.py                  # plan_steps()
│   ├── search.py                   # serper_search()
│   ├── rag.py                      # query_vector_store()
│   ├── reasoner.py                 # reason_over_sources()
│   └── synthesizer.py              # synthesize_answer()
└── tests/
    ├── mock_serper.json            # fixture
    └── test_agent.py
```

---

### 🔑 Environment Variables

```
SERPER_API_KEY=...        # required for real search
OPENAI_API_KEY=...        # required only if RAG is enabled
RAG_DOC_PATH=./my_docs    # optional user-supplied local document directory
```

---

### 🚀 Agent Flow (main.py)

1. Prompt user: `input("🔍 Question: ")`
2. Clarify input → `clarifier.py`
3. Plan next steps → `planner.py` → returns e.g. `["search", "rag"]`
4. Search results → `search.py` (Serper API, mocked in tests)
5. Optional RAG → `rag.py` (Chroma vector search over `RAG_DOC_PATH`)
6. Reason over sources → `reasoner.py`
7. Synthesize answer → `synthesizer.py`
8. Print final answer. If `--verbose`, print each step’s intermediate output.

---

### 🛠 Agent Implementation Rules

* All agent modules are standalone, with one clear job
* No license file (private/internal use only)
* If API keys are missing, script must fail gracefully with clear message
* All functions must include docstrings specifying I/O expectations
* `--verbose` mode must display reasoning steps and decision trace

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
4. **Customize It**: edit individual agent modules
5. **RAG Setup**: drop documents into `RAG_DOC_PATH` and rerun
6. **Verbose Mode**: `python main.py --verbose`
7. **Future Ideas**: LangGraph, FastAPI, MCP endpoints

---

### 🔌 Extension Hooks

* Plug `search.py` into other web APIs as desired
* Wrap `main.py` into a FastAPI service for web UI
* Convert the agent steps to LangGraph nodes with dynamic state edge control
* MCP endpoint wrapper for use in Cursor or other toolchains

---

### ✅ Success Definition

* `python main.py` must run a real Serper-based research loop
* `pytest` must pass with offline mock
* RAG activates if user supplies docs and `OPENAI_API_KEY`
* Users should be able to modify one module and see the agent change behavior in <10 minutes

---
