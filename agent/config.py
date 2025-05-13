"""
Configuration loading module.

Reads settings from config.yaml and provides them to other agent modules.
Handles default values if the config file is missing or incomplete.
"""

import yaml
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    'synthesizer': {
        'model': 'o4-mini', # Model for final answer synthesis
        'system_prompt': """
You are a research assistant. Synthesize a comprehensive and well-structured answer to the user's question based ONLY on the provided curated research notes.
Do not use a preamble or postamble - only output the synthesized response.
Use the Answer Outline provided to fill in your content - DO NOT deviate from that structure.
You MAY add more sub-headers to the Answer Outline as is appropriate to structure your response.
**Crucially, preserve the full source citation tags exactly as they appear in the notes (e.g., [Source URL='...', Title='...', Chunk=...]). Do NOT summarize or alter these tags.**
Structure your answer clearly. Do not invent facts or information not present in the notes.
""".strip(),
        'temperature': 1
    },
    'search': {
        'num_results': 5 # Number of results from Serper search
    },
    'rag': { # Kept for potential future use or integration
        'rag_initial_link_follow_depth': 3,
        'rag_follow_external_links': True,
        'rag_follow_internal_chunk_links': True,
        'rag_internal_link_depth': 1,
        'rag_internal_link_k': 2
    },
    'reasoner': { # Config for the decision-making LLM
        'model': 'o4-mini',
        'temperature': 1,
        'max_iterations': 20, # Max cycles of search/fetch/retrieve/summarize
        'system_prompt': """
You are the reasoning core of a research agent. Your goal is to decide the single next step to fulfill the research plan based on the information gathered so far.

Analyze the User's Question, the Research Plan Outline, and the Notes gathered.
Consider the Recent Search Results if deciding to fetch a URL.

Possible Next Actions:
1.  SEARCH: If more general information or starting points are needed for an outline topic. Provide a concise search query relevant to an uncovered part of the outline.
2.  FETCH: If a specific URL from recent search results seems highly promising for an outline topic. Provide the exact URL to fetch. Only choose FETCH if search results are available.
3.  RETRIEVE_CHUNKS: If you need to consult information already fetched and stored (e.g., to check coverage on a topic before searching again). Provide a concise query for the vector store relevant to an outline topic.
4.  CONSOLIDATE: If you believe enough information has been gathered across all outline points and notes should be prepared for the final answer. Choose this if the notes adequately cover the outline.
5.  STOP: If the plan seems fulfilled by the notes, or if you are stuck after trying different actions.

Current Iteration: {iteration}/{max_iterations}

Provide your decision in the following format ONLY:
Action: [SEARCH|FETCH|RETRIEVE_CHUNKS|CONSOLIDATE|STOP]
Argument: [Your search query | URL to fetch | Your vector store query | None]
""".strip()
    },
    # --- New Sections for Deep Research Loop ---
    'embedding': {
        'model': 'text-embedding-3-small' # Default model for chunk embeddings
    },
    'summarizer': {
        'model': 'gpt-4o-mini', # Cheaper model for summarizing chunks
        'temperature': 0.0,
        'system_prompt': "You are an efficient assistant. Summarize the key facts from the following passages in bullet points (maximum 120 words total). Focus on information relevant to the original query. Keep exact numbers/quotes where possible. **Cite each claim meticulously using the EXACT source citation tag provided with each passage, like [Source URL='...', Title='...', Chunk=...]. Do NOT alter the citation tag format.**"
    },
    'retriever': {
        'k': 6 # Number of chunks to retrieve from session store per query
    },
    'consolidator': {
        'rerank': True, # Whether to re-rank notes before synthesis
        'top_n': 20, # Max number of notes to pass to synthesizer
        'cross_encoder_model': 'cross-encoder/ms-marco-MiniLM-L-12-v2' # Model for re-ranking
    }
    , # Add comma here
    'clarifier': { # Added defaults for clarifier
        'clarification_model': 'gpt-4o-mini', # Model for checking if clarification is needed
        'refinement_model': 'gpt-4o-mini',    # Model for refining question and generating outline
        'clarification_temperature': 0.2,
        'refinement_temperature': 0.5
    },
    'graph': { # Configuration for the LangGraph execution
        'recursion_limit': 100 # Default recursion limit for the graph
    },
    'prompt_logging': { # Configuration for prompt logging
        'enabled': False, # Set to True to enable prompt logging
        'log_file_path': "logs/prompt_logs.jsonl" # Path to save prompt logs
    },
    'openai_pricing': { # Default OpenAI API pricing
        'models': {
            "gpt-o4-mini": {
                "input_cost_per_million_tokens": 0.15,
                "output_cost_per_million_tokens": 0.60
            },
            "gpt-4-turbo": {
                "input_cost_per_million_tokens": 10.00,
                "output_cost_per_million_tokens": 30.00
            },
            "text-embedding-3-small": {
                "cost_per_million_tokens": 0.02
            },
            "text-embedding-3-large": {
                "cost_per_million_tokens": 0.13
            },
            "text-embedding-ada-002": {
                "cost_per_million_tokens": 0.10
            }
        }
        # 'default_model_for_pricing': "gpt-4o-mini" # Optional: if you want a fallback
    }
}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration from a YAML file, merging with defaults."""
    config = DEFAULT_CONFIG.copy() # Start with defaults

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Deep merge user config into defaults
                    for section, settings in user_config.items():
                        if section in config and isinstance(config[section], dict) and isinstance(settings, dict):
                             config[section].update(settings) # Update existing dict section
                        else:
                             config[section] = settings # Add new sections or overwrite non-dict sections
    except Exception as e:
        print(f"Warning: Could not load or parse {config_path}: {e}. Using default configuration.")
        config = DEFAULT_CONFIG.copy() # Reset to defaults on error

    # --- Environment variables override specific config keys ---
    # Example: Allow overriding the model via env var
    # if 'OPENAI_MODEL' in os.environ:
    #    config['synthesizer']['model'] = os.environ['OPENAI_MODEL']

    return config

# Load config once when the module is imported
CONFIG = load_config()

# --- Helper functions to access config easily ---

def get_synthesizer_config() -> Dict[str, Any]:
    return CONFIG.get('synthesizer', DEFAULT_CONFIG['synthesizer'])

def get_search_config() -> Dict[str, Any]:
    return CONFIG.get('search', DEFAULT_CONFIG['search'])

def get_rag_config() -> Dict[str, Any]:
    return CONFIG.get('rag', DEFAULT_CONFIG['rag'])

def get_reasoner_config() -> Dict[str, Any]:
    return CONFIG.get('reasoner', DEFAULT_CONFIG['reasoner'])

# --- Getters for New Sections ---

def get_embedding_config() -> Dict[str, Any]:
    """Returns the configuration for the embedding model."""
    return CONFIG.get('embedding', DEFAULT_CONFIG['embedding'])

def get_summarizer_config() -> Dict[str, Any]:
    """Returns the configuration for the summarizer node."""
    return CONFIG.get('summarizer', DEFAULT_CONFIG['summarizer'])

def get_retriever_config() -> Dict[str, Any]:
    """Returns the configuration for the retriever node."""
    return CONFIG.get('retriever', DEFAULT_CONFIG['retriever'])

def get_consolidator_config() -> Dict[str, Any]:
    """Returns the configuration for the consolidator node."""
    return CONFIG.get('consolidator', DEFAULT_CONFIG['consolidator'])

def get_clarifier_config() -> Dict[str, Any]: # Added getter for clarifier
    """Returns the configuration for the clarifier node."""
    return CONFIG.get('clarifier', DEFAULT_CONFIG['clarifier'])

def get_graph_config() -> Dict[str, Any]:
    """Returns the configuration for graph execution parameters."""
    return CONFIG.get('graph', DEFAULT_CONFIG['graph'])

def get_prompt_logging_config() -> Dict[str, Any]:
    """Returns the configuration for prompt logging."""
    return CONFIG.get('prompt_logging', DEFAULT_CONFIG['prompt_logging'])

def get_openai_pricing_config() -> Dict[str, Any]:
    """Returns the OpenAI API pricing configuration."""
    return CONFIG.get('openai_pricing', DEFAULT_CONFIG['openai_pricing'])