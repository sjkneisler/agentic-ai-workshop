I have come up with a plan to add an OpenAI API cost counter to the Deep Research Agent. The plan involves modifications to the agent's state, configuration files, core processing nodes, the main script for display, and updates to documentation and tests.

**Plan: Implement OpenAI API Cost Tracking**

**Goal:** To track and display the estimated cost of OpenAI API calls (LLMs and embeddings) made during a single run of the Deep Research Agent.

**Key Areas of Change:**

1.  **Agent State (`agent/state.py`):**
    *   Add `total_openai_cost: float = 0.0` to `AgentState`.

2.  **Configuration (`config.yaml` & `agent/config.py`):**
    *   Add an `openai_pricing` section to `config.yaml` with costs per million tokens for each model.
    *   Update `agent/config.py` to load this new pricing information.

3.  **Cost Calculation in Nodes:**
    *   Modify nodes making OpenAI calls (`clarifier.py`, `reasoner.py`, `chunk_embed.py`, `summarize.py`, `synthesizer.py`).
    *   In each, after an API call:
        1.  Retrieve token usage.
        2.  Identify the model used.
        3.  Fetch pricing from config.
        4.  Calculate call cost.
        5.  Add this cost to `total_openai_cost` in the agent state.

4.  **Displaying the Cost (`main.py`):**
    *   After `agent.run_agent()`, extract `total_openai_cost` from the final state.
    *   Print the estimated cost to the console.

5.  **Documentation Updates:**
    *   Update `README.md` (feature explanation, config details).
    *   Update Memory Bank files (`activeContext.md`, `productContext.md`, `techContext.md`, `progress.md`, `projectbrief.md`) to reflect the new feature and its implementation.

6.  **Testing (`tests/test_agent.py`):**
    *   Add tests to mock API responses with token usage.
    *   Verify correct calculation of `total_openai_cost`.
    *   Test cost display in `main.py`.

We can proceed with the first step of this plan, which would be modifying `agent/state.py`, once you approve.