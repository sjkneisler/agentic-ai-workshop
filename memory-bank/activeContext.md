# Active Context

## Current Work Focus

The initial implementation (v0.1.0) was completed, but initial testing revealed SSL certificate errors on macOS and issues with output formatting and answer depth. These have been addressed. Additionally, enhancements for configuration and output verbosity control have been implemented based on user feedback.

The current focus is on:
- **Verification:** Testing the major RAG refactoring, including Langchain integration, link following, semantic chunking, and source display.
- **Refinement:** Ensuring the new RAG system integrates smoothly with the agent pipeline and provides relevant context.
- **Planning Next Phase:** Considering further RAG enhancements (e.g., different chunking strategies, metadata filtering) or other goals.

## Recent Changes (since last Memory Bank update - Post v0.1.0)

- **Fixed SSL Errors:** Addressed `SSLError(SSLCertVerificationError)` on macOS by:
    - Adding `certifi` import and `verify=certifi.where()` to `requests.post` in `agent/search.py`.
    - Setting `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` environment variables in `main.py` using `certifi.where()`.
- **Corrected Output Formatting:** Fixed `main.py` to correctly print `rich.Panel` objects even when not in verbose mode.
- **Enhanced Answer Depth:** Modified the system prompt in `agent/synthesizer.py` to request more "detailed and comprehensive" answers instead of "concise" ones.
- **Implemented Configuration System:**
    - Created `config.yaml` for agent behavior settings (models, prompts, search count, etc.).
    - Added `PyYAML` to `requirements.txt`.
    - Created `agent/config.py` to load YAML configuration with defaults.
    - Refactored `agent/synthesizer.py` and `agent/search.py` to use settings from `config.yaml`.
    - Added `config.yaml` to `.gitignore`.
- **Implemented Verbosity Levels:**
    - Added mutually exclusive `--quiet` (`-q`, level 0) and `--verbose` (`-v`, level 2) flags in `main.py`, with default level 1.
    - Modified `agent/__init__.py` (`run_agent`) to accept `verbosity_level` and adjust internal printing.
    - `run_agent` now returns `(final_answer, source_urls)`.
    - `main.py` now conditionally prints Processing panel, Source URLs panel, and Final Answer panel based on verbosity level.
- **Updated Documentation:** Modified `README.md` to explain the new `config.yaml` system and verbosity levels.
- **Implemented RAG Corpus Embedding:**
    - Added `embed_corpus` function to `agent/rag.py` to process `.txt` and `.md` files.
    - Modified `_initialize_rag` to automatically call `embed_corpus` if the ChromaDB collection is empty upon initialization.
    - Refined RAG initialization logic to handle missing `OPENAI_API_KEY` more gracefully (warns and disables RAG instead of raising immediate error).
- **Updated Memory Bank:** This update reflects all changes above, including RAG embedding. (Self-reference for tracking).
- **Enhanced RAG Indexing with Internal Link Metadata:**
    - During indexing (`_initialize_rag`):
        - Continues to follow internal document links (`[[WikiLinks]]`, `[Markdown](link.md)`) up to `rag_initial_link_follow_depth` to load all relevant local files.
        - **NEW:** Before chunking, extracts internal links from each loaded document's content, resolves their target file paths.
        - **FIX:** Stores the list of paths as a serialized string (`internal_linked_paths_str`, joined by `;;`) in metadata to ensure Chroma compatibility.
        - Chunks documents using `SemanticChunker`, propagating the `internal_linked_paths_str` metadata to derived chunks.
        - Stores chunks with source path and `internal_linked_paths_str` metadata in Chroma.
        - External web links are *no longer* fetched during indexing.
- **Enhanced RAG Output:**
    - Modified `agent/rag.py` (`query_vector_store`) to return source file paths.
    - Updated `agent/__init__.py` (`run_agent`) to return RAG source paths.
    - Updated `main.py` to display a "Sources Used (Local Documents)" panel.
- **Refactored RAG to use Langchain Indexing API:**
    - Replaced manual ChromaDB setup and document processing in `agent/rag.py`.
    - Integrated `langchain_community.document_loaders` (`DirectoryLoader`, `TextLoader`, `UnstructuredMarkdownLoader`).
    - Integrated `langchain_openai.OpenAIEmbeddings`.
    - Integrated `langchain_chroma.Chroma` vector store wrapper.
    - Added dependencies: `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `unstructured` to `requirements.txt`.
    - Removed old `embed_corpus` function and `agent/rag_utils/ingestion.py` (initially).
- **Addressed Langchain/Chroma Compatibility:**
    - Updated Chroma import from `langchain_community` to `langchain_chroma`.
    - Added `langchain-chroma` dependency.
    - Required deletion of old `.rag_store` due to format incompatibility.
- **Fixed RAG Loader Dependency:**
    - Added missing `unstructured` dependency required by `UnstructuredMarkdownLoader`.
- **Switched to Semantic Chunker:**
    - Replaced `RecursiveCharacterTextSplitter` with `langchain_experimental.text_splitter.SemanticChunker` in `agent/rag.py`.
    - Ensured source metadata is preserved during semantic chunking.
- **Restored RAG Link Following (Post-Langchain Refactor):**
    - Re-created `agent/rag_utils/ingestion.py`.
    - Modified `agent/rag.py`'s `_initialize_rag` to perform link traversal *after* initial loading via `DirectoryLoader` but *before* splitting with `SemanticChunker`.
- **Enhanced RAG Retrieval with Link Traversal & Web Fetching:**
    - Modified `query_vector_store` in `agent/rag.py`.
    - Added new config options: `rag_follow_internal_chunk_links` (bool), `rag_internal_link_depth` (int), `rag_internal_link_k` (int).
    - **Retrieval Flow:**
        1. Performs initial semantic search for relevant chunks.
        2. **(Optional) Internal Chunk Traversal:** If `rag_follow_internal_chunk_links` is true, retrieves the `internal_linked_paths_str` metadata, splits it back into a list of paths, and uses these paths to perform filtered similarity searches for linked chunks in other documents, up to `rag_internal_link_depth`. Collects unique linked chunks.
        3. **(Optional) External Web Fetching:** If `rag_follow_external_links` is true, extracts all `http/https` links from the content of *all* collected chunks (initial + internally linked). Fetches content using `requests`/`BeautifulSoup` on the fly.
        4. Combines context from initial chunks, internally linked chunks, and fetched web pages.
        5. Returns combined context and a list of all contributing sources (local file paths and fetched web URLs).
- **Refactored RAG Structure:** Moved RAG initialization logic to `agent/rag_utils/rag_initializer.py` and query logic to `agent/rag_utils/rag_query.py`, updating `agent/rag.py` to be an interface.
- **Implemented Interactive LangChain Clarifier:**
    - Refactored `agent/clarifier.py` to use LangChain components (`ChatOpenAI`, `ChatPromptTemplate`, `JsonOutputParser`, `StrOutputParser`) instead of direct `openai` calls. Models and temperature are configurable via `config.yaml` (`clarification_model`, `refinement_model`, etc.).
    - **Clarification Check:** A LangChain chain determines if the initial question needs clarification and suggests specific questions to ask the user (using `JsonOutputParser`).
    - **User Interaction:** If clarification is needed, the agent prompts the user with the suggested questions directly in the terminal and waits for input.
    - **Question Refinement:** A second LangChain chain synthesizes a refined question based on the original query and the user's answers (using `StrOutputParser`).
    - Falls back to the original question if `OPENAI_API_KEY` is missing, LangChain components fail to initialize, user cancels, or chain invocations fail.
    - Requires `langchain-openai`, `langchain-core` libraries and `OPENAI_API_KEY` in `.env` for clarification functionality.

## Next Steps

1.  **Install/Update Dependencies:**
    *   Run `python3 -m pip install -r requirements.txt` (to ensure `PyYAML`, `langchain`, `langchain-community`, `langchain-openai`, `langchain-core`, `langchain-chroma`, `unstructured` are installed).
2.  **Configure Environment & Config:**
    *   Ensure `.env` has valid `SERPER_API_KEY` and `OPENAI_API_KEY` (now required for RAG *and* LangChain Clarification).
    *   Ensure `RAG_DOC_PATH` in `.env` points to a directory with `.txt` or `.md` files (including some with internal *and external* links for testing).
    *   Review/modify `config.yaml`, especially the RAG section (`rag_...` settings) and the new Clarifier section (`clarification_model`, `refinement_model`, etc.).
3.  **Manual Testing (Focus on Clarifier & RAG):**
    *   Delete the `.rag_store` directory if it exists from previous incompatible versions.
    *   Run with default/verbose mode: `python3 main.py "..."`
    *   **Test Clarifier:**
        *   Ask ambiguous questions to trigger the clarification flow.
        *   Answer the follow-up questions in the terminal.
        *   Verify the refined question (in verbose output) makes sense.
        *   Test cancelling the clarification (Ctrl+C).
        *   Test running without an `OPENAI_API_KEY` to ensure it skips clarification gracefully.
    *   **Test RAG (as before):**
        *   Verify RAG initialization messages.
        *   Ask questions designed to trigger retrieval from specific documents and linked documents (using the *refined* question if clarification occurred).
        *   Check the "Sources Used (Local Documents)" panel.
        *   Check verbose output (`-v`) for RAG details.
        *   Test different RAG settings in `config.yaml`.
        *   Verify context from internal/external links appears as expected.
        *   Verify the "Sources Used" panel lists all sources correctly.
4.  **Run Automated Tests:**
    *   Execute `python3 -m pytest`. Tests interacting with RAG *and Clarifier* will likely need significant updates or mocking.
5.  **Address Issues:** Fix any bugs identified during testing.
6.  **Consider Enhancements:** Review RAG performance, explore different Langchain splitters/loaders, or other goals.

## Active Decisions & Considerations

- **Configuration:** `config.yaml` is now the primary method for tuning common agent parameters (models, prompts, search count). `.env` remains for secrets.
- **Verbosity:** Three distinct levels (`quiet`, `default`, `verbose`) control the CLI output. Default shows sources, verbose shows internal steps.
- **Agent Output:** `run_agent` now returns both the answer and the list of source URLs.
- **SSL Fix:** The implemented SSL fix targets common macOS issues by explicitly using `certifi` bundle.
- **Testing:** Automated tests (`pytest`) might need updates to accommodate the new configuration system and `run_agent` return type.
- **RAG:** RAG implementation uses Langchain Indexing API (`DirectoryLoader`, `SemanticChunker`, `OpenAIEmbeddings`, `Chroma`).
    - **Indexing:** Follows internal document links up to `rag_initial_link_follow_depth`. Stores resolved target file paths from internal links as a serialized string (`internal_linked_paths_str`) in metadata on chunks (due to Chroma limitations) before saving to Chroma. Does *not* fetch external links during indexing.
    - **Retrieval:** Performs initial semantic search. Optionally traverses internal links *between chunks* by deserializing the stored `internal_linked_paths_str` metadata and performing filtered searches (controlled by `rag_follow_internal_chunk_links`, `rag_internal_link_depth`, `rag_internal_link_k`). Optionally fetches external web links found in collected chunks on the fly (controlled by `rag_follow_external_links`). Combines all context.
- **Agent Output:** `run_agent` now returns `(final_answer, web_source_urls, rag_source_paths)`. `main.py` displays both web and local sources (including fetched web URLs and sources from internally linked chunks).
- **Clarification:** The agent now uses an interactive LangChain-based clarification step (`agent/clarifier.py`) if an `OPENAI_API_KEY` is provided. It uses `ChatOpenAI` and structured output parsing to determine if clarification is needed, prompts the user in the terminal with suggested questions, and then refines the query using another LangChain chain. This behavior can be tuned via `config.yaml`.