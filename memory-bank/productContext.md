# Product Context

## Why This Project Exists

This project aims to create a clear, runnable demonstration of a research agent pipeline using LangGraph. It serves as an educational tool and a foundation for more complex agentic systems, showcasing a deep research loop involving web fetching, session-based vector storage, iterative retrieval/summarization, and citation handling.

## Problems It Solves

- Provides a practical example of a more sophisticated agentic workflow (Clarify+Outline -> Reason -> [Search -> Fetch -> Chunk/Embed -> Retrieve -> Summarize] -> Consolidate -> Synthesize).
- Offers a modular structure using LangGraph nodes that's easy to understand and extend.
- Demonstrates techniques like session-based vector stores, source-grounded summarization, and citation post-processing.
- Lowers the barrier to entry for experimenting with research agents by using standard Python and LangChain/LangGraph.

## How It Should Work (Updated for Deep Research Loop)

- The agent takes a user's question via a command-line interface (CLI).
- The agent's workflow is orchestrated by LangGraph (`agent/__init__.py`), defining a state machine with nodes primarily in `agent/nodes/`:
    - **Clarification Node (`clarifier.py`):** Uses LangChain components to refine the question and generate a Markdown research outline (`plan_outline`). Updates `clarified_question` and `plan_outline` state.
    - **Reasoning Node (`reasoner.py`):** Acts as the central decision-maker. Based on the question, outline, current notes, and iteration count, it decides the `next_action` (SEARCH, FETCH, RETRIEVE_CHUNKS, CONSOLIDATE, STOP) and sets necessary arguments (`current_query`, `url_to_fetch`) in the state.
    - **Search Node (`search.py`):** Executes a web search via `agent.search.serper_search` using `current_query`. Updates `search_results`. Returns to Reasoner.
    - **Fetch Node (`fetch.py`):** Fetches full HTML content from `url_to_fetch` using the `agent.tools.fetch.fetch_url` tool. Updates `fetched_docs`. Proceeds to Chunk/Embed.
    - **Chunk/Embed Node (`chunk_embed.py`):** Takes `fetched_docs`, chunks the HTML, generates embeddings (using OpenAI via `utils.py`), and adds them to the `session_vector_store` (in-memory Chroma). Clears `fetched_docs`. Returns to Reasoner.
    - **Retrieve Node (`retrieve.py`):** Queries the `session_vector_store` using `current_query`. Updates `retrieved_chunks`. Proceeds to Summarize.
    - **Summarize Node (`summarize.py`):** Takes `retrieved_chunks`, uses a smaller LLM (via `utils.py`) to generate a concise note with detailed embedded source citations (e.g., `[Source URL='...', Title='...', Chunk=...]`). Appends note to `notes`. Clears `retrieved_chunks`. Returns to Reasoner.
    - **Consolidate Node (`consolidate.py`):** Takes all `notes`, re-ranks them against the `clarified_question` using a sentence-transformer cross-encoder. Selects the top N notes and formats them into `combined_context`. Proceeds to Synthesize.
    - **Synthesis Node (`synthesizer.py`):** Generates the final answer using a primary LLM (via `utils.py`) based on `clarified_question` and `combined_context` (curated notes). Preserves detailed citations during generation, then post-processes the answer to create a numbered reference list and replace inline citations with numbers (e.g., `[ref:1]`). Updates `final_answer`.
- The LangGraph application (`app`) is invoked by `agent.run_agent()`.
- It utilizes external APIs (Serper for search, OpenAI for LLMs/embeddings) configured via `.env` (API keys) and `config.yaml` (models, prompts, component settings).
- The final synthesized answer (with references) or error message is printed to the console. Output detail is controlled via CLI flags.

## User Experience Goals

- **Simplicity:** Relatively easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be understandable, demonstrating a clear research pattern.
- **Extensibility:** Users should feel empowered to modify node behavior (e.g., prompts via config), add tools, or integrate other components (like the existing RAG).
- **Graceful Failure:** The agent should provide clear error messages if required configurations or dependencies are missing.
- **Transparency:** Verbose mode should allow users to follow the decision-making and data flow through the graph nodes.