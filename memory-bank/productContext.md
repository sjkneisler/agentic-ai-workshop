# Product Context

## Why This Project Exists

This project aims to create a clear, runnable demonstration of a recursive research agent pipeline. It serves as an educational tool and a foundation for more complex agentic systems.

## Problems It Solves

- Provides a practical example of agentic workflow (Clarify -> Plan -> Search -> Reason -> Synthesize).
- Offers a modular structure that's easy to understand and extend.
- Lowers the barrier to entry for experimenting with research agents by using standard Python and minimal dependencies.

## How It Should Work

- The agent takes a user's question via a command-line interface (CLI).
- It follows a sequence of steps:
    - **Clarification:** Uses LangChain components (`ChatOpenAI`, prompts, output parsers in `agent/clarifier.py`) to determine if the initial question is ambiguous. If so, it suggests specific follow-up questions, prompts the user for answers in the terminal, and then uses another LangChain chain to synthesize a refined question. This step requires `langchain-openai`, `langchain-core`, an `OPENAI_API_KEY`, and uses models/settings from `config.yaml`. If clarification isn't needed or possible, it uses the original question.
    - **Planning:** Determines the next steps (`agent/planner.py`), typically including "search" and potentially "rag" if configured, using the (potentially refined) question.
    - **Searching:** Executes web searches (`agent/search.py`) using the (potentially refined) question and the Serper API (requires `SERPER_API_KEY`).
    - **RAG (Optional):** If enabled and configured (`RAG_DOC_PATH` in `.env`, `OPENAI_API_KEY` needed), retrieves relevant context from local documents (`agent/rag.py`) using the (potentially refined) question.
        - **Indexing:** Uses LangChain (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`) to load local documents from `RAG_DOC_PATH`, following internal document links up to `rag_initial_link_follow_depth`. Stores internal link target paths as a serialized string (`internal_linked_paths_str`) in chunk metadata (for Chroma compatibility) before embedding into a persistent Chroma store.
        - **Retrieval:** Performs an initial semantic search using the (potentially refined) question. Optionally traverses internal links between retrieved chunks by deserializing the stored metadata string and performing filtered searches (controlled by `rag_follow_internal_chunk_links`, `rag_internal_link_depth`, `rag_internal_link_k`). Optionally fetches content from external web links found in collected chunks on the fly (controlled by `rag_follow_external_links`).
    - **Reasoning:** Consolidates information from search and RAG (`agent/reasoner.py`).
    - **Synthesis:** Generates the final answer using an LLM (`agent/synthesizer.py`) based on the (potentially refined) question and consolidated context, requiring `OPENAI_API_KEY` and using settings from `config.yaml`.
- It utilizes external APIs (Serper for search, OpenAI via LangChain for LLM tasks) configured via `.env` (API keys) and `config.yaml` (models, prompts, RAG settings, clarification settings).
- The final synthesized answer is printed to the console. Output detail is controlled via `--quiet`, default (includes web and local sources from all RAG steps), and `--verbose` (includes intermediate steps) flags.
    - **Indexing:** Uses Langchain (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`) to load local documents from `RAG_DOC_PATH`, following internal document links up to `rag_initial_link_follow_depth`. Stores internal link target paths as a serialized string (`internal_linked_paths_str`) in chunk metadata (for Chroma compatibility) before embedding into a persistent Chroma store.
    - **Retrieval:** Performs an initial semantic search. Optionally traverses internal links between retrieved chunks by deserializing the stored metadata string and performing filtered searches (controlled by `rag_follow_internal_chunk_links`, `rag_internal_link_depth`, `rag_internal_link_k`). Optionally fetches content from external web links found in collected chunks on the fly (controlled by `rag_follow_external_links`).
- The final synthesized answer is printed to the console. Output detail is controlled via `--quiet`, default (includes web and local sources from all RAG steps), and `--verbose` (includes intermediate steps) flags.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand.
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules easily.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.