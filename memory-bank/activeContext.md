# Active Context

## Current Work Focus

The primary focus is on **Refining Agent Research Quality and Output Comprehensiveness**.
Current efforts are focused on:
- Improving citation generation and post-processing.
- Ensuring the agent covers all aspects of a multi-faceted query.
- Enhancing the depth and detail of the final synthesized answer.
- Addressing issues with temporal anchoring (e.g., focusing on the correct year for "latest" advancements).
- Ongoing **Testing and Refinement** of the Deep Research Loop architecture.

## Recent Changes (This Session)

**Iteration 1: Initial Fixes Post Log Analysis**
- **Citation Prompts:**
    - Strengthened system prompt in `agent/nodes/summarize.py` to be more explicit about including exact citation tags.
    - Strengthened system prompt in `agent/nodes/synthesizer.py` to be extremely explicit about preserving citation tags verbatim.
- **Redundant Fetching/Similar Searches:**
    - Updated `agent/nodes/reasoner.py` prompt to be more forceful about not re-fetching already processed URLs.
    - Updated `agent/nodes/reasoner.py` prompt to further discourage semantically similar search queries.
- **Clarifier Year Anchoring (Attempt 1):**
    - Modified `agent/nodes/clarifier.py` refinement prompt to emphasize "latest" or "current" advancements.
- **Synthesizer Debugging:**
    - Added verbose logging in `agent/nodes/synthesizer.py` to print the raw `combined_context` fed to the LLM to help diagnose citation issues.

**Iteration 2: Addressing `KeyError` and Richer Synthesizer Context**
- **Clarifier `KeyError: 'topic'` Fix:**
    - Modified `agent/nodes/clarifier.py` refinement prompt to have the LLM infer the main topic from the question rather than requiring a `{topic}` variable.
    - Prompt now also encourages separate outline sections for distinct aspects of a query.
    - Dynamically added current year to clarifier prompt and updated `clarify_question` to pass it. Added `import datetime`.
- **State & Node Updates for Richer Synthesizer Context:**
    - **`agent/state.py`:**
        - Defined `StructuredNote(TypedDict)`: `{'summary': str, 'source_chunks': List[Document]}`.
        - Updated `AgentState.notes` to be `List[StructuredNote]`.
    - **`agent/nodes/summarize.py`:**
        - Modified to append `StructuredNote` objects (summary + its source_chunks) to `state.notes`.
    - **`agent/nodes/consolidate.py`:**
        - Updated to handle `List[StructuredNote]`.
        - Ranks based on summaries but retains association with `source_chunks`.
        - Constructs `combined_context` to include both ranked summaries and the `page_content` of their corresponding source_chunks.
    - **`agent/nodes/synthesizer.py`:**
        - Updated citation regex to: `re.compile(r"(\[Source\s+(?:\w+\s*=\s*'[^']*'(?:\s*,\s*|\s+)?)+\])")`.
        - Updated system prompt to instruct the LLM on using both summaries and raw chunks from the enriched `combined_context`.
- **Summarizer Output Length:**
    - Increased target word count in `agent/nodes/summarize.py` prompt to aim for 300-400 words.
- **Reasoner `KeyError: 'summary'` Fix:**
    - Updated `agent/nodes/reasoner.py` to correctly access `note['summary']` from `StructuredNote` objects when formatting its prompt.

**(Previous Sessions: Cost Tracking, Prompt Logging, Deep Research Loop Implementation - details in older activeContext versions or commit history)**

## Current Known Issues & Observations (Post Last Run)

- **Citation Post-Processing:** While detailed citation tags `[Source URL='...', ...]` are now present in the synthesizer's *raw output* (confirmed by `RAW COMBINED CONTEXT` log), the `_post_process_citations` function in `synthesizer.py` still reports "No detailed citation tags found for post-processing." This means its internal regex is not matching these tags for replacement with `[ref:N]`. The regex `(\[Source\s+(?:\w+\s*=\s*'[^']*'(?:\s*,\s*|\s+)?)+\])` needs further debugging or refinement.
- **Incomplete Topic Coverage:** The last run, while better on year focusing, still seemed to heavily favor "code review" over "code generation," despite the clarifier producing an outline with sections for both. The reasoner might not be effectively using the outline to ensure all parts are researched.
- **Output Length/Depth:** While the synthesizer now receives raw chunks, the final answer's depth and coverage of all sub-topics (like specific code generation models) could still be improved.

## Next Steps (Immediate)

1.  **Finalize Memory Bank Update:** Review and update `progress.md`, `systemPatterns.md`, and `techContext.md`.
2.  **Address Citation Regex:** Add debug prints within `_post_process_citations` in `synthesizer.py` to inspect the exact strings the regex is attempting to match against. This will allow for precise regex correction.
3.  **Strengthen Reasoner's Outline Adherence:** Further refine the `reasoner.py` system prompt to more strongly compel it to generate actions that cover all sections of the `plan_outline`, especially those currently lacking information in `notes`.
4.  **Refine Synthesizer's Use of Raw Chunks:** Adjust the `synthesizer.py` prompt to more explicitly guide the LLM to prioritize and extract detailed information from the "Supporting Raw Chunks" sections, using summaries mainly for structure.
5.  **Consider Further Clarifier Prompting for Year:** If year-specific searches are still problematic, explore making the clarifier even more direct in how it formulates the refined question regarding the current year.

## Active Decisions & Considerations

- **Agent Architecture:** Deep Research Loop with `StructuredNote` passing raw chunks to synthesizer is the current approach.
- **Observability:** Prompt logging and cost tracking are functional. Added raw context logging to synthesizer.
- **Citation Strategy:** Summaries embed full tags. Synthesizer aims to preserve these, then post-process. The preservation part seems to work; the post-processing regex is the issue.
- **Topic Coverage Strategy:** Relying on clarifier outline and reasoner's ability to follow it. Needs strengthening.
- **State Management:** `notes` are now `List[StructuredNote]`. `combined_context` is a rich string of summaries + raw chunks.
- **Testing:** Automated tests (`test_agent.py`) are significantly outdated and need a major overhaul once the core loop behavior stabilizes.