"""
Handles the initialization and state management of the RAG system using Langchain.

Checks environment variables, loads/creates the Chroma vector store,
handles document loading, link following, metadata processing, and chunking.
"""

import os
import warnings
from pathlib import Path
from typing import Optional, Tuple, List, Set, Dict, Any
from collections import deque

# Langchain Imports
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain.schema import Document

# --- Local Imports ---
from agent.config import get_rag_config
from agent.rag_utils.ingestion import extract_links, is_web_link, resolve_link

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

def is_rag_enabled() -> bool:
    """Checks if RAG is initialized and enabled."""
    global _rag_initialized, _rag_enabled
    if not _rag_initialized:
        initialize_rag() # Attempt initialization if not done yet
    return _rag_enabled

def get_vector_store() -> Optional[Chroma]:
    """Returns the initialized vector store instance, initializing if necessary."""
    global _rag_initialized, _vector_store
    if not _rag_initialized:
        initialize_rag()
    return _vector_store


def initialize_rag(verbose: bool = False) -> None:
    """
    Initializes the RAG system using Langchain: checks env vars, loads/creates
    the Chroma vector store using specified document loaders and embeddings.
    Updates the internal state (_vector_store, _rag_initialized, _rag_enabled).
    """
    global _vector_store, _rag_initialized, _rag_enabled

    if _rag_initialized:
        return # Already initialized

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
        return

    rag_doc_path = Path(rag_doc_path_str)
    if not rag_doc_path.is_dir():
        warnings.warn(f"RAG_DOC_PATH ('{rag_doc_path_str}') is not a valid directory. Disabling RAG.")
        _rag_initialized = True
        return

    if not openai_api_key:
        warnings.warn("OPENAI_API_KEY missing. RAG embedding/querying cannot proceed. Disabling RAG.")
        _rag_initialized = True
        return

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
            loaded_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings,
                collection_name=COLLECTION_NAME
            )
            # Simple check if store seems valid (e.g., has a collection count)
            try:
                 count = loaded_store._collection.count()
                 if verbose: print(f"Successfully loaded store with {count} existing documents.")
                 _vector_store = loaded_store # Assign to global only if load is successful
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
                 return

            # --- Link Following Logic ---
            final_docs: List[Document] = []
            queue: deque[Tuple[Document, int]] = deque([(doc, 0) for doc in initial_docs]) # Queue stores (Document, depth)
            # Use resolved absolute paths for visited file tracking
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
                 return

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
                 return

            # Create Chroma vector store from documents
            if verbose: print(f"Creating Chroma vector store and persisting to: {persist_directory}")
            created_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=persist_directory
            )
            _vector_store = created_store # Assign to global
            if verbose: print("Vector store created successfully.")

        _rag_enabled = True
        _rag_initialized = True

    except Exception as e:
        warnings.warn(f"Failed to initialize Langchain RAG system: {e}")
        _rag_enabled = False
        _rag_initialized = True
        _vector_store = None
        if verbose:
            import traceback
            traceback.print_exc()