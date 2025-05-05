# Tech Context

## Technologies Used

- **Language:** Python (≥3.10)
- **Package Management:** pip (via `requirements.txt`)
- **Core Libraries:**
    - `python-dotenv`: For managing environment variables (`.env`).
    - `PyYAML`: For parsing configuration file (`config.yaml`).
    - `requests`: For making HTTP requests (Serper API, RAG web fetching). - UPDATED
    - `beautifulsoup4`: For parsing HTML content from RAG web fetching. - NEW
    - `openai`: For interacting with OpenAI models (clarification, synthesis).
    - `langchain`: Core Langchain library. - NEW
    - `langchain-community`: Langchain community components (loaders, splitters). - NEW
    - `langchain-openai`: Langchain OpenAI integrations (embeddings). - NEW
    - `langchain-chroma`: Langchain Chroma vector store integration. - NEW
    - `chromadb`: Underlying vector store (used via `langchain-chroma`).
    - `unstructured`: Document parsing library (dependency for Markdown loader). - NEW
    - `tiktoken`: For token counting (used with OpenAI/Langchain).
    - `rich` (optional): For enhanced terminal output (colors, formatting).
    - `certifi`: Used internally for SSL certificate handling.
- **Testing:** `pytest`
- **External APIs:**
    - Serper API (for web search results)
    - OpenAI API (for LLM capabilities)

## Development Setup

- Clone the repository.
- Install dependencies: `pip install -r requirements.txt` (includes `PyYAML`).
- Configure environment variables by copying `.env.example` to `.env` and filling in API keys (`SERPER_API_KEY`, `OPENAI_API_KEY`).
- Configure agent behavior by creating/editing `config.yaml` (see README for options). - NEW
- Optionally, specify `RAG_DOC_PATH` in `.env` to point to a directory of local documents for RAG.

## Technical Constraints

- Requires Python 3.10 or newer.
- Relies on external API keys for full functionality (Serper required, OpenAI optional for RAG/clarification).
- RAG functionality depends on the existence of documents in the specified `RAG_DOC_PATH` and a valid `OPENAI_API_KEY`.
- Designed for CLI execution.

## Dependencies

- See `requirements.txt` for specific packages and versions (includes `PyYAML`, `langchain` suite, `unstructured`, `requests`, `beautifulsoup4`, etc.). Pinning should be reviewed/updated.
- Assumes standard Python installation and network access for API calls and dependency installation.
- SSL certificate verification relies on the `certifi` package.