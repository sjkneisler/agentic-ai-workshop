# Tech Context

## Technologies Used

- **Language:** Python (≥3.10)
- **Package Management:** pip (via `requirements.txt`)
- **Core Libraries:**
    - `python-dotenv`: For managing environment variables (`.env`).
    - `PyYAML`: For parsing configuration file (`config.yaml`).
    - `requests`: For making HTTP requests (Serper API).
    - `requests-html`: For fetching and parsing HTML content (`fetch_url` tool). - NEW
    - `lxml[html_clean]`: Dependency for `requests-html`. - NEW
    - `beautifulsoup4`: (Potentially used by `requests-html` or RAG utils).
    - `openai`: For interacting with OpenAI models (used via LangChain).
    - `langchain`: Core Langchain library.
    - `langchain-community`: Langchain community components.
    - `langchain-openai`: Langchain OpenAI integrations (embeddings, chat models).
    - `langchain-chroma`: Langchain Chroma vector store integration (used for session store).
    - `langchain-text-splitters`: For splitting documents (`chunk_embed_node`). - NEW (or implicitly required)
    - `chromadb`: Underlying vector store (used via `langchain-chroma` for session store).
    - `unstructured`: (Dependency for RAG loaders, currently unused by main loop).
    - `tiktoken`: For token counting (used with OpenAI/Langchain).
    - `sentence-transformers`: For cross-encoder re-ranking (`consolidate_notes_node`). - NEW
    - `rich` (optional): For enhanced terminal output (colors, formatting).
    - `certifi`: Used internally for SSL certificate handling.
    - `langgraph`: For orchestrating the agent workflow as a state graph.
- **Testing:** `pytest`
- **External APIs:**
    - Serper API (for web search results via `search_node`)
    - OpenAI API (for LLMs: clarifier, reasoner, summarizer, synthesizer; and for embeddings)

## Development Setup

- Clone the repository.
- Install dependencies: `pip install -r requirements.txt` (includes `requests-html`, `lxml[html_clean]`, `sentence-transformers`, etc.).
- Configure environment variables by copying `.env.example` to `.env` and filling in API keys (`SERPER_API_KEY`, `OPENAI_API_KEY`).
- Configure agent behavior by creating/editing `config.yaml` (includes sections for `reasoner`, `embedding`, `summarizer`, `retriever`, `consolidator`, `synthesizer`, and `graph` for recursion limit). - UPDATED
- Optionally, specify `RAG_DOC_PATH` in `.env` (currently unused by main loop).

## Technical Constraints

- Requires Python 3.10 or newer.
- Relies on external API keys for full functionality (OpenAI required for core LLM/embedding tasks, Serper required for search node).
- Session vector store is in-memory (using Chroma) and ephemeral per run.
- RAG functionality (persistent local doc store) exists but is not integrated into the main loop.
- Designed for CLI execution.

## Dependencies

- See `requirements.txt` for specific packages and versions (includes `requests-html`, `lxml[html_clean]`, `sentence-transformers`, `langgraph`, `langchain` suite, etc.). Pinning should be reviewed/updated.
- Assumes standard Python installation and network access for API calls and dependency installation.
- SSL certificate verification relies on the `certifi` package.