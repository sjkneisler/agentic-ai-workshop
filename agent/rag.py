"""
Agent module for Retrieval-Augmented Generation (RAG) using Langchain.

Loads documents, splits them, embeds them using OpenAI, stores them in
a Chroma vector store, and retrieves relevant context based on a query.
Requires RAG_DOC_PATH and OPENAI_API_KEY environment variables.
"""

import os
import warnings
from pathlib import Path
from typing import Optional, Tuple, List, Set, Dict, Any # Added Set, Dict, Any
from collections import deque # Added deque
import requests # Added for web fetching
from bs4 import BeautifulSoup # Added for HTML parsing

# Langchain Imports
from langchain_chroma import Chroma # Updated import
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredMarkdownLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter # Old splitter
from langchain_experimental.text_splitter import SemanticChunker # New splitter
from langchain.schema import Document # For type hinting

# --- Local Imports ---
from agent.config import get_rag_config # Added config import
from agent.rag_utils.ingestion import extract_links, is_web_link, resolve_link # Added utils import

# --- Constants ---
RAG_STORE_PATH = ".rag_store"
COLLECTION_NAME = "research_docs"
# Define supported extensions and corresponding loaders
LOADER_MAPPING = {
    ".md": UnstructuredMarkdownLoader,
    ".txt": TextLoader,
}

# --- Globals / State ---
# Store the Langchain Chroma vector store instance
_vector_store: Optional[Chroma] = None
_rag_initialized = False
_rag_enabled = False

