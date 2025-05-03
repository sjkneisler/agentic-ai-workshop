import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main function we want to test
import agent

# --- Constants ---
MOCK_SERPER_PATH = Path(__file__).parent / "mock_serper.json"

# --- Helper Functions / Fixtures ---

@pytest.fixture
def mock_search_results():
    """Loads the mock Serper search results from the JSON file."""
    if not MOCK_SERPER_PATH.is_file():
        pytest.fail(f"Mock Serper data file not found at {MOCK_SERPER_PATH}")
    with open(MOCK_SERPER_PATH, 'r') as f:
        return json.load(f)

# --- Environment Variable Checks for Skipping ---

# Check if RAG should be tested (requires RAG_DOC_PATH to be a valid directory)
RAG_DOC_PATH_STR = os.getenv("RAG_DOC_PATH")
RAG_ENABLED = False
if RAG_DOC_PATH_STR:
    RAG_DOC_PATH = Path(RAG_DOC_PATH_STR)
    if RAG_DOC_PATH.is_dir():
        RAG_ENABLED = True
        # Additionally, RAG needs OpenAI key for embeddings, but we might mock that part
        # For skipping, just checking the path is usually sufficient for basic tests.
    else:
        print(f"\nNote: RAG_DOC_PATH ('{RAG_DOC_PATH_STR}') is set but not a directory. Skipping RAG-dependent tests.")
else:
    print("\nNote: RAG_DOC_PATH not set. Skipping RAG-dependent tests.")

# --- Test Cases ---

@patch('agent.search.serper_search') # Mock the search function
@patch('agent.rag.query_vector_store') # Mock RAG query
@patch('agent.synthesizer.synthesize_answer') # Mock synthesis
def test_run_agent_offline_mocked_search(
    mock_synthesize, mock_rag_query, mock_search, mock_search_results
):
    """
    Tests the main agent flow with mocked search, RAG, and synthesis.
    Ensures the pipeline runs end-to-end without external calls or API keys.
    """
    # Configure mocks
    mock_search.return_value = mock_search_results
    mock_rag_query.return_value = "Mock RAG context for testing." # Simulate RAG finding something
    mock_synthesize.return_value = "Synthesized answer based on mock search and RAG."

    # Set environment variable to potentially enable RAG planning step,
    # even though the query itself is mocked. We need a *valid* path for the planner.
    # If RAG_ENABLED is False based on actual env, we skip this part.
    original_rag_path = os.environ.get("RAG_DOC_PATH")
    if RAG_ENABLED:
        # Keep the existing valid path
        pass
    else:
        # Temporarily set a dummy path *if* we want the planner to include 'rag'
        # For this test, let's assume we *don't* want RAG planned if not enabled globally.
        # So, no need to set a dummy path here. The planner should skip 'rag'.
        pass


    # --- Run the agent ---
    test_question = "What is testing?"
    final_answer, source_urls = agent.run_agent(test_question, verbosity_level=2) # Run with verbose (level 2) for more output

    # --- Assertions ---
    # 1. Check that mocked functions were called as expected
    mock_search.assert_called_once_with(test_question, verbose=True)

    # Planner decides if RAG runs. Check if rag_query was called based on RAG_ENABLED
    if RAG_ENABLED:
         mock_rag_query.assert_called_once_with(test_question, verbose=True)
    else:
         mock_rag_query.assert_not_called() # Should not be called if RAG path invalid/missing

    # Reasoner combines results, Synthesizer gets called with combined context
    # We mocked synthesize directly, so check it was called.
    # The exact context passed to synthesize depends on reasoner logic, which we trust here.
    mock_synthesize.assert_called_once()
    # We could add more specific assertions on the arguments passed to synthesize if needed

    # 2. Check the final answer is what the mocked synthesizer returned
    assert final_answer == "Synthesized answer based on mock search and RAG." # Check the first element of the tuple

    # Restore original RAG_DOC_PATH if we changed it (we didn't in this version)
    # if original_rag_path is None and "RAG_DOC_PATH" in os.environ:
    #     del os.environ["RAG_DOC_PATH"]
    # elif original_rag_path:
    #     os.environ["RAG_DOC_PATH"] = original_rag_path


@pytest.mark.skipif(not RAG_ENABLED, reason="RAG_DOC_PATH not set or not a directory")
@patch('agent.search.serper_search') # Mock search
@patch('agent.rag._initialize_rag') # Mock the RAG initialization/query part
@patch('agent.synthesizer.synthesize_answer')
def test_run_agent_with_rag_planned(mock_synthesize, mock_rag_init, mock_search, mock_search_results):
    """
    Tests that if RAG is configured (RAG_ENABLED), the planner includes 'rag'
    and the RAG query function is called (though mocked here).
    This test only runs if RAG_ENABLED is True.
    """
    # Mock return values
    mock_search.return_value = mock_search_results
    # Simulate RAG finding context - mock the query function called *within* run_agent
    # We actually need to mock query_vector_store, not _initialize_rag for this.
    # Let's re-patch:
    with patch('agent.rag.query_vector_store') as mock_rag_query:
        mock_rag_query.return_value = "Specific RAG context for this test."
        mock_synthesize.return_value = "Synthesized answer including RAG."

        test_question = "Tell me about RAG."
        final_answer, source_urls = agent.run_agent(test_question, verbosity_level=2)

        # Assertions
        mock_search.assert_called_once_with(test_question, verbose=True)
        mock_rag_query.assert_called_once_with(test_question, verbose=True) # Crucial check
        mock_synthesize.assert_called_once()
        assert final_answer == "Synthesized answer including RAG." # Check the first element of the tuple


# Add more tests as needed:
# - Test case where search fails (mock search to raise exception)
# - Test case where RAG fails (mock rag_query to raise exception)
# - Test case with different verbose settings
# - Test case specifically for missing API keys (though run_agent catches RuntimeError now)