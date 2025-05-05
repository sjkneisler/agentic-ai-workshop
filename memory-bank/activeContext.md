# Active Context

## Current Work Focus

The agent pipeline has undergone a major refactoring:
- The Planner node has been removed.
- The Clarifier node now generates a Markdown outline in addition to refining the question.
- The Reasoner node has been transformed into an iterative, tool-using agent (using LangChain Agents) that attempts to fulfill the outline using Search and RAG tools.

The current focus is on:
- **Verification:** Testing this new Clarify->Reason(Agent)->Synthesize flow. Ensuring the reasoner agent correctly uses tools and iterates based on the outline.
- **Refinement:** Tuning the reasoner agent's prompt, iteration limits (`config.yaml`), and tool usage logic. Addressing potential issues like source tracking loss.
- **Testing:** Updating `pytest` tests to reflect the new architecture.

## Recent Changes (since last Memory Bank update - Post LangGraph Refactor)

- **Refactored Reasoner to Iterative Agent:**
    - Removed `agent/planner.py` and the `plan_node` from the LangGraph definition in `agent/__init__.py`.
    - Modified `agent/state.py` to replace `planned_steps` with `plan_outline: str`.
    - Modified `agent/clarifier.py`:
        - Updated LangChain prompts/chains to generate a Markdown outline alongside the refined question.
        - `clarify_node` now populates both `clarified_question` and `plan_outline` in the state.
    - Refactored `agent/reasoner.py`:
        - Implemented `reason_node` which now sets up and runs a LangChain agent (e.g., `create_openai_tools_agent` with `AgentExecutor`).
        - Defined `web_search` (using `agent.search.serper_search`) and `local_document_search` (using `agent.rag_utils.rag_query.query_vector_store`) as tools using the `@tool` decorator.
        - The agent receives the `clarified_question`, `plan_outline`, tool descriptions, and `max_iterations` via its prompt.
        - The agent iteratively calls the tools based on its internal reasoning to gather context relevant to the question and outline.
        - The final output of the agent execution becomes the `combined_context`.
    - Added `reasoner` configuration section to `config.yaml` (model, temperature, max_iterations) and updated `agent/config.py` to load it.
    - Updated `agent/__init__.py` graph definition to connect `clarify_node` -> `reason_node` -> `synthesize_node`.
- **Fixed Reasoner Prompt Input:** Corrected an issue in `agent/reasoner.py` where the `AgentExecutor` was not invoked with all the variables required by its prompt template.

*(Previous changes like LangGraph adoption, RAG enhancements, Clarifier implementation, etc., are documented in prior versions/below)*

--- (Previous Change Log Snippets for Context) ---

- **Refactored Agent Pipeline to LangGraph:** ... (details omitted for brevity) ...
- **Centralized Shared Utilities:** ... (details omitted for brevity) ...
- **Fixed Clarifier Bug:** ... (details omitted for brevity) ...
- **Enhanced RAG Retrieval with Link Traversal & Web Fetching:** ... (details omitted for brevity) ...
- **Implemented Interactive LangChain Clarifier:** ... (details omitted for brevity) ...
- *(... and so on for other previous changes ...)*

## Next Steps

1.  **Install/Update Dependencies:**
    *   Run `python3 -m pip install -r requirements.txt` (ensure `langchain-agents` or equivalent is included if not already covered by `langchain`).
2.  **Configure Environment & Config:**
    *   Ensure `.env` has valid `SERPER_API_KEY` (for search tool) and `OPENAI_API_KEY` (required for Clarifier, Reasoner Agent LLM, RAG tool, Synthesizer).
    *   Ensure `RAG_DOC_PATH` in `.env` points to a directory with documents if RAG tool usage is desired.
    *   Review/modify `config.yaml`, especially the new `reasoner` section (`model`, `temperature`, `max_iterations`).
3.  **Manual Testing (Focus on New Reasoner Agent Flow):**
    *   Run with default/verbose mode: `python3 main.py "Your question here"`
    *   **Test Clarifier:** Verify it still refines questions and now *also* outputs a reasonable Markdown `plan_outline` (visible in verbose logs).
    *   **Test Reasoner Agent:**
        *   Use `-v` to observe the `AgentExecutor` logs. Check if it's calling the `web_search` and `local_document_search` tools appropriately based on the question/outline.
        *   Verify it stops after `max_iterations` or (ideally) when it deems the outline fulfilled.
        *   Examine the `combined_context` passed to the synthesizer (in verbose logs) - does it reflect the information gathered by the tools?
        *   Test with and without RAG enabled (`RAG_DOC_PATH` set/unset).
    *   **Test Synthesizer:** Does the final answer make sense based on the context provided by the reasoner?
4.  **Run/Update Automated Tests:**
    *   Execute `python3 -m pytest`. Tests will need significant updates to mock the new reasoner agent's behavior or test its components in isolation.
5.  **Address Issues:** Fix bugs identified during testing (e.g., reasoner prompt tuning, tool query generation, source tracking).
6.  **Consider Enhancements:** Improve reasoner's stopping criteria, re-implement source tracking, add more tools.

## Active Decisions & Considerations

- **Agent Architecture:** Shifted from a fixed pipeline (`plan->search/rag->reason`) to a more dynamic one (`clarify+outline -> reason(agent+tools) -> synthesize`).
- **Reasoner:** Now an iterative LangChain agent responsible for tool selection (Search/RAG) and execution based on the clarified question and a generated outline. Configurable via `config.yaml`.
- **Planner:** Removed. Outline generation is now part of the Clarifier.
- **State:** `AgentState` now includes `plan_outline` instead of `planned_steps`.
- **Configuration:** `config.yaml` includes a `reasoner` section for model, temperature, and `max_iterations`.
- **Source Tracking:** Direct tracking of source URLs/paths from Search/RAG results is currently lost because the `AgentExecutor` abstracts the tool calls. Re-implementing this would require parsing the agent's intermediate steps.
- **Testing:** Automated tests require significant updates for the new architecture.