def _initialize_rag(verbose: bool = False) -> Optional[Chroma]:
    """
    Initializes the RAG system using Langchain: checks env vars, loads/creates
    the Chroma vector store using specified document loaders and embeddings.

    Returns:
        The Langchain Chroma vector store instance if RAG is enabled and
        initialized, otherwise None.
    """
    global _vector_store, _rag_initialized, _rag_enabled

    if _rag_initialized:
        # Return existing state if already initialized
        return _vector_store if _rag_enabled else None

    # Reset state for initialization attempt
    _rag_initialized = False
    _rag_enabled = False
    _vector_store = None

    if verbose:
        print("--- Initializing RAG System (Langchain) ---")

    # --- Environment Variable Checks ---
    rag_doc_path_str = os.getenv("RAG_DOC_PATH")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not rag_doc_path_str:
        if verbose: print("RAG_DOC_PATH not set. Skipping RAG initialization.")
        _rag_initialized = True
        return None

    rag_doc_path = Path(rag_doc_path_str)
    if not rag_doc_path.is_dir():
        warnings.warn(f"RAG_DOC_PATH ('{rag_doc_path_str}') is not a valid directory. Disabling RAG.")
        _rag_initialized = True
        return None

    if not openai_api_key:
        warnings.warn("OPENAI_API_KEY missing. RAG embedding/querying cannot proceed. Disabling RAG.")
        _rag_initialized = True
        return None

    if verbose:
        print(f"RAG enabled. Document path: {rag_doc_path}")
        print(f"Using Chroma persistent path: {RAG_STORE_PATH}")

    try:
        # --- Initialize Embeddings ---
        embeddings = OpenAIEmbeddings(api_key=openai_api_key) # Consider model_name if needed

        # --- Load or Create Vector Store ---
        persist_directory = str(Path(RAG_STORE_PATH).resolve()) # Use absolute path

        if Path(persist_directory).exists():
            if verbose: print(f"Loading existing Chroma vector store from: {persist_directory}")
            _vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings,
                collection_name=COLLECTION_NAME
            )
            # Simple check if store seems valid (e.g., has a collection count)
            try:
                 count = _vector_store._collection.count()
                 if verbose: print(f"Successfully loaded store with {count} existing documents.")
            except Exception as load_err:
                 warnings.warn(f"Error verifying loaded vector store: {load_err}. Will attempt to rebuild.")
                 _vector_store = None # Force rebuild
        else:
             if verbose: print("Existing vector store not found. Creating a new one.")
             _vector_store = None # Ensure it's None before creation attempt

        # If store doesn't exist or failed to load, create it
        if _vector_store is None:
            if verbose: print(f"--- Starting Document Loading & Link Following ---")

            # --- Configuration for Link Following ---
            rag_config = get_rag_config()
            # Renamed config key for clarity
            initial_max_depth = rag_config.get('rag_initial_link_follow_depth', 3)
            # External link following is now done at query time
            if verbose:
                print(f"Max internal DOCUMENT link follow depth during indexing: {initial_max_depth}")

            # --- Initial Document Load ---
            initial_docs: List[Document] = []
            if verbose: print(f"Loading initial documents from: {rag_doc_path}")
            for ext, LoaderClass in LOADER_MAPPING.items():
                loader = DirectoryLoader(
                    str(rag_doc_path),
                    glob=f"**/*{ext}",
                    loader_cls=LoaderClass,
                    use_multithreading=True, # Can keep this for initial load
                    show_progress=verbose,
                    # loader_kwargs={'encoding': 'utf-8'} # Example if needed
                )
                try:
                    loaded = loader.load()
                    if verbose: print(f"  Loaded {len(loaded)} initial documents with extension '{ext}'")
                    initial_docs.extend(loaded)
                except Exception as load_err:
                    warnings.warn(f"Error loading initial files with extension '{ext}': {load_err}")
                    if verbose: import traceback; traceback.print_exc()

            if not initial_docs:
                 warnings.warn("No initial documents loaded. RAG cannot be initialized.")
                 _rag_initialized = True
                 return None

            # --- Link Following Logic ---
            final_docs: List[Document] = []
            queue: deque[Tuple[Document, int]] = deque([(doc, 0) for doc in initial_docs]) # Queue stores (Document, depth)
            # Use resolved absolute paths for visited file tracking
            visited_files: Set[Path] = set()
            # Web fetching and related tracking removed from initialization
            visited_files: Set[Path] = set()

            processed_files_count = 0
            while queue:
                current_doc, current_depth = queue.popleft()

                # Ensure metadata and source exist
                if not current_doc.metadata or 'source' not in current_doc.metadata:
                     warnings.warn(f"Document missing source metadata, skipping link following for it: {current_doc.page_content[:100]}...")
                     final_docs.append(current_doc) # Add doc even if metadata missing
                     continue

                try:
                    current_file_path = Path(current_doc.metadata['source']).resolve()
                except Exception as path_err:
                     warnings.warn(f"Could not resolve source path '{current_doc.metadata['source']}', skipping link following: {path_err}")
                     final_docs.append(current_doc)
                     continue

                # Skip if already processed or depth exceeded
                # Use initial_max_depth for document traversal during indexing
                if current_file_path in visited_files or (initial_max_depth > 0 and current_depth >= initial_max_depth):
                    # Still add the document itself to the final list if not already added at this depth
                    # Check if this exact doc object is already there (might be redundant but safe)
                    if current_doc not in final_docs:
                         final_docs.append(current_doc)
                    continue

                visited_files.add(current_file_path)
                final_docs.append(current_doc) # Add the current document to the final list
                processed_files_count += 1

                if verbose:
                    try: log_path = current_file_path.relative_to(rag_doc_path)
                    except ValueError: log_path = current_file_path
                    print(f"  [Depth {current_depth}] Processing links in: {log_path}")

                # Extract internal links only if depth allows further document traversal
                if initial_max_depth == 0 or current_depth < initial_max_depth:
                    links = extract_links(current_doc.page_content)
                    for _link_text, link_target in links:
                        # Skip web links during initial document loading
                        if is_web_link(link_target):
                            continue

                        # --- Handle Internal Links (Document Loading) ---
                        resolved_path = resolve_link(link_target, current_file_path, rag_doc_path)

                        # Check if resolved, is a file, is supported type, and not visited (file)
                        if (resolved_path and
                            resolved_path.is_file() and
                            resolved_path.suffix.lower() in LOADER_MAPPING and
                            resolved_path not in visited_files):

                            # Avoid adding duplicates to the queue
                            if any(item[0].metadata.get('source') and Path(item[0].metadata['source']).resolve() == resolved_path for item in queue):
                                continue

                            # Load the linked document
                            try:
                                LinkLoaderClass = LOADER_MAPPING[resolved_path.suffix.lower()]
                                link_loader = LinkLoaderClass(str(resolved_path))
                                linked_docs = link_loader.load()
                                if linked_docs:
                                    if verbose: print(f"    [Depth {current_depth+1}] Following link to load: {resolved_path.relative_to(rag_doc_path)}")
                                    for new_doc in linked_docs:
                                        # Add source if loader didn't (some might not)
                                        if 'source' not in new_doc.metadata:
                                             new_doc.metadata['source'] = str(resolved_path)
                                        queue.append((new_doc, current_depth + 1))
                                else:
                                     if verbose: print(f"    Link resolved but loader returned no docs for: {resolved_path}")
                            except Exception as link_load_err:
                                warnings.warn(f"Error loading linked file {resolved_path}: {link_load_err}")
        
                    if verbose: print(f"--- Finished Initial Document Link Following: Processed {processed_files_count} unique local files. Total documents collected: {len(final_docs)} ---")

                    # --- Add Internal Link Metadata BEFORE Chunking ---
                    if verbose: print("--- Adding internal link metadata to documents ---")
                    for doc in final_docs:
                        if 'source' in doc.metadata:
                            try:
                                doc_path = Path(doc.metadata['source']).resolve()
                                internal_links = extract_links(doc.page_content)
                                linked_paths = []
                                for _, target in internal_links:
                                    if not is_web_link(target):
                                        resolved = resolve_link(target, doc_path, rag_doc_path)
                                        if resolved and resolved.is_file():
                                            linked_paths.append(str(resolved)) # Store absolute path string
                                if linked_paths:
                                    # Serialize list into a single string for Chroma compatibility
                                    doc.metadata['internal_linked_paths_str'] = ";;".join(linked_paths)
                                    if verbose: print(f"  Added {len(linked_paths)} internal link targets (as string) to metadata for: {doc_path.relative_to(rag_doc_path)}")
                            except Exception as meta_err:
                                warnings.warn(f"Error processing links for metadata in {doc.metadata.get('source', 'Unknown')}: {meta_err}")
                        else:
                             warnings.warn(f"Skipping link metadata addition for doc missing source: {doc.page_content[:100]}...")


                    # --- Split all collected documents ---
            if not final_docs:
                 warnings.warn("No documents available after loading and link following. RAG cannot be initialized.")
                 _rag_initialized = True
                 return None

            text_splitter = SemanticChunker(embeddings)
            splits: List[Document] = []
            if verbose: print(f"Splitting {len(final_docs)} documents into semantic chunks...")
            # Process document by document to preserve metadata
            for doc in final_docs:
                 try:
                     # SemanticChunker expects a list of texts
                     semantic_chunks = text_splitter.create_documents([doc.page_content])
                     # Add original metadata back to the new chunks
                     for chunk in semantic_chunks:
                         chunk.metadata = doc.metadata.copy() # Copy original metadata
                     splits.extend(semantic_chunks)
                 except Exception as split_err:
                     warnings.warn(f"Error splitting document {doc.metadata.get('source', 'Unknown')}: {split_err}")

            if verbose: print(f"Generated {len(splits)} semantic chunks.")

            if not splits:
                 warnings.warn("No chunks generated after splitting. RAG cannot be initialized.")
                 _rag_initialized = True
                 return None

            # Create Chroma vector store from documents
            if verbose: print(f"Creating Chroma vector store and persisting to: {persist_directory}")
            _vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=persist_directory
            )
            if verbose: print("Vector store created successfully.")

        _rag_enabled = True
        _rag_initialized = True
        return _vector_store

    except Exception as e:
        warnings.warn(f"Failed to initialize Langchain RAG system: {e}")
        _rag_enabled = False
        _rag_initialized = True
        _vector_store = None
        if verbose:
            import traceback
            traceback.print_exc()
        return None


