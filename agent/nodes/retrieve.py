"""
LangGraph node for retrieving relevant chunks from the session vector store.
"""
import warnings
from typing import Dict, Any, List

# State and Config
from agent.state import AgentState
from agent.config import get_retriever_config # Need to add this to config.py

# LangChain components
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings # For type hinting

# Shared Utilities
from agent.utils import print_verbose, initialize_embedding_model # Need this utility

# --- LangGraph Node ---

def retrieve_relevant_chunks_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieves relevant document chunks from the session_vector_store
    based on a query (expected in state['current_query']).
    Puts the results into state['retrieved_chunks'].
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"):
        if is_verbose: print_verbose("Skipping retrieval due to previous error.", style="yellow")
        return {}

    if is_verbose: print_verbose("Entering Retrieve Relevant Chunks Node", style="magenta")

    vector_store: VectorStore = state.get('session_vector_store')
    query: str = state.get('current_query') # Expect the reasoner node to set this

    if not vector_store:
        if is_verbose: print_verbose("Session vector store not initialized. Cannot retrieve.", style="yellow")
        # Should this be an error? Or just return no chunks? Let's return no chunks.
        return {"retrieved_chunks": []}

    if not query:
        if is_verbose: print_verbose("No query provided for retrieval.", style="yellow")
        return {"retrieved_chunks": [], "error": "No query provided for retrieval node."} # Signal error

    retriever_config = get_retriever_config()
    k = retriever_config.get('k', 6) # Number of chunks to retrieve

    if is_verbose: print_verbose(f"Retrieving top {k} chunks for query: '{query}'", style="dim blue")

    try:
        # Option 1: Use the vector store's built-in similarity search
        # This assumes the vector store was initialized with the correct embedding function
        retrieved_chunks: List[Document] = vector_store.similarity_search(query, k=k)

        # Option 2: Explicitly embed query (if store doesn't handle it or different embedding needed)
        # embedding_function = initialize_embedding_model() # Get the embedding func
        # if not embedding_function:
        #     return {"error": "Failed to initialize embedding model for retrieval."}
        # query_embedding = embedding_function.embed_query(query)
        # retrieved_chunks: List[Document] = vector_store.similarity_search_by_vector(query_embedding, k=k)

        if is_verbose:
            print_verbose(f"Retrieved {len(retrieved_chunks)} chunks.", style="green")
            # for i, chunk in enumerate(retrieved_chunks):
            #     print_verbose(f"  Chunk {i+1}: {chunk.metadata.get('url')} (Score: ??)", style="dim") # Score might not be available

        # Store retrieved chunks for the summarizer node
        return {
            "retrieved_chunks": retrieved_chunks,
            "current_query": None, # Clear the query after use
            "error": None
        }

    except Exception as e:
        error_msg = f"Failed to retrieve chunks from session vector store: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "retrieved_chunks": []}


# Example of how to add retriever config to config.yaml
# retriever:
#   k: 6 # Number of chunks to retrieve per query