"""
LangGraph node for chunking fetched HTML content and adding it to a session vector store.
"""
import warnings
from typing import Dict, Any, List, Optional

# State and Config
from agent.state import AgentState
from agent.config import get_embedding_config # Assuming config for embedding model exists

# LangChain components
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma # Using Chroma for in-memory store
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document

# Shared Utilities
from agent.utils import print_verbose, OPENAI_AVAILABLE, count_tokens

# --- Helper Functions ---

def _initialize_session_store(embedding_function) -> Optional[VectorStore]:
    """Initializes an in-memory Chroma vector store."""
    try:
        # In-memory Chroma requires a collection name but doesn't persist unless specified
        # Using a unique name per run might be safer if Chroma has global state issues,
        # but a fixed name should be fine for ephemeral use.
        vector_store = Chroma(
            collection_name="session_store",
            embedding_function=embedding_function
            # persist_directory=None # Ensure it's in-memory
        )
        # print_verbose("Initialized new in-memory Chroma session vector store.", style="dim blue")
        return vector_store
    except Exception as e:
        warnings.warn(f"Failed to initialize Chroma session vector store: {e}")
        return None

def _get_embedding_function():
    """Initializes the embedding function based on config."""
    if not OPENAI_AVAILABLE:
        warnings.warn("OpenAI library not available. Cannot create embeddings.")
        return None
    
    embedding_config = get_embedding_config()
    model_name = embedding_config.get('model', 'text-embedding-3-small') # Default embedding model
    
    try:
        # print_verbose(f"Initializing embedding model: {model_name}", style="dim blue")
        return OpenAIEmbeddings(model=model_name)
    except Exception as e:
        warnings.warn(f"Failed to initialize OpenAIEmbeddings: {e}")
        return None

# --- LangGraph Node ---