def query_vector_store(query: str, n_results: int = 3, verbose: bool = False) -> Tuple[str, List[str]]:
    """
    Queries the Langchain vector store for context relevant to the query.
    Optionally traverses internal links between retrieved chunks and fetches
    external web links found in the collected context.

    Args:
        query: The query string to search for in the vector store.
        n_results: The maximum number of results to retrieve (passed as 'k').
        verbose: Flag for detailed output.

    Returns:
        A tuple containing:
        - A string with relevant context from initial retrieval, internal chunk traversal, and external web fetching.
        - A list of unique source file paths/URLs contributing to the context.
        Returns ("", []) if RAG is disabled, not initialized, or no context found.
    """
    if verbose:
        print("--- Querying Vector Store (Langchain RAG) ---")
        print(f"Querying for: '{query}' (k={n_results})")

    # Ensure RAG is initialized
    vector_store = _initialize_rag(verbose)

    if not _rag_enabled or not vector_store:
        if verbose: print("RAG is not enabled or vector store failed to initialize. Skipping query.")
        return "", []

    final_context_parts: List[str] = []
    final_sources: Set[str] = set()
    collected_chunks: Dict[str, Document] = {} # Use dict to store chunks by ID for easy lookup

    try:
        # --- Step 1: Initial Retrieval ---
        if verbose: print(f"--- Performing initial retrieval (k={n_results}) ---")
        retriever = vector_store.as_retriever(search_kwargs={'k': n_results})
        initial_chunks: List[Document] = retriever.invoke(query)

        if not initial_chunks:
            if verbose: print("No relevant documents found in initial retrieval.")
            return "", []

        for chunk in initial_chunks:
             # Assuming Chroma adds a unique ID or we can generate one
             # Langchain docs often have IDs, let's assume vector_store assigns them or they exist in metadata
             # If not, we might need to hash content or use index. Fallback needed.
             chunk_id = chunk.metadata.get('id', str(hash(chunk.page_content))) # Example ID generation
             if chunk_id not in collected_chunks:
                 collected_chunks[chunk_id] = chunk

        if verbose: print(f"Retrieved {len(collected_chunks)} initial unique chunks.")

        # --- Step 2: Internal Chunk Link Traversal ---
        rag_config = get_rag_config()
        follow_internal_chunks = rag_config.get('rag_follow_internal_chunk_links', False)
        internal_link_depth = rag_config.get('rag_internal_link_depth', 1)
        internal_link_k = rag_config.get('rag_internal_link_k', 2)

        if follow_internal_chunks and internal_link_depth > 0:
            if verbose: print(f"--- Traversing internal chunk links (max_depth={internal_link_depth}, k={internal_link_k}) ---")
            queue: deque[Tuple[str, int]] = deque([(cid, 0) for cid in collected_chunks]) # Queue of (chunk_id, depth)
            visited_chunk_ids_for_traversal = set(collected_chunks.keys()) # Track visited during traversal

            while queue:
                current_chunk_id, current_depth = queue.popleft()

                if current_depth >= internal_link_depth:
                    continue

                current_chunk = collected_chunks.get(current_chunk_id)
                # Check for the serialized string metadata key
                if not current_chunk or 'internal_linked_paths_str' not in current_chunk.metadata:
                    continue

                # Deserialize the string back into a list
                linked_paths_str = current_chunk.metadata['internal_linked_paths_str']
                if not linked_paths_str or not isinstance(linked_paths_str, str):
                    continue # Skip if empty or not a string
                linked_paths = linked_paths_str.split(";;")

                if verbose: print(f"  [Depth {current_depth}] Chunk from '{current_chunk.metadata.get('source', 'Unknown')}' links to {len(linked_paths)} files.")

                for target_path_str in linked_paths:
                    if verbose: print(f"    Searching for chunks related to query in linked file: {target_path_str}")
                    try:
                        # Perform filtered search using the *original query*
                        linked_retriever = vector_store.as_retriever(
                            search_kwargs={'k': internal_link_k, 'filter': {'source': target_path_str}}
                        )
                        found_linked_chunks = linked_retriever.invoke(query)

                        if verbose: print(f"      Found {len(found_linked_chunks)} chunks in {target_path_str}.")

                        for linked_chunk in found_linked_chunks:
                            linked_chunk_id = linked_chunk.metadata.get('id', str(hash(linked_chunk.page_content)))
                            if linked_chunk_id not in visited_chunk_ids_for_traversal:
                                visited_chunk_ids_for_traversal.add(linked_chunk_id)
                                collected_chunks[linked_chunk_id] = linked_chunk # Add to overall collection
                                queue.append((linked_chunk_id, current_depth + 1))
                                if verbose: print(f"        Added linked chunk (ID: {linked_chunk_id}) from {target_path_str} to results and queue.")

                    except Exception as search_err:
                        warnings.warn(f"Error performing filtered search for linked path {target_path_str}: {search_err}")

        # --- Step 3: Extract Content and External Links from ALL Collected Chunks ---
        if verbose: print(f"--- Processing {len(collected_chunks)} total collected chunks (initial + linked) ---")
        external_links_to_fetch = set()
        rag_doc_path_env = os.getenv("RAG_DOC_PATH", ".") # Get base path for relative sources

        for chunk_id, chunk in collected_chunks.items():
            final_context_parts.append(chunk.page_content)
            # Add source
            if chunk.metadata and 'source' in chunk.metadata:
                 source_val = str(chunk.metadata['source'])
                 # Try to make local paths relative
                 try:
                     source_path = Path(source_val)
                     # Check if it's absolute or resolve relative to CWD before making relative to RAG path
                     if source_path.is_absolute():
                          relative_path = str(source_path.relative_to(Path(rag_doc_path_env).resolve()))
                          final_sources.add(relative_path)
                     elif source_path.resolve().is_relative_to(Path(rag_doc_path_env).resolve()):
                          relative_path = str(source_path.resolve().relative_to(Path(rag_doc_path_env).resolve()))
                          final_sources.add(relative_path)
                     else:
                          final_sources.add(source_val) # Use original if not relative to RAG path
                 except (ValueError, TypeError, OSError):
                      final_sources.add(source_val) # Fallback on error
            # Extract external links
            links_in_chunk = extract_links(chunk.page_content)
            for _, link_target in links_in_chunk:
                if is_web_link(link_target):
                    external_links_to_fetch.add(link_target)

        # --- Step 4: Fetch External Links if Enabled ---
        follow_external = rag_config.get('rag_follow_external_links', False)
        fetched_web_sources = set()

        if follow_external and external_links_to_fetch:
            if verbose: print(f"--- Fetching {len(external_links_to_fetch)} unique external links found in collected chunks ---")
            for link_target in external_links_to_fetch:
                if verbose: print(f"  Fetching: {link_target}")
                try:
                    response = requests.get(link_target, timeout=10, headers={'User-Agent': 'RooResearchAgent/1.0'})
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.decompose()
                    body_text = soup.get_text(separator='\n', strip=True)

                    if body_text:
                        fetched_content = f"--- Content from {link_target} ---\n{body_text}\n--- End Content from {link_target} ---"
                        final_context_parts.append(fetched_content)
                        fetched_web_sources.add(link_target)
                        if verbose: print(f"    Successfully fetched and parsed.")
                    else:
                        if verbose: print(f"    No text content extracted.")
                except requests.exceptions.RequestException as req_err:
                    warnings.warn(f"Failed to fetch external link {link_target} during query: {req_err}")
                except Exception as parse_err:
                     warnings.warn(f"Failed to parse content from {link_target} during query: {parse_err}")

            final_sources.update(fetched_web_sources) # Add successfully fetched URLs to sources

        # --- Step 5: Combine and Return ---
        final_rag_context = "\n\n".join(final_context_parts)
        final_rag_source_paths = sorted(list(final_sources))

        if verbose:
             print(f"--- Final RAG Results ---")
             print(f"Total Chunks Contributed (Initial + Linked): {len(collected_chunks)}")
             print(f"External URLs Fetched: {len(fetched_web_sources)}")
             print(f"Final Sources: {final_rag_source_paths}")

        return final_rag_context, final_rag_source_paths

    except Exception as e:
        warnings.warn(f"Error during RAG query processing: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        # Return empty results on error
        return "", []

# Note: embed_corpus function is removed as Langchain handles the process.