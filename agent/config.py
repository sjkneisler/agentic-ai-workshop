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
        'model': 'gpt-4o-mini',
        'system_prompt': 'You are a helpful research assistant. Synthesize a concise answer to the user\'s question based *only* on the provided context. Do not add information not present in the context. If the context is insufficient, say so.',
        'max_tokens': 500,
        'temperature': 0.7
    },
    'search': {
        'num_results': 5
    },
    'rag': {
        'rag_initial_link_follow_depth': 3, # Max depth for following internal doc links during INITIAL indexing
        'rag_follow_external_links': True, # Fetch external web links found in retrieved chunks at QUERY time?
        'rag_follow_internal_chunk_links': True, # Follow internal links between CHUNKS at QUERY time?
        'rag_internal_link_depth': 1,       # Max depth for internal chunk link traversal at QUERY time
        'rag_internal_link_k': 2            # How many related chunks to retrieve per internal link at QUERY time
    },
    'reasoner': { # Added defaults for reasoner
        'model': 'gpt-4o-mini',
        'temperature': 0.3,
        'max_iterations': 5
    }
    # Add defaults for other sections like 'clarifier' if needed
}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration from a YAML file, merging with defaults."""
    config = DEFAULT_CONFIG.copy() # Start with defaults

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # Deep merge user config into defaults (simple merge for now)
                    # A more robust merge might be needed for nested dicts if complex
                    for section, settings in user_config.items():
                        if section in config and isinstance(config[section], dict):
                             config[section].update(settings)
                        else:
                             config[section] = settings # Add new sections if any
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

def get_reasoner_config() -> Dict[str, Any]: # Added getter for reasoner
    return CONFIG.get('reasoner', DEFAULT_CONFIG['reasoner'])

# Add getters for other sections as needed
# def get_clarifier_config()...