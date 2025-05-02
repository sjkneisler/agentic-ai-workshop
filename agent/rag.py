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
        return _chroma_client.get_collection(COLLECTION_NAME) if _rag_enabled else None

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
        raise RuntimeError("RAG_DOC_PATH is set, but OPENAI_API_KEY environment variable is missing. Cannot generate embeddings for RAG.")

    if verbose:
        print(f"RAG enabled. Document path: {rag_doc_path}")
        print(f"Initializing ChromaDB client (persistent path: {RAG_STORE_PATH})")

    try:
        # Initialize ChromaDB client (persistent)
        _chroma_client = chromadb.PersistentClient(path=RAG_STORE_PATH)

        # Initialize OpenAI Embedding Function
        _openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            # Consider specifying model_name if needed, e.g., "text-embedding-ada-002"
            # model_name="text-embedding-ada-002"
        )

        # Get or create the collection
        collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_openai_ef
            # Add metadata if needed, e.g., {"hnsw:space": "cosine"}
        )

        # TODO: Implement corpus embedding logic here
        # This should ideally only run if the collection is new or empty,
        # or if the source documents have changed.
        # For now, we just ensure the collection exists.
        if verbose:
             count = collection.count()
             print(f"ChromaDB collection '{COLLECTION_NAME}' ready. Current document count: {count}")
             if count == 0:
                 print("NOTE: Collection is empty. Corpus embedding needs to be implemented.")


        _rag_enabled = True
        _rag_initialized = True
        return collection

    except Exception as e:
        warnings.warn(f"Failed to initialize ChromaDB or OpenAI embeddings: {e}. Disabling RAG.")
        _rag_enabled = False
        _rag_initialized = True
        _chroma_client = None # Ensure client is None on failure
        _openai_ef = None
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
    if verbose:
        print("--- Querying Vector Store (RAG) ---")
        print(f"Querying for: '{query}' (n_results={n_results})")

    collection = _initialize_rag(verbose)

    if not collection:
        if verbose:
            print("RAG is not enabled or failed to initialize. Skipping query.")
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

# TODO: Implement a function to embed the corpus from RAG_DOC_PATH
# def embed_corpus(directory_path: Path, collection: chromadb.Collection, verbose: bool = False):
#     """Loads documents, chunks them, embeds, and adds to Chroma."""
#     if verbose:
#         print(f"--- Embedding Corpus from {directory_path} ---")
#     # Logic to find files (e.g., .txt, .md), load content, chunk, embed, add to collection
#     # Use collection.add() or collection.upsert()
#     # Needs careful implementation (chunking strategy, handling duplicates, etc.)
#     print("Corpus embedding logic not yet implemented.")
#     pass