def chunk_and_embed_node(state: AgentState) -> Dict[str, Any]:
    """
    Chunks HTML documents from state['fetched_docs'], embeds them,
    and adds them to the state['session_vector_store'].
    Initializes the vector store if it doesn't exist.
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"):
        if is_verbose: print_verbose("Skipping chunk/embed due to previous error.", style="yellow")
        return {}
    
    if is_verbose: print_verbose("Entering Chunk & Embed Node", style="magenta")

    fetched_docs = state.get('fetched_docs', [])
    if not fetched_docs:
        if is_verbose: print_verbose("No fetched documents to chunk and embed.", style="dim blue")
        return {} # Nothing to do

    # 1. Initialize Embeddings and Vector Store (if needed)
    embedding_function = _get_embedding_function()
    if not embedding_function:
        return {"error": "Failed to initialize embedding function."}

    vector_store = state.get('session_vector_store')
    if not vector_store:
        vector_store = _initialize_session_store(embedding_function)
        if not vector_store:
            return {"error": "Failed to initialize session vector store."}
        if is_verbose: print_verbose("Initialized new session vector store.", style="dim blue")
    elif is_verbose:
         print_verbose("Using existing session vector store.", style="dim blue")


    # 2. Configure Text Splitter for HTML
    # Adjust chunk_size and overlap based on embedding model and desired context length
    # Using smaller chunks as suggested in the plan (e.g., 384 tokens)
    # Note: Token count is approximate with character splitters.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, # Characters, roughly maps to ~250-384 tokens
        chunk_overlap=100, # Character overlap
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", " ", "", "<p>", "<h1>", "<h2>", "<h3>", "<li>"] # HTML tags as separators
    )

    # 3. Process each fetched document
    all_chunks_to_add: List[Document] = []
    total_chunks_processed = 0
    for doc_data in fetched_docs:
        if 'error' in doc_data or not doc_data.get('html'):
            if is_verbose: print_verbose(f"Skipping document due to fetch error or missing HTML: {doc_data.get('url', 'N/A')}", style="yellow")
            continue

        url = doc_data['url']
        title = doc_data['title']
        html_content = doc_data['html']

        if is_verbose: print_verbose(f"Chunking content from: {url}", style="dim blue")

        try:
            # Split the HTML content
            chunks = splitter.split_text(html_content)
            
            # Create Document objects with metadata for each chunk
            for i, chunk_text in enumerate(chunks):
                metadata = {
                    "url": url,
                    "title": title,
                    "chunk_index": i, # Simple index, could add start/end char if needed
                    # Add other relevant metadata if available, e.g., headings
                }
                # Create LangChain Document object
                chunk_doc = Document(page_content=chunk_text, metadata=metadata)
                all_chunks_to_add.append(chunk_doc)
            
            total_chunks_processed += len(chunks)
            if is_verbose: print_verbose(f"  -> Created {len(chunks)} chunks.", style="dim blue")

        except Exception as e:
            warnings.warn(f"Failed to split text for {url}: {e}")
            if is_verbose: print_verbose(f"Error splitting text for {url}: {e}", style="red")


    # 4. Add all collected chunks to the vector store IN BATCHES
    if all_chunks_to_add:
        max_tokens_per_batch = 250000 # Stay safely below the 300k limit
        current_batch: List[Document] = []
        current_batch_tokens = 0
        total_added_count = 0

        if is_verbose: print_verbose(f"Preparing to add {len(all_chunks_to_add)} chunks in batches (max ~{max_tokens_per_batch} tokens/batch)...", style="dim blue")

        for i, chunk_doc in enumerate(all_chunks_to_add):
            # Estimate tokens for the current chunk
            try:
                # Use the imported count_tokens utility
                chunk_tokens = count_tokens(chunk_doc.page_content)
            except Exception:
                chunk_tokens = len(chunk_doc.page_content) // 3 # Rough fallback estimate

            # Check if adding this chunk exceeds the batch limit
            if current_batch and (current_batch_tokens + chunk_tokens > max_tokens_per_batch):
                # Process the current batch before adding the new chunk
                if is_verbose: print_verbose(f"  Adding batch of {len(current_batch)} chunks ({current_batch_tokens} tokens)...", style="dim blue")
                try:
                    vector_store.add_documents(current_batch)
                    total_added_count += len(current_batch)
                    if is_verbose: print_verbose(f"  Batch added successfully. Total added: {total_added_count}", style="green")
                except Exception as e:
                    error_msg = f"Failed to add batch ({len(current_batch)} docs) to session vector store: {e}"
                    warnings.warn(error_msg)
                    if is_verbose: print_verbose(f"  Error adding batch: {e}", style="bold red")
                    # Optionally return error here, or just warn and continue? Let's warn and continue for now.
                    # return {"error": error_msg, "session_vector_store": vector_store}

                # Start a new batch
                current_batch = [chunk_doc]
                current_batch_tokens = chunk_tokens
            else:
                # Add chunk to the current batch
                current_batch.append(chunk_doc)
                current_batch_tokens += chunk_tokens

            # Process the last batch if this is the final chunk
            if i == len(all_chunks_to_add) - 1 and current_batch:
                 if is_verbose: print_verbose(f"  Adding final batch of {len(current_batch)} chunks ({current_batch_tokens} tokens)...", style="dim blue")
                 try:
                     vector_store.add_documents(current_batch)
                     total_added_count += len(current_batch)
                     if is_verbose: print_verbose(f"  Final batch added successfully. Total added: {total_added_count}", style="green")
                 except Exception as e:
                     error_msg = f"Failed to add final batch ({len(current_batch)} docs) to session vector store: {e}"
                     warnings.warn(error_msg)
                     if is_verbose: print_verbose(f"  Error adding final batch: {e}", style="bold red")
                     # Optionally return error here
                     # return {"error": error_msg, "session_vector_store": vector_store}

        # Original error handling block removed as batching handles errors internally now.

    # 5. Update state: Store the vector_store, clear fetched_docs, PRESERVE query_for_retrieval
    # Note: We modify the store in place, but need to ensure the state dict reflects it.
    # Clear fetched_docs as they have been processed.
    return {
        "session_vector_store": vector_store,
        "fetched_docs": [], # Clear the processed docs
        "query_for_retrieval": state.get("query_for_retrieval"), # Preserve the retrieval query
        "error": None
    }

# Example of how to add embedding config to config.yaml (if not already present)
# embedding:
#   model: text-embedding-3-small