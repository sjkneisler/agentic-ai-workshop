# Tech Context

## Technologies Used

- **Language:** Python (≥3.10)
- **Package Management:** pip (via `requirements.txt`)
- **Core Libraries:**
    - `python-dotenv`: For managing environment variables.
    - `requests`: For making HTTP requests to the Serper API.
    - `openai`: For interacting with OpenAI models (clarification, synthesis, RAG embeddings).
    - `chromadb`: For local vector storage and retrieval (RAG).
    - `tiktoken`: For token counting (used with OpenAI).
    - `rich` (optional): For enhanced terminal output (colors, formatting).
- **Testing:** `pytest`
- **External APIs:**
    - Serper API (for web search results)
    - OpenAI API (for LLM capabilities)

## Development Setup

- Clone the repository.
- Install dependencies: `pip install -r requirements.txt`
- Configure environment variables by copying `.env.example` to `.env` and filling in API keys (`SERPER_API_KEY`, `OPENAI_API_KEY`).
- Optionally, specify `RAG_DOC_PATH` in `.env` to point to a directory of local documents for RAG.

## Technical Constraints

- Requires Python 3.10 or newer.
- Relies on external API keys for full functionality (Serper required, OpenAI optional for RAG/clarification).
- RAG functionality depends on the existence of documents in the specified `RAG_DOC_PATH` and a valid `OPENAI_API_KEY`.
- Designed for CLI execution.

## Dependencies

- See `requirements.txt` for specific package versions (to be pinned later in the process).
- Assumes standard Python installation and network access for API calls.