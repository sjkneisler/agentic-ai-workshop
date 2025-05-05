# Product Context

## Why This Project Exists

This project aims to create a clear, runnable demonstration of a recursive research agent pipeline. It serves as an educational tool and a foundation for more complex agentic systems.

## Problems It Solves

- Provides a practical example of agentic workflow (Clarify -> Plan -> Search -> Reason -> Synthesize).
- Offers a modular structure that's easy to understand and extend.
- Lowers the barrier to entry for experimenting with research agents by using standard Python and minimal dependencies.

## How It Should Work

- The agent takes a user's question via a command-line interface (CLI).
- The agent's workflow is orchestrated by LangGraph (`agent/__init__.py`), defining a state machine with nodes for each step:
    - **Clarification Node (`agent/clarifier.py`):** Uses LangChain components (initialized via `agent/utils.py`) to determine if the initial question is ambiguous. If so, it suggests specific follow-up questions, prompts the user for answers in the terminal, and then uses another LangChain chain to synthesize a refined question. Requires `langchain-openai`, `langchain-core`, an `OPENAI_API_KEY`, and uses models/settings from `config.yaml`. If clarification isn't needed or possible, it uses the original question.
    - **Planning Node (`agent/planner.py`):** Determines the next steps (typically "search" and potentially "rag") based on the (potentially refined) question and environment configuration (`RAG_DOC_PATH`).
    - **Search Node (`agent/search.py`):** Executes web searches using the (potentially refined) question and the Serper API (requires `SERPER_API_KEY`).
    - **RAG Node (`agent/rag_utils/rag_query.py`):** If enabled (`RAG_DOC_PATH` in `.env`, `OPENAI_API_KEY` needed), retrieves relevant context from local documents using the (potentially refined) question.
        - *Indexing (handled by `agent/rag_utils/rag_initializer.py`):* Uses LangChain (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`) to load local documents, follow internal links, and embed into a persistent Chroma store, storing internal link metadata.
        - *Retrieval:* Performs semantic search, optionally traverses internal chunk links (using stored metadata), and optionally fetches external web links found in context (controlled by `config.yaml`).
    - **Reasoning Node (`agent/reasoner.py`):** Consolidates information from search results and RAG context.
    - **Synthesis Node (`agent/synthesizer.py`):** Generates the final answer using an LLM (initialized via `agent/utils.py`) based on the (potentially refined) question and consolidated context. Requires `OPENAI_API_KEY` and uses settings from `config.yaml`.
- The LangGraph application (`app`) is invoked by `agent.run_agent()`.
- It utilizes external APIs (Serper for search, OpenAI via LangChain/utils for LLM tasks) configured via `.env` (API keys) and `config.yaml` (models, prompts, RAG settings, clarification settings).
- The final synthesized answer (or error message) from the graph's final state is printed to the console. Output detail is controlled via `--quiet`, default (includes web and local sources), and `--verbose` (includes intermediate node execution logs) flags.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand.
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules easily.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.