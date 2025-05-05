# 🧠 Deep Research Agent - Demo

A small, recursive research agent built in Python that plans, searches the web (via Serper API), optionally incorporates local documents (via RAG with ChromaDB and OpenAI embeddings), reasons over the findings, and synthesizes answers using an LLM (OpenAI).

This project serves as a clear, runnable demonstration of a basic agentic workflow and is designed for easy understanding and modification.

## ✨ Features

*   **Modular Design:** Each step (Clarify, Plan, Search, RAG, Reason, Synthesize) is a separate Python module in the `agent/` directory.
*   **CLI Interface:** Simple command-line interaction via `main.py`.
*   **Configurable:** Uses `.env` file for API keys (`SERPER_API_KEY`, `OPENAI_API_KEY`) and RAG document path (`RAG_DOC_PATH`).
*   **Optional RAG:** Easily enable Retrieval-Augmented Generation by providing a path to local documents.
*   **Verbose Mode:** Inspect the agent's internal steps using the `--verbose` flag.
*   **Offline Testing:** Includes basic `pytest` tests with mocked external calls.

## 🚀 Quickstart

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url> # Replace with the actual URL later
    cd deep-research-agent
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure you have Python >= 3.10)*

3.  **Configure environment variables:**
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your API keys:
    *   `SERPER_API_KEY`: **Required** for web search. Get one from [serper.dev](https://serper.dev/).
    *   `OPENAI_API_KEY`: **Optional**, but required for RAG embeddings and LLM-based synthesis/clarification. Get one from [OpenAI](https://platform.openai.com/api-keys).
    *   `RAG_DOC_PATH`: **Optional**. See "RAG Setup" below.

4.  **Run the agent:**
    ```bash
    python main.py "What are the latest advancements in AI agents?"
    ```
    Or run without an argument to be prompted:
    ```bash
    python main.py
    ```

## ⚙️ Configuration

Beyond the API keys and RAG path in the `.env` file, you can tune the agent's behavior using the `config.yaml` file:

*   **Synthesizer:** Change the OpenAI model (`synthesizer.model`), adjust the system prompt (`synthesizer.system_prompt`) to alter the desired answer style (e.g., concise vs. detailed, tone), set `max_tokens`, and `temperature`.
*   **Search:** Configure the default number of search results (`search.num_results`).
*   **(Future):** Configure clarifier model/prompt, add output structure guidance, etc.

Example (`config.yaml`):
```yaml
synthesizer:
  model: "gpt-4o-mini"
  system_prompt: |
    You are a factual research assistant. Provide a bulleted list summarizing
    the key findings based strictly on the provided context.
  max_tokens: 300
search:
  num_results: 7
```

Modify `config.yaml` directly to experiment with different agent behaviors.

## ⚙️ How It Works

The agent follows a predefined pipeline orchestrated in `agent/__init__.py`:

1.  **Input:** Takes a question from the CLI (`main.py`).
2.  **Clarify (`agent/clarifier.py`):** (Optional) Refines the question (currently passes through).
3.  **Plan (`agent/planner.py`):** Determines the necessary steps (always "search", adds "rag" if `RAG_DOC_PATH` is valid).
4.  **Execute Steps:**
    *   **Search (`agent/search.py`):** Performs a web search using the Serper API if planned.
    *   **RAG (`agent/rag.py`):** Queries a local ChromaDB vector store if planned and configured. Requires `RAG_DOC_PATH` and `OPENAI_API_KEY`. Embeddings are generated on the fly (basic implementation).
5.  **Reason (`agent/reasoner.py`):** Combines the context gathered from search and RAG into a single block of text.
6.  **Synthesize (`agent/synthesizer.py`):** Uses the combined context and the clarified question to generate a final answer. Attempts to use OpenAI (`gpt-4o-mini` by default) if the key is available; otherwise, falls back to echoing the context.
7.  **Output:** Prints the final synthesized answer to the console.

```mermaid
graph TD
    A[Start: User Question] --> B(Clarify Question);
    B --> C(Plan Steps);
    C --> D{Execute Plan};
    D -- Search --> E[Web Search (Serper)];
    D -- RAG --> F[Vector Store Query (ChromaDB)];
    E --> G(Reason Over Sources);
    F --> G;
    G --> H[Synthesize Answer (OpenAI/Fallback)];
    H --> I[End: Final Answer];

    style E fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#ccf,stroke:#333,stroke-width:2px
    style H fill:#9cf,stroke:#333,stroke-width:2px
```
*(Mermaid diagram showing the flow)*

## 🔧 Customize It

While basic tuning (LLM model, prompts, number of search results) should be done via `config.yaml`, the modular design allows for deeper customization by editing the Python modules directly:

*   **Change Search Provider:** Edit `agent/search.py` to use a different API entirely.
*   **Improve Planning:** Modify the rules or logic in `agent/planner.py`.
*   **Enhance Reasoning:** Update `agent/reasoner.py` to perform more sophisticated analysis or summarization beyond simple concatenation.
*   **Use a Different LLM Provider:** Fundamentally change the API call logic in `agent/synthesizer.py` or `agent/clarifier.py` to use a non-OpenAI model.
*   **Improve RAG:** Enhance `agent/rag.py` with better document loading, chunking, embedding strategies, or different vector stores.

## 📚 RAG Setup (Optional)

To enable the agent to use your own local documents as context:

1.  Create a directory containing your documents (e.g., `.txt`, `.md` files - current RAG implementation is basic and doesn't explicitly handle file types yet).
2.  Set the `RAG_DOC_PATH` variable in your `.env` file to the **absolute or relative path** of that directory.
    ```dotenv
    RAG_DOC_PATH=./my_local_docs
    ```
3.  Ensure you have set a valid `OPENAI_API_KEY` in your `.env` file, as it's required for generating embeddings.
4.  Run the agent. The first time it runs with a valid `RAG_DOC_PATH`, it will attempt to initialize a ChromaDB vector store in `.rag_store/`. *(Note: The current implementation lacks robust document processing and embedding - this is a basic skeleton).*

## 🗣️ Verbose Mode

To see the intermediate steps, decisions, and outputs of each module, run the agent with the `--verbose` or `-v` flag:

```bash
python main.py --verbose "Tell me about vector databases."
```

## 💡 Future Ideas

This simple agent could be extended in many ways:

*   **LangGraph Integration:** Convert the steps into nodes in a LangGraph graph for more complex, stateful flows.
*   **FastAPI Wrapper:** Expose the agent logic via a web API using FastAPI.
*   **MCP Endpoint:** Wrap the agent as a Model Context Protocol (MCP) tool for use in environments like Cursor.
*   **Improved RAG:** Implement more robust document loading, chunking, metadata handling, and embedding management.
*   **Tool Use:** Allow the agent to plan and use other tools beyond search and RAG.
*   **Memory:** Add short-term or long-term memory capabilities.