"""
Defines the shared state object for the LangGraph agent pipeline.
"""
from typing import List, Dict, Any, TypedDict, Optional

class AgentState(TypedDict):
    """Represents the state of our agent graph."""
    original_question: str
    clarified_question: str
    planned_steps: List[str]
    search_results: List[Dict[str, Any]]
    rag_context: str
    rag_source_paths: List[str]
    combined_context: str
    final_answer: str
    web_source_urls: List[str]
    verbosity_level: int
    error: Optional[str] # To capture errors within the graph flow