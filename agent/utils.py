"""
Shared utility functions for the agent package.
"""
import os
import warnings
from typing import Optional, Any

# --- Rich Output Handling ---
try:
    from rich import print as rich_print
    from rich.panel import Panel
    from rich.console import Console
    console = Console() # console might be useful for other things later
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback print function
    def rich_print(*args, **kwargs): print(*args, **kwargs)
    # Dummy Panel class if rich is not available
    class Panel:
        def __init__(self, content, title="", **kwargs):
            self.content = content
            self.title = title
        def __str__(self):
            header = f"--- {self.title} ---" if self.title else "---"
            return f"{header}\n{self.content}\n---"

def print_verbose(message: str, title: str = "", style: str = "blue"):
    """
    Helper function for verbose printing, using rich if available.
    """
    if RICH_AVAILABLE:
        if title:
            rich_print(Panel(message, title=title, border_style=style, title_align="left"))
        else:
            rich_print(f"[{style}]{message}[/{style}]")
    else:
        if title:
            print(f"\n--- {title} ---")
            print(message)
            print("---")
        else:
            print(message)

# --- OpenAI/LangChain Utilities ---
try:
    import openai
    import tiktoken
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    # Define dummy ChatOpenAI if needed for type hinting elsewhere, though checks should prevent usage
    class ChatOpenAI: pass

# Import config loader carefully to avoid circular dependencies if utils is imported by config
try:
    from .config import load_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    def load_config(): return {} # Dummy config loader

_config_cache = None

def get_config_value(key: str, default: Any = None) -> Any:
    """Safely gets a value from the cached config."""
    global _config_cache
    if not CONFIG_AVAILABLE:
        return default
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache.get(key, default)

def initialize_llm(model_config_key: str, temp_config_key: str, default_model: str = 'gpt-4o-mini', default_temp: float = 0.7) -> Optional[ChatOpenAI]:
    """
    Initializes a ChatOpenAI instance based on config values.

    Args:
        model_config_key: The key in config.yaml for the model name.
        temp_config_key: The key in config.yaml for the temperature.
        default_model: Default model name if not in config.
        default_temp: Default temperature if not in config.

    Returns:
        A ChatOpenAI instance or None if unavailable/misconfigured.
    """
    if not OPENAI_AVAILABLE:
        warnings.warn("OpenAI/LangChain libraries not available.")
        return None

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        warnings.warn("OPENAI_API_KEY not found in environment variables.")
        return None

    try:
        model_name = get_config_value(model_config_key, default_model)
        temperature = get_config_value(temp_config_key, default_temp)

        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=openai_api_key
        )
        return llm
    except Exception as e:
        warnings.warn(f"Failed to initialize ChatOpenAI model '{model_config_key}': {e}")
        return None

def count_tokens(text: str, model: str = 'gpt-4o-mini') -> int:
    """Counts tokens using tiktoken, using a default model if needed."""
    if not OPENAI_AVAILABLE:
        warnings.warn("Tiktoken (part of OpenAI libs) not available for token counting.")
        return 0 # Cannot count tokens without tiktoken
    try:
        # Use the provided model name, fall back to default if necessary
        effective_model = model if model else 'gpt-4o-mini'
        encoding = tiktoken.encoding_for_model(effective_model)
        return len(encoding.encode(text))
    except Exception as e:
        warnings.warn(f"Could not count tokens for model '{effective_model}': {e}")
        return 0

# --- Other Potential Utilities (Add as needed) ---