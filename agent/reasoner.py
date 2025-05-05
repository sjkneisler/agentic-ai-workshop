"""
Agent module for reasoning over gathered information using tools.

This module now implements an iterative agent that uses Search and RAG
as tools to gather information based on the clarified question and plan outline,
up to a maximum number of iterations.
"""
import warnings
from typing import List, Dict, Any, Optional

# LangChain Core and Components
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# Need to import the specific LLM wrapper (e.g., ChatOpenAI) if used directly,
# but initialize_llm handles this.

# Shared Utilities (Logging, LLM Init)
from .utils import print_verbose, initialize_llm

# Agent State
from agent.state import AgentState

# Tool Functions
from agent.search import serper_search
from agent.rag_utils.rag_query import query_vector_store
from agent.rag_utils.rag_initializer import is_rag_enabled

# Config
from .config import get_search_config, get_rag_config, get_reasoner_config


# --- Tool Definitions ---

@tool
def web_search(query: str) -> List[Dict[str, Any]]:
    """
    Performs a web search using the Serper API to find relevant online information.
    Use this for broad, public knowledge or recent events.
    Input should be a concise search query.
    """
    # Verbosity and num_results will be handled by the underlying serper_search
    # which reads from config and state. We might need to pass state or verbosity later if needed.
    search_config = get_search_config()
    num_results = search_config.get('num_results', 5)
    # Note: Currently not passing verbosity to the tool directly, relies on global state/config.
    # This might need adjustment if tool execution needs isolated verbosity.
    try:
        # Call the original function, let it handle API keys and errors internally
        return serper_search(query=query, n=num_results, verbose=False) # Keep tool output clean
    except Exception as e:
        return [{"error": f"Web search failed: {e}"}]

@tool
def local_document_search(query: str) -> str:
    """
    Searches local documents (RAG) for specific information, internal knowledge, or project context.
    Use this when the query relates to information likely contained within the indexed local files.
    Input should be a concise search query targeting local content.
    """
    if not is_rag_enabled():
        return "Local document search (RAG) is not enabled or configured."

    rag_config = get_rag_config()
    n_results = rag_config.get('rag_num_results', 3) # Use a config value for RAG results
    # Note: Currently not passing verbosity to the tool directly.
    try:
        # Call the original function
        context, sources = query_vector_store(query=query, n_results=n_results, verbose=False) # Keep tool output clean
        if not context:
            return "No relevant information found in local documents."
        # Maybe add sources later if needed, but keep context clean for LLM
        return f"Found relevant context in local documents:\n{context}"
    except Exception as e:
        return f"Local document search failed: {e}"


# --- LangGraph Node ---

def reason_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node that runs the iterative reasoning agent using tools.
    """
    is_verbose = state['verbosity_level'] == 2
    if state.get("error"): # Skip if prior node failed
         if is_verbose: print_verbose("Skipping reasoning due to previous error.", style="yellow")
         return {}

    if is_verbose: print_verbose("Entering Reasoning Node (Iterative Agent)", style="magenta")

    clarified_question = state['clarified_question']
    plan_outline = state['plan_outline']
    reasoner_config = get_reasoner_config()
    max_iterations = reasoner_config.get('max_iterations', 5)

    # Initialize LLM for the agent
    agent_llm = initialize_llm(
        model_config_key='reasoner_model',
        temp_config_key='reasoner_temperature',
        default_model='gpt-4o-mini', # Sensible default
        default_temp=0.3
    )

    if not agent_llm:
        error_msg = "Failed to initialize LLM for Reasoner Agent."
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg}

    # Define tools
    tools = [web_search]
    if is_rag_enabled():
        tools.append(local_document_search)
        if is_verbose: print_verbose("RAG is enabled, adding local_document_search tool.", style="dim blue")
    elif is_verbose:
        print_verbose("RAG is disabled, local_document_search tool unavailable.", style="yellow")

    # Format tool information for the prompt
    tool_names = ", ".join([t.name for t in tools])
    tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in tools])

    # Define the Agent Prompt
    # This prompt needs refinement based on testing.
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a research assistant. Your goal is to gather comprehensive information to answer the user's question and fulfill the research plan outline using the available tools.

User's Question: {question}

Research Plan Outline:
{outline}

Available Tools: {tool_names}
Tool Descriptions: {tools}

Instructions:
1. Analyze the question and outline.
2. Decide which tool (if any) is needed to gather the next piece of information. Prioritize `local_document_search` for specific internal/local context mentioned or implied, and `web_search` for broader public knowledge or recent information.
3. If you use a tool, formulate a concise query for it.
4. Evaluate the information returned by the tool in the context of the question and outline.
5. Repeat steps 2-4 up to a maximum of {max_iterations} times to build a comprehensive context.
6. Once you have gathered sufficient information or reached the iteration limit, synthesize the gathered information into a coherent text that addresses the user's question and aligns with the plan outline. This final text will be your output.
7. If no relevant information is found after using the tools, state that clearly.
""",
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True), # For potential future conversational use
            ("human", "{input}"), # The initial trigger/input for the agent
            MessagesPlaceholder(variable_name="agent_scratchpad"), # Where tool calls/responses go
        ]
    )

    # Create the Agent
    try:
        agent = create_openai_tools_agent(agent_llm, tools, prompt_template)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=is_verbose, # Pass verbosity to the executor
            max_iterations=max_iterations,
            handle_parsing_errors=True # Gracefully handle potential LLM output issues
            )
    except Exception as e:
        error_msg = f"Failed to create Reasoner AgentExecutor: {e}"
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        return {"error": error_msg}

    # Run the Agent
    if is_verbose: print_verbose(f"Invoking Reasoner Agent (max_iterations={max_iterations})...", style="dim blue")

    try:
        # The initial input combines the question and outline for the agent's context
        agent_input = f"Start research based on the question: '{clarified_question}' and the outline:\n{plan_outline}"
        # Prepare the full input dictionary for the prompt template
        invoke_input = {
            "input": agent_input,
            "question": clarified_question,
            "outline": plan_outline,
            "tool_names": tool_names,
            "tools": tool_descriptions, # Pass the formatted descriptions
            "max_iterations": max_iterations,
            "chat_history": [] # No history for now
        }
        result = agent_executor.invoke(invoke_input)
        final_context = result.get("output", "Agent did not produce an output.")
    
        if is_verbose:
            print_verbose("Reasoner Agent finished.", style="green")
            # print_verbose(f"Final Context:\n{final_context}", style="dim") # Maybe too verbose

        # TODO: Extract source URLs/paths from agent intermediate steps if needed
        # This requires parsing agent_executor's intermediate steps, which adds complexity.
        # For now, we lose the direct source tracking from the old search/rag nodes.

        return {"combined_context": final_context, "error": None}

    except Exception as e:
        error_msg = f"Reasoner Agent execution failed: {e}"
        warnings.warn(error_msg) # Log warning
        if is_verbose: print_verbose(error_msg, title="Node Error", style="bold red")
        # Return error state, but maybe include partial context if available?
        # For now, just return the error.
        return {"error": error_msg}

# Remove the old function
# def reason_over_sources(...)

# __all__ = ['reason_node']