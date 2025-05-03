# Product Context

## Why This Project Exists

This project aims to create a clear, runnable demonstration of a recursive research agent pipeline. It serves as an educational tool and a foundation for more complex agentic systems.

## Problems It Solves

- Provides a practical example of agentic workflow (Clarify -> Plan -> Search -> Reason -> Synthesize).
- Offers a modular structure that's easy to understand and extend.
- Lowers the barrier to entry for experimenting with research agents by using standard Python and minimal dependencies.

## How It Should Work

- The agent takes a user's question via a command-line interface (CLI).
- It follows a predefined sequence of steps, calling specific Python modules for each task (clarification, planning, searching, optional RAG, reasoning, synthesis).
- It utilizes external APIs (Serper for search, OpenAI for LLM tasks) configured via `.env` (API keys) and `config.yaml` (models, prompts).
- It can optionally incorporate local documents into its knowledge base using Retrieval-Augmented Generation (RAG) with ChromaDB.
- The final synthesized answer is printed to the console. Output detail is controlled via `--quiet`, default (includes sources), and `--verbose` (includes intermediate steps) flags.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand.
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules easily.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.