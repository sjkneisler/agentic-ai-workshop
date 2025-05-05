"""
Agent module for Retrieval-Augmented Generation (RAG).

This module acts as an interface to the RAG system, delegating
initialization and querying to specialized submodules.
"""

from typing import Tuple, List

# Import the public functions from the new modules within rag_utils
from agent.rag_utils.rag_initializer import initialize_rag, is_rag_enabled
from agent.rag_utils.rag_query import query_vector_store

# You might optionally want to trigger initialization here if needed globally,
# but the current design initializes lazily when query_vector_store is called.
# initialize_rag() # Uncomment if eager initialization is desired

# Expose the query function directly
__all__ = ["query_vector_store", "is_rag_enabled", "initialize_rag"]

# No other code needed here, the logic lives in the imported modules.