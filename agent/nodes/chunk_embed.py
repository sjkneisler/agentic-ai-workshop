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


    # 4. Add all collected chunks to the vector store
    if all_chunks_to_add:
        if is_verbose: print_verbose(f"Adding {len(all_chunks_to_add)} chunks to session vector store...", style="dim blue")
        try:
            # Use add_documents for batch efficiency
            vector_store.add_documents(all_chunks_to_add)
            if is_verbose: print_verbose("Successfully added chunks to vector store.", style="green")
        except Exception as e:
            error_msg = f"Failed to add documents to session vector store: {e}"
            warnings.warn(error_msg)
            if is_verbose: print_verbose(error_msg, style="bold red")
            # Decide if this is a fatal error for the node
            return {"error": error_msg, "session_vector_store": vector_store} # Return store even if add failed partially?

    # 5. Update state: Store the vector_store, clear fetched_docs
    # Note: We modify the store in place, but need to ensure the state dict reflects it.
    # Clear fetched_docs as they have been processed.
    return {
        "session_vector_store": vector_store,
        "fetched_docs": [], # Clear the processed docs
        "error": None
    }

# Example of how to add embedding config to config.yaml (if not already present)
# embedding:
#   model: text-embedding-3-small