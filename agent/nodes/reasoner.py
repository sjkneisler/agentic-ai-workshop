"""
Agent module that acts as the 'brain' of the research loop, deciding the next action.
"""
import warnings
from typing import Dict, Any, List, Optional

# LangChain Core and Components
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Shared Utilities (Logging, LLM Init)
from agent.utils import print_verbose, initialize_llm, log_prompt_data # Use absolute import

# Langchain callbacks for token usage
try:
    from langchain_community.callbacks.manager import get_openai_callback
    LANGCHAIN_CALLBACKS_AVAILABLE = True
except ImportError:
    warnings.warn("LangChain callbacks not found. Cost calculation via get_openai_callback will be disabled for reasoner.")
    LANGCHAIN_CALLBACKS_AVAILABLE = False

# Agent State
from agent.state import AgentState # Use absolute import

# Config
from agent.config import get_reasoner_config, get_openai_pricing_config # Use absolute import

# --- LangGraph Node ---

def reason_node(state: AgentState) -> Dict[str, Any]:
    """
    Acts as the 'brain' of the research loop. Decides the next action based
    on the question, outline, and notes gathered so far.

    Possible next actions: SEARCH, FETCH, RETRIEVE_CHUNKS, SUMMARIZE, CONSOLIDATE, STOP.
    """
    is_verbose = state['verbosity_level'] == 2
    # Check for prior errors first
    current_total_openai_cost = state.get('total_openai_cost', 0.0) # Get existing cost

    if state.get("error"):
        if is_verbose: print_verbose("Skipping reasoning due to previous error.", style="yellow")
        # If there's an error, default to STOP and propagate the error message, preserving current cost
        return {"next_action": "STOP", "error": state.get("error"), "total_openai_cost": current_total_openai_cost}

    if is_verbose: print_verbose("Entering Reasoning Node (Decision Maker)", style="magenta")

    # --- Initialize cost for this node's calls ---
    current_node_call_cost = 0.0
    pricing_config = get_openai_pricing_config().get('models', {})

    # --- Gather context from state ---
    question = state['clarified_question']
    outline = state['plan_outline']
    notes = state.get('notes', [])
    search_results = state.get('search_results', []) # Needed to decide if FETCH is possible
    current_iteration = state.get('current_iteration', 0) # Default to 0 if not set
    seen_queries = state.get('seen_queries', set()) # Read seen queries
    seen_urls = state.get('seen_urls', set()) # Read seen URLs
    reasoner_config = get_reasoner_config()
    max_iterations = reasoner_config.get('max_iterations', 5) # Max reasoning cycles

    # --- Check stopping condition (Max Iterations) ---
    if current_iteration >= max_iterations:
        if is_verbose: print_verbose(f"Max iterations ({max_iterations}) reached. Moving to consolidate.", style="yellow")
        return {"next_action": "CONSOLIDATE", "current_iteration": current_iteration, "total_openai_cost": current_total_openai_cost}

    # --- Initialize LLM ---
    reasoner_llm = initialize_llm(
        model_config_key='reasoner_model', # Key within reasoner config section
        temp_config_key='reasoner_temperature',
        default_model='o4-mini', # Use a capable model for reasoning
        default_temp=1 # Low temp for deterministic decision making
    )
    if not reasoner_llm:
        error_msg = "Failed to initialize LLM for Reasoner Node."
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg, "next_action": "STOP", "total_openai_cost": current_total_openai_cost}

    # --- Format Notes and Search Results for Prompt ---
    formatted_notes = "\n".join(f"- {note}" for note in notes) if notes else "No notes gathered yet."
    formatted_search = ""
    if search_results:
         # Mark seen URLs in the list presented to the LLM
         url_list_items = []
         for i, res in enumerate(search_results):
             url = res.get('link', 'N/A')
             seen_marker = " (Already Fetched)" if url in seen_urls else ""
             url_list_items.append(f"  - [{i+1}] {res.get('title', 'N/A')} ({url}){seen_marker}")
         url_list = "\n".join(url_list_items)
         formatted_search = f"Recent Search Results (potential URLs to fetch):\n{url_list}"
    else:
         formatted_search = "No recent search results available to fetch from."

    formatted_seen_queries = "\n".join(f"- '{q}'" for q in seen_queries) if seen_queries else "None"
    formatted_seen_urls = "\n".join(f"- {url}" for url in seen_urls) if seen_urls else "None"

    # --- Define Prompt for Decision Making ---
    # This prompt needs careful crafting and testing.
    system_prompt = reasoner_config.get('system_prompt', """
You are the reasoning core of a research agent. Your goal is to decide the single next step to fulfill the research plan based on the information gathered so far.

Analyze the User's Question, the Research Plan Outline, and the Notes gathered.
Consider the Recent Search Results if deciding to fetch a URL.

Possible Next Actions:
1.  FETCH: If there is at least one URL in 'Recent Search Results' that is **NOT** listed under 'URLs Already Fetched' AND you deem it highly promising for a topic in the 'Research Plan Outline'. Prioritize this over SEARCH. Provide the exact URL to fetch. If multiple unvisited URLs are promising, pick the one you believe is most relevant.
2.  RETRIEVE_CHUNKS: If you need to consult information already fetched and stored (e.g., to check coverage on a topic before searching again, or if the most relevant URLs have already been fetched and summarized). Provide a concise query for the vector store relevant to an outline topic.
3.  CONSOLIDATE: If you believe enough information has been gathered across all outline points and notes should be prepared for the final answer. Choose this if the notes adequately cover the outline.
4.  STOP: If the plan seems fulfilled by the notes, or if you are stuck after trying different actions.
5.  SEARCH: **ONLY as a last resort.** Choose SEARCH if, and only if, **ALL** of the following conditions are met:
    a. There are NO unvisited URLs in 'Recent Search Results' that you deem relevant and promising for any part of the 'Research Plan Outline'.
    b. You have already considered if `RETRIEVE_CHUNKS` could answer the immediate need.
    c. More general information or new starting points are absolutely essential for an uncovered part of the outline.
    Avoid previously attempted queries listed below, or queries that are extremely similar.

Current Iteration: {iteration}/{max_iterations}

Previously Attempted Queries (Avoid repeating):
{seen_queries}

URLs Already Fetched (Avoid fetching again):
{seen_urls}

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

Previously Attempted Queries:
{formatted_seen_queries}

URLs Already Fetched:
{formatted_seen_urls}

Based on the current state (Iteration {current_iteration+1}/{max_iterations}), what is the single best next action to take? Ensure the action and argument directly help fulfill the Research Plan Outline. Format your response clearly as 'Action: [ACTION]' and 'Argument: [ARGUMENT]'. If the action doesn't require an argument, use 'Argument: None'.
"""

    # --- Invoke LLM for Decision ---
    if is_verbose: print_verbose("Invoking reasoner LLM to decide next action...", style="dim blue")

    try:
        messages = [
            SystemMessage(content=system_prompt.format(
                iteration=current_iteration+1,
                max_iterations=max_iterations,
                seen_queries=formatted_seen_queries,
                seen_urls=formatted_seen_urls
            )),
            HumanMessage(content=user_prompt.format(
                formatted_seen_queries=formatted_seen_queries,
                formatted_seen_urls=formatted_seen_urls
            )),
        ]
        if LANGCHAIN_CALLBACKS_AVAILABLE and reasoner_llm:
            with get_openai_callback() as cb:
                response = reasoner_llm.invoke(messages)
                decision_text = response.content if hasattr(response, 'content') else str(response)
                
                prompt_tokens = cb.prompt_tokens
                completion_tokens = cb.completion_tokens
                model_name = reasoner_llm.model_name if hasattr(reasoner_llm, 'model_name') else reasoner_config.get('model')

                model_pricing_info = pricing_config.get(model_name)
                if model_pricing_info:
                    input_cost = model_pricing_info.get('input_cost_per_million_tokens', 0)
                    output_cost = model_pricing_info.get('output_cost_per_million_tokens', 0)
                    call_cost_iter = (prompt_tokens / 1_000_000 * input_cost) + \
                                     (completion_tokens / 1_000_000 * output_cost)
                    current_node_call_cost += call_cost_iter
                    if is_verbose: print_verbose(f"Reasoner call cost: ${call_cost_iter:.6f}", style="dim yellow")
        else:
            response = reasoner_llm.invoke(messages)
            decision_text = response.content if hasattr(response, 'content') else str(response)
            if is_verbose and not LANGCHAIN_CALLBACKS_AVAILABLE: print_verbose("Langchain callbacks unavailable, skipping cost calculation for reasoner.", style="dim yellow")

        # Log prompt and response
        log_prompt_data(
            node_name="reasoner_node",
            prompt={"system_prompt": system_prompt.format(
                        iteration=current_iteration+1,
                        max_iterations=max_iterations,
                        seen_queries=formatted_seen_queries,
                        seen_urls=formatted_seen_urls
                    ), "user_prompt": user_prompt.format(
                        formatted_seen_queries=formatted_seen_queries,
                        formatted_seen_urls=formatted_seen_urls
                    )
            },
            response=decision_text,
            additional_info={
                "model": reasoner_llm.model_name if reasoner_llm else reasoner_config.get('model'),
                "temperature": reasoner_llm.temperature if reasoner_llm else reasoner_config.get('temperature')
            }
        )

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
                # MODIFIED LINE: Strip surrounding quotes as well
                argument = line.split(":", 1)[1].strip().strip('"')
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
        updated_total_openai_cost = current_total_openai_cost + current_node_call_cost
        update_dict = {
            "next_action": action,
            "current_iteration": current_iteration + 1,
            "total_openai_cost": updated_total_openai_cost # Include updated cost
        }
        if is_verbose:
            print_verbose(f"Reasoner node cost: ${current_node_call_cost:.6f}", style="yellow")
            print_verbose(f"Total OpenAI cost updated: ${current_total_openai_cost:.6f} -> ${updated_total_openai_cost:.6f}", style="yellow")

        # Preserve query_for_retrieval and seen_urls by default unless explicitly changed
        update_dict["query_for_retrieval"] = state.get("query_for_retrieval")
        update_dict["seen_urls"] = seen_urls # Start with the input seen_urls

        # Set specific fields based on the action
        if action == "SEARCH":
            update_dict["current_query"] = argument
            update_dict["query_for_retrieval"] = argument # Set this query as the one to use for potential retrieval later
            # Add the new query to the set of seen queries
            updated_seen_queries = seen_queries.copy()
            updated_seen_queries.add(argument)
            update_dict["seen_queries"] = updated_seen_queries
            # update_dict["search_results"] = [] # DON'T Clear search results here
            update_dict["url_to_fetch"] = None
        elif action == "FETCH":
            update_dict["url_to_fetch"] = argument
            # Add the fetched URL to seen_urls
            updated_seen_urls = seen_urls.copy()
            updated_seen_urls.add(argument)
            update_dict["seen_urls"] = updated_seen_urls
            # update_dict["search_results"] = [] # DON'T Clear search results here
            # Clear current_query as it's not relevant for the FETCH step itself
            update_dict["current_query"] = None
            # query_for_retrieval is already preserved from input state by default setting above
        elif action == "RETRIEVE_CHUNKS":
            # Set current_query for the retrieval node, but don't change query_for_retrieval
            update_dict["current_query"] = argument
            # update_dict["search_results"] = [] # DON'T Clear search results here
            update_dict["url_to_fetch"] = None
        elif action in ["CONSOLIDATE", "STOP"]:
            # Clear potentially lingering action-specific fields
            update_dict["current_query"] = None
            update_dict["url_to_fetch"] = None
            update_dict["search_results"] = [] # OK to clear results when consolidating/stopping
            update_dict["query_for_retrieval"] = None # Clear retrieval query when stopping/consolidating

        # Ensure seen_queries and seen_urls are passed through if not updated
        if "seen_queries" not in update_dict:
             update_dict["seen_queries"] = seen_queries
        # seen_urls is already preserved by default setting above

        # ADDED LOGGING:
        if is_verbose:
            print_verbose(f"Reasoner node returning update: {update_dict}", style="yellow")

        return update_dict

    except Exception as e:
        error_msg = f"Reasoner LLM invocation or parsing failed: {e}"
        warnings.warn(error_msg)
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Stop on error, include error message in state, preserve cost as it was before this node's attempt
        return {"error": error_msg, "next_action": "STOP", "current_iteration": current_iteration + 1, "total_openai_cost": current_total_openai_cost}

# Comments moved inside the function or removed if obsolete
# Need to add 'current_iteration' to AgentState (if not already done) - This should be done in agent/state.py
# Need to add reasoner config section to config.yaml and load in config.py - This should be done in config.yaml and agent/config.py
# Need to add get_reasoner_config to config.py - This should be done in agent/config.py