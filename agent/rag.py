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
            max_depth = rag_config.get('link_follow_depth', 3) # Default internal depth
            follow_external = rag_config.get('rag_follow_external_links', False) # Get external link setting
            if verbose:
                print(f"Max internal link follow depth: {max_depth}")
                print(f"Follow external web links: {follow_external}")

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
            # Use URLs for visited web link tracking
            visited_urls: Set[str] = set()

            processed_files_count = 0
            processed_urls_count = 0
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
                if current_file_path in visited_files or (max_depth > 0 and current_depth >= max_depth): # Only check depth if max_depth > 0
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

                # Extract links only if depth allows further traversal
                if max_depth == 0 or current_depth < max_depth:
                    links = extract_links(current_doc.page_content)
                    for _link_text, link_target in links:
                        # --- Handle Web Links ---
                        if is_web_link(link_target):
                            if follow_external and link_target not in visited_urls:
                                if verbose: print(f"    Attempting to fetch external link: {link_target}")
                                try:
                                    response = requests.get(link_target, timeout=10, headers={'User-Agent': 'RooResearchAgent/1.0'}) # Added User-Agent
                                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                                    # Basic HTML parsing with BeautifulSoup
                                    soup = BeautifulSoup(response.content, 'html.parser')

                                    # Remove script and style elements
                                    for script_or_style in soup(["script", "style"]):
                                        script_or_style.decompose()

                                    # Get text, strip leading/trailing whitespace, join lines
                                    body_text = soup.get_text(separator='\n', strip=True)

                                    if body_text:
                                        web_doc = Document(
                                            page_content=body_text,
                                            metadata={'source': link_target, 'title': soup.title.string if soup.title else link_target} # Use URL as source
                                        )
                                        final_docs.append(web_doc)
                                        visited_urls.add(link_target)
                                        processed_urls_count += 1
                                        if verbose: print(f"      Successfully fetched and parsed content from: {link_target}")
                                    else:
                                        if verbose: print(f"      No text content extracted from: {link_target}")

                                except requests.exceptions.RequestException as req_err:
                                    warnings.warn(f"Failed to fetch external link {link_target}: {req_err}")
                                except Exception as parse_err:
                                     warnings.warn(f"Failed to parse content from {link_target}: {parse_err}")
                                finally:
                                     visited_urls.add(link_target) # Add even if failed to prevent retries

                            elif verbose and link_target in visited_urls:
                                 print(f"    Skipping already visited external link: {link_target}")
                            elif verbose and not follow_external:
                                 print(f"    Skipping external link (disabled): {link_target}")
                            continue # Move to next link after handling web link

                        # --- Handle Internal Links (Existing Logic) ---
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
        
                    if verbose: print(f"--- Finished Link Following: Processed {processed_files_count} unique files and {processed_urls_count} unique web URLs. Total documents for splitting: {len(final_docs)} ---")
        
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

    Args:
        query: The query string to search for in the vector store.
        n_results: The maximum number of results to retrieve (passed as 'k').
        verbose: Flag for detailed output.

    Returns:
        A tuple containing:
        - A string with relevant context retrieved from the store.
        - A list of unique source file paths from which the context was retrieved.
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

    rag_context = ""
    rag_source_paths: List[str] = []

    try:
        # Create a retriever
        retriever = vector_store.as_retriever(search_kwargs={'k': n_results})

        # Retrieve relevant documents
        retrieved_docs: List[Document] = retriever.invoke(query)

        if retrieved_docs:
            # Concatenate document content
            rag_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

            # Extract unique source paths from metadata
            unique_sources = set()
            for doc in retrieved_docs:
                if doc.metadata and isinstance(doc.metadata, dict) and 'source' in doc.metadata:
                    source_val = str(doc.metadata['source'])
                    # Check if it's a web link (simple check)
                    if source_val.startswith('http://') or source_val.startswith('https://'):
                        unique_sources.add(source_val) # Add URL directly
                    else:
                        # Try to make local paths relative
                        try:
                             rag_doc_path = Path(os.getenv("RAG_DOC_PATH", "."))
                             source_path = Path(source_val)
                             # Check if the source path is absolute or relative to the CWD
                             # If it's not inside the RAG_DOC_PATH, just use the original string
                             if source_path.is_absolute() or source_path.resolve().is_relative_to(Path.cwd()):
                                 relative_path = str(source_path.relative_to(rag_doc_path))
                                 unique_sources.add(relative_path)
                             else:
                                 unique_sources.add(source_val) # Use original if not relative to RAG path
                        except (ValueError, TypeError, OSError): # Added OSError for path issues
                             unique_sources.add(source_val) # Fallback to original path string on error
            rag_source_paths = sorted(list(unique_sources))

            if verbose:
                print(f"Retrieved {len(retrieved_docs)} document chunks.")
                print(f"Sources: {rag_source_paths}")
        elif verbose:
            print("No relevant documents found in vector store for this query.")

    except Exception as e:
        warnings.warn(f"Error querying Langchain vector store: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        rag_context = ""
        rag_source_paths = []

    return rag_context, rag_source_paths

# Note: embed_corpus function is removed as Langchain handles the process.