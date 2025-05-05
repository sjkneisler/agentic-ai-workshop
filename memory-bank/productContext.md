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
- It can optionally incorporate local documents (`.txt`, `.md`) into its knowledge base using Retrieval-Augmented Generation (RAG). It uses the Langchain framework (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`) to automatically load, chunk (semantically), and embed documents found in the `RAG_DOC_PATH` into a persistent Chroma vector store upon initialization if the store is empty or incompatible. It follows internal Markdown/Wiki links between documents up to a configurable depth (`rag_link_follow_depth`). **NEW:** If enabled via `rag_follow_external_links` in `config.yaml`, it will also attempt to fetch and include content from external web links (`http/https`) found within the documents.
- The final synthesized answer is printed to the console. Output detail is controlled via `--quiet`, default (includes web and local sources, including fetched web URLs), and `--verbose` (includes intermediate steps) flags.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand.
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules easily.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.