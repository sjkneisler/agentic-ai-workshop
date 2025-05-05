# Product Context

## Why This Project Exists

This project aims to create a clear, runnable demonstration of a research agent pipeline using LangGraph and tool-using agents. It serves as an educational tool and a foundation for more complex agentic systems.

## Problems It Solves

- Provides a practical example of an agentic workflow (Clarify+Outline -> Reason(Tool Use) -> Synthesize).
- Offers a modular structure that's easy to understand and extend.
- Lowers the barrier to entry for experimenting with research agents by using standard Python and LangChain/LangGraph.

## How It Should Work

- The agent takes a user's question via a command-line interface (CLI).
- The agent's workflow is orchestrated by LangGraph (`agent/__init__.py`), defining a state machine with nodes for each step:
    - **Clarification Node (`agent/clarifier.py`):** Uses LangChain components (initialized via `agent/utils.py`) to determine if the initial question is ambiguous. If so, it suggests specific follow-up questions, prompts the user for answers in the terminal, and then uses another LangChain chain to synthesize a refined question *and* generate a basic Markdown research outline (`plan_outline`). Requires `langchain-openai`, `langchain-core`, an `OPENAI_API_KEY`, and uses models/settings from `config.yaml`. If clarification isn't needed or possible, it uses the original question and generates a default outline. Updates `clarified_question` and `plan_outline` state.
    - **Reasoning Node (`agent/reasoner.py`):** Initializes and runs an iterative LangChain agent (e.g., OpenAI Tools Agent).
        - Receives `clarified_question` and `plan_outline` from state.
        - Uses `web_search` (from `agent/search.py`) and `local_document_search` (RAG, from `agent/rag_utils/rag_query.py`) as tools.
        - Iteratively calls tools based on the question/outline to gather information, using intermediate results.
        - Runs up to `max_iterations` (from `config.yaml`).
        - Requires `OPENAI_API_KEY` for the agent's LLM. Tool usage may require `SERPER_API_KEY` (search) or `OPENAI_API_KEY` (RAG).
        - Updates `combined_context` state with the agent's final synthesized information.
    - **Synthesis Node (`agent/synthesizer.py`):** Generates the final answer using an LLM (initialized via `agent/utils.py`) based on the `clarified_question` and the `combined_context` from the reasoner. Requires `OPENAI_API_KEY` and uses settings from `config.yaml`. Updates `final_answer` state.
- The LangGraph application (`app`) is invoked by `agent.run_agent()`.
- It utilizes external APIs (Serper for search tool, OpenAI via LangChain/utils for LLM tasks and RAG tool) configured via `.env` (API keys) and `config.yaml` (models, prompts, RAG settings, clarification settings, reasoner settings).
- The final synthesized answer (or error message) from the graph's final state is printed to the console. Output detail is controlled via `--quiet`, default, and `--verbose` flags. Source tracking from the reasoner's tool calls is currently not implemented.

## User Experience Goals

- **Simplicity:** Easy to set up and run with standard Python tooling.
- **Clarity:** The agent's flow and the code for each module should be straightforward to understand (though the reasoner is now more complex).
- **Extensibility:** Users should feel empowered to modify or replace individual agent modules or add tools to the reasoner.
- **Graceful Failure:** The agent should provide clear error messages if required configurations (like API keys) are missing.