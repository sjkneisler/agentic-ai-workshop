"""
Agent module for Retrieval-Augmented Generation (RAG).

Queries a local vector store (ChromaDB) built from user-provided
documents to retrieve relevant context. Requires RAG_DOC_PATH and
OPENAI_API_KEY environment variables to be set for full functionality.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import warnings
from typing import Optional

# --- Constants ---
RAG_STORE_PATH = ".rag_store"
COLLECTION_NAME = "research_docs"
SUPPORTED_FILE_TYPES = ['.txt', '.md'] # Added

# --- Globals / State (Consider refactoring to a class if state becomes complex) ---
_chroma_client: Optional[chromadb.Client] = None
_openai_ef: Optional[embedding_functions.OpenAIEmbeddingFunction] = None
_rag_initialized = False
_rag_enabled = False

def _initialize_rag(verbose: bool = False) -> Optional[chromadb.Collection]:
    """
    Initializes the RAG system: checks env vars, sets up ChromaDB client
    and collection, and potentially triggers corpus embedding.

    Returns:
        The ChromaDB collection object if RAG is enabled and initialized,
        otherwise None.
    """
    global _chroma_client, _openai_ef, _rag_initialized, _rag_enabled

    if _rag_initialized:
        # Optimization: If already initialized, return existing state
        if not _rag_enabled or not _chroma_client:
             return None
        try:
            # Ensure collection still exists if client was persisted
            return _chroma_client.get_collection(name=COLLECTION_NAME, embedding_function=_openai_ef)
        except Exception as e:
             warnings.warn(f"Error retrieving existing collection '{COLLECTION_NAME}': {e}. Re-initializing.")
             # Fall through to re-initialize if retrieval fails

    # Reset state for re-initialization attempt
    _rag_initialized = False
    _rag_enabled = False
    _chroma_client = None
    _openai_ef = None


    if verbose:
        print("--- Initializing RAG System ---")

    rag_doc_path_str = os.getenv("RAG_DOC_PATH")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not rag_doc_path_str:
        if verbose:
            print("RAG_DOC_PATH not set. Skipping RAG initialization.")
        _rag_enabled = False
        _rag_initialized = True
        return None

    rag_doc_path = Path(rag_doc_path_str)
    if not rag_doc_path.is_dir():
        warnings.warn(f"RAG_DOC_PATH ('{rag_doc_path_str}') does not exist or is not a directory. Disabling RAG.")
        _rag_enabled = False
        _rag_initialized = True
        return None

    if not openai_api_key:
        # Allow initialization without key, but embedding/query will fail later if needed
        warnings.warn("OPENAI_API_KEY environment variable is missing. RAG embedding/querying will fail if attempted.")
        # We can still proceed to set up the client/collection structure if desired
        # but let's disable RAG for now to prevent downstream errors.
        _rag_enabled = False
        _rag_initialized = True
        return None # Or raise RuntimeError as before if strictness is preferred

    if verbose:
        print(f"RAG enabled. Document path: {rag_doc_path}")
        print(f"Initializing ChromaDB client (persistent path: {RAG_STORE_PATH})")

    try:
        # Initialize ChromaDB client (persistent)
        _chroma_client = chromadb.PersistentClient(path=RAG_STORE_PATH)

        # Initialize OpenAI Embedding Function
        _openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            # model_name="text-embedding-3-small" # Example: Specify model if needed
        )

        # Get or create the collection
        collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_openai_ef
            # Add metadata if needed, e.g., {"hnsw:space": "cosine"}
        )

        # --- MODIFICATION START ---
        # Embed corpus if the collection is empty
        initial_count = collection.count()
        if initial_count == 0:
            if verbose:
                print(f"Collection '{COLLECTION_NAME}' is empty. Attempting to embed corpus from {rag_doc_path}...")
            embed_corpus(rag_doc_path, collection, verbose=verbose)
            if verbose:
                 final_count = collection.count()
                 print(f"Corpus embedding finished. Document chunk count: {final_count}")
        elif verbose:
            print(f"ChromaDB collection '{COLLECTION_NAME}' already contains {initial_count} documents. Skipping embedding.")
        # --- MODIFICATION END ---


        _rag_enabled = True
        _rag_initialized = True
        return collection

    except Exception as e:
        warnings.warn(f"Failed to initialize ChromaDB or OpenAI embeddings: {e}. Disabling RAG.")
        _rag_enabled = False
        _rag_initialized = True
        _chroma_client = None # Ensure client is None on failure
        _openai_ef = None
        if verbose:
            import traceback
            traceback.print_exc()
        return None


def query_vector_store(query: str, n_results: int = 3, verbose: bool = False) -> str:
    """
    Queries the local vector store for context relevant to the query.

    Args:
        query: The query string to search for in the vector store.
        n_results: The maximum number of results to retrieve.
        verbose: Flag for detailed output.

    Returns:
        A string containing relevant context retrieved from the store,
        concatenated from the 'documents' field of the results.
        Returns an empty string if RAG is disabled, not initialized,
        or no relevant context is found.
    """
    # ... (existing query logic - needs slight adjustment to handle potential init failure)
    if verbose:
        print("--- Querying Vector Store (RAG) ---")
        print(f"Querying for: '{query}' (n_results={n_results})")

    # Ensure RAG is initialized before querying
    collection = _initialize_rag(verbose)

    # Check _rag_enabled state AFTER initialization attempt
    if not _rag_enabled or not collection:
        if verbose:
            print("RAG is not enabled or failed to initialize properly. Skipping query.")
        return ""

    rag_context = ""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            # include=['documents', 'metadatas', 'distances'] # Include desired fields
            include=['documents']
        )

        if results and results.get('documents') and results['documents'][0]:
            # Concatenate the document snippets
            rag_context = "\n\n".join(results['documents'][0])
            if verbose:
                print(f"Found {len(results['documents'][0])} relevant document chunks in vector store.")
                # print(f"Retrieved context:\n{rag_context}") # Can be very verbose
        elif verbose:
            print("No relevant documents found in vector store for this query.")

    except Exception as e:
        warnings.warn(f"Error querying ChromaDB collection '{COLLECTION_NAME}': {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        rag_context = "" # Ensure empty string on error

    return rag_context

# --- NEW FUNCTION ---
def embed_corpus(directory_path: Path, collection: chromadb.Collection, verbose: bool = False):
    """
    Loads documents from the specified directory, chunks them, and adds them
    to the ChromaDB collection. Skips files that are not supported.

    Args:
        directory_path: The Path object pointing to the directory containing documents.
        collection: The ChromaDB collection object to add documents to.
        verbose: Flag for detailed output.
    """
    if verbose:
        print(f"--- Embedding Corpus from {directory_path} ---")

    all_docs = []
    all_metadatas = []
    all_ids = []
    doc_index = 0

    for file_path in directory_path.rglob('*'): # Use rglob for recursive search
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FILE_TYPES:
            if verbose:
                print(f"Processing file: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Simple chunking by paragraphs (or significant whitespace)
                chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]

                if not chunks:
                    if verbose:
                        print(f"  No content chunks found in {file_path}. Skipping.")
                    continue

                for i, chunk in enumerate(chunks):
                    doc_id = f"{file_path.stem}_{i}" # Create a unique ID for each chunk
                    all_docs.append(chunk)
                    all_metadatas.append({"source": str(file_path.relative_to(directory_path))}) # Store relative path
                    all_ids.append(doc_id)
                    doc_index += 1

            except Exception as e:
                warnings.warn(f"Error processing file {file_path}: {e}")
        elif file_path.is_file() and verbose:
             print(f"Skipping unsupported file type: {file_path}")


    if not all_docs:
        if verbose:
            print("No processable documents found in the specified directory.")
        return

    if verbose:
        print(f"Adding {len(all_docs)} document chunks to collection '{collection.name}'...")

    try:
        # Add documents in batches if necessary (ChromaDB handles batching internally to some extent)
        # For very large corpora, consider explicit batching.
        collection.add(
            documents=all_docs,
            metadatas=all_metadatas,
            ids=all_ids
        )
        if verbose:
            print("Successfully added documents to the collection.")
    except Exception as e:
        warnings.warn(f"Error adding documents to ChromaDB collection '{collection.name}': {e}")
        if verbose:
            import traceback
            traceback.print_exc()

# --- END NEW FUNCTION ---