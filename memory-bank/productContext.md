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
- It can optionally incorporate local documents (`.txt`, `.md`) into its knowledge base using Retrieval-Augmented Generation (RAG).
    - **Indexing:** Uses Langchain (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`) to load local documents from `RAG_DOC_PATH`, following internal document links up to `rag_initial_link_follow_depth`. Stores internal link target paths as a serialized string (`internal_linked_paths_str`) in chunk metadata (for Chroma compatibility) before embedding into a persistent Chroma store.
    - **Retrieval:** Performs an initial semantic search. Optionally traverses internal links between retrieved chunks by deserializing the stored metadata string and performing filtered searches (controlled by `rag_follow_internal_chunk_links`, `rag_internal_link_depth`, `rag_internal_link_k`). Optionally fetches content from external web links found in collected chunks on the fly (controlled by `rag_follow_external_links`).
- The final synthesized answer is printed to the console. Output detail is controlled via `--quiet`, default (includes web and local sources from all RAG steps), and `--verbose` (includes intermediate steps) flags.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand.
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules easily.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.