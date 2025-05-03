# Tech Context

## Technologies Used

- **Language:** Python (≥3.10)
- **Package Management:** pip (via `requirements.txt`)
- **Core Libraries:**
    - `python-dotenv`: For managing environment variables (`.env`).
    - `PyYAML`: For parsing configuration file (`config.yaml`). - NEW
    - `requests`: For making HTTP requests to the Serper API.
    - `openai`: For interacting with OpenAI models (clarification, synthesis, RAG embeddings).
    - `chromadb`: For local vector storage and retrieval (RAG).
    - `tiktoken`: For token counting (used with OpenAI).
    - `rich` (optional): For enhanced terminal output (colors, formatting).
    - `certifi`: Used internally for SSL certificate handling. - NEW (Implicit dependency, but good to note)
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

- See `requirements.txt` for specific package versions (includes `PyYAML`). Pinning was attempted during the v0.1.0 polish pass, though some versions might require manual verification based on the specific Python environment used.
- Assumes standard Python installation and network access for API calls.
- SSL certificate verification relies on the `certifi` package, which is automatically installed/updated by the SSL fix logic if needed, or included in `requirements.txt`.