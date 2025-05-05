"""
Agent module that acts as the 'brain' of the research loop, deciding the next action.
"""
import warnings
from typing import Dict, Any, List, Optional

# LangChain Core and Components
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Shared Utilities (Logging, LLM Init)
from agent.utils import print_verbose, initialize_llm # Use absolute import

# Agent State
from agent.state import AgentState # Use absolute import

# Config
from agent.config import get_reasoner_config # Use absolute import

# --- LangGraph Node ---

def reason_node(state: AgentState) -> Dict[str, Any]:
    """
    Acts as the 'brain' of the research loop. Decides the next action based
    on the question, outline, and notes gathered so far.

    Possible next actions: SEARCH, FETCH, RETRIEVE_CHUNKS, SUMMARIZE, CONSOLIDATE, STOP.
    """
    is_verbose = state['verbosity_level'] == 2
    # Check for prior errors first
    if state.get("error"):
        if is_verbose: print_verbose("Skipping reasoning due to previous error.", style="yellow")
        # If there's an error, default to STOP and propagate the error message
        return {"next_action": "STOP", "error": state.get("error")}

    if is_verbose: print_verbose("Entering Reasoning Node (Decision Maker)", style="magenta")

    # --- Gather context from state ---
    question = state['clarified_question']
    outline = state['plan_outline']
    notes = state.get('notes', [])
    search_results = state.get('search_results', []) # Needed to decide if FETCH is possible
    current_iteration = state.get('current_iteration', 0) # Default to 0 if not set
    reasoner_config = get_reasoner_config()
    max_iterations = reasoner_config.get('max_iterations', 5) # Max reasoning cycles

    # --- Check stopping condition (Max Iterations) ---
    if current_iteration >= max_iterations:
        if is_verbose: print_verbose(f"Max iterations ({max_iterations}) reached. Moving to consolidate.", style="yellow")
        return {"next_action": "CONSOLIDATE", "current_iteration": current_iteration} # Keep iteration count

    # --- Initialize LLM ---
    reasoner_llm = initialize_llm(
        model_config_key='reasoner_model', # Key within reasoner config section
        temp_config_key='reasoner_temperature',
        default_model='gpt-4o-mini', # Use a capable model for reasoning
        default_temp=0.1 # Low temp for deterministic decision making
    )
    if not reasoner_llm:
        error_msg = "Failed to initialize LLM for Reasoner Node."
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "next_action": "STOP"}

    # --- Format Notes and Search Results for Prompt ---
    formatted_notes = "\n".join(f"- {note}" for note in notes) if notes else "No notes gathered yet."
    formatted_search = ""
    if search_results:
         url_list = "\n".join(f"  - [{i+1}] {res.get('title', 'N/A')} ({res.get('link', 'N/A')})" for i, res in enumerate(search_results))
         formatted_search = f"Recent Search Results (potential URLs to fetch):\n{url_list}"
    else:
         formatted_search = "No recent search results available to fetch from."

    # --- Define Prompt for Decision Making ---
    # This prompt needs careful crafting and testing.
    system_prompt = reasoner_config.get('system_prompt', """
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
""").strip()

    user_prompt = f"""
User Question: {question}

Research Plan Outline:
{outline}

Notes Gathered So Far:
{formatted_notes}

{formatted_search}

Based on the current state (Iteration {current_iteration+1}/{max_iterations}), what is the single best next action to take? Ensure the action and argument directly help fulfill the Research Plan Outline. Format your response clearly as 'Action: [ACTION]' and 'Argument: [ARGUMENT]'. If the action doesn't require an argument, use 'Argument: None'.
"""

    # --- Invoke LLM for Decision ---
    if is_verbose: print_verbose("Invoking reasoner LLM to decide next action...", style="dim blue")

    try:
        messages = [
            SystemMessage(content=system_prompt.format(iteration=current_iteration+1, max_iterations=max_iterations)),
            HumanMessage(content=user_prompt),
        ]
        response = reasoner_llm.invoke(messages)
        decision_text = response.content if hasattr(response, 'content') else str(response)

        if is_verbose: print_verbose(f"LLM Decision Output:\n{decision_text}", style="dim")

        # --- Parse Decision ---
        action = "STOP" # Default to STOP if parsing fails
        argument = None
        lines = decision_text.strip().split('\n')
        action_found = False
        argument_found = False
        for line in lines:
            if line.lower().startswith("action:") and not action_found:
                action = line.split(":", 1)[1].strip().upper()
                action_found = True
            elif line.lower().startswith("argument:") and not argument_found:
                argument = line.split(":", 1)[1].strip()
                if argument.lower() == 'none':
                    argument = None # Handle explicit None
                argument_found = True
            if action_found and argument_found:
                 break # Stop parsing once both are found

        # Validate action
        valid_actions = ["SEARCH", "FETCH", "RETRIEVE_CHUNKS", "CONSOLIDATE", "STOP"]
        if action not in valid_actions:
             warnings.warn(f"LLM returned invalid action: '{action}'. Defaulting to STOP.")
             action = "STOP"
             argument = None # Clear argument if action is invalid
        
        # Validate argument presence/absence
        if action in ["SEARCH", "RETRIEVE_CHUNKS"] and not argument:
             warnings.warn(f"Action '{action}' requires an argument, but none was provided. Defaulting to STOP.")
             action = "STOP"
        if action == "FETCH":
             if not argument:
                 warnings.warn(f"Action 'FETCH' requires a URL argument, but none was provided. Defaulting to STOP.")
                 action = "STOP"
             elif not search_results: # Cannot fetch if no search results exist
                 warnings.warn(f"Action 'FETCH' chosen, but no search results available. Defaulting to STOP.")
                 action = "STOP"
                 argument = None

        if action in ["CONSOLIDATE", "STOP"] and argument:
             warnings.warn(f"Action '{action}' does not require an argument, but one was provided ('{argument}'). Ignoring argument.")
             argument = None


        if is_verbose: print_verbose(f"Parsed Action: {action}, Argument: {argument}", style="green")

        # --- Update State based on Decision ---
        # Always update iteration count and the decided next action
        update_dict = {"next_action": action, "current_iteration": current_iteration + 1}

        # Set specific fields based on the action
        if action == "SEARCH":
            update_dict["current_query"] = argument
            update_dict["search_results"] = [] # Clear old search results before new search
            update_dict["url_to_fetch"] = None
        elif action == "FETCH":
            update_dict["url_to_fetch"] = argument
            # Keep search_results until after fetch? Or clear now? Let's clear.
            update_dict["search_results"] = []
            update_dict["current_query"] = None
        elif action == "RETRIEVE_CHUNKS":
            update_dict["current_query"] = argument
            update_dict["search_results"] = [] # Clear search results if retrieving
            update_dict["url_to_fetch"] = None
        elif action in ["CONSOLIDATE", "STOP"]:
            # Clear potentially lingering action-specific fields
            update_dict["current_query"] = None
            update_dict["url_to_fetch"] = None
            update_dict["search_results"] = []

        return update_dict

    except Exception as e:
        error_msg = f"Reasoner LLM invocation or parsing failed: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Stop on error, include error message in state
        return {"error": error_msg, "next_action": "STOP", "current_iteration": current_iteration + 1}

# Need to add 'current_iteration' to AgentState (if not already done)
# Need to add reasoner config section to config.yaml and load in config.py
# Need to add get_reasoner_config to config.py