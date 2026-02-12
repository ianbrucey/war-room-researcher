# Integration Plan: GPT Researcher as Legal Research API

This plan outlines how to adapt GPT Researcher running within the Gemini/Auggie CLI to serve as a specialized **Legal Research API** for the `strategy_relay_defensive.py` workflow.

---

## 1. Goal
Enable the `strategy_relay_defensive.py` script to call GPT Researcher programmatically to:
1.  **Ingest Local Case Context**: Read PDFs from the `case-folder`.
2.  **Research External Law**: Search for case law and statutes via web/Legal Hub.
3.  **Return Data**: Output structured JSON (or specific Markdown sections) that the relay script can directly consume.

## 2. Approach: The "Research Adapter" Pattern

Instead of modifying the core GPT Researcher library significantly, we will create a dedicated **Adapter Script** (`api/research_adapter.py`) that bridges the gap between the Relay Script and GPT Researcher.

### Architecture

```
[Strategy Relay Script]
       |
       v (Subprocess with -P)
[Gemini/Auggie Agent]
       |
       v (Imports & Calls)
[Research Adapter]
       |
       v
[GPT Researcher] --> [Local Docs (DocumentLoader)]
                 --> [Web Search (Tavily/Legal Hub)]
```

---

## 3. Implementation Steps

### Step 1: Create `api/research_adapter.py`
This script will:
*   Import `GPTResearcher`.
*   Accept arguments: `query`, `case_folder_path`, `output_format` (json/md).
*   Configure `DOC_PATH` to `case_folder_path`.
*   Set `REPORT_SOURCE` to `hybrid` (Local + Web).
*   Instantiate `GPTResearcher`.
*   Run `conduct_research()`.
*   Run `write_report()` with a **Custom Prompt** designed to output JSON.

### Step 2: Define JSON Output Prompts
We need specific prompts for the legal domain.

**Example Prompt for Phase B (Counter-Requirements):**
> "Research the following legal counter-requirement: '{requirement}'. Find supporting case law in jurisdiction '{jurisdiction}'. Output the result strictly as a JSON object with keys: 'legal_basis', 'summary', 'citation'."

### Step 3: Modify `strategy_relay_defensive.py`
*   Replace direct calls to `file_search_query_legal-hub` and `search_cases_legal-hub` with a call to the **Research Adapter**.
*   Parse the JSON response.
*   Update the strategy artifacts.

---

## 4. Proof of Concept (POC) Plan

We will create a POC script `tests/poc_legal_research_api.py` to validate this workflow without touching the production relay script yet.

**POC Requirements:**
1.  **Mock Case Folder**: A folder with 1-2 dummy PDF/Text files.
2.  **Mock Query**: "What is the standard for Motion to Dismiss in Georgia?"
3.  **Execution**:
    *   Initialize `GPTResearcher` pointing to Mock Folder.
    *   Run Hybrid Research.
    *   Generate a Report.
    *   **Verify**: Does it cite the local PDF? Does it cite real external cases?

---

## 5. Challenges & Solutions

| Challenge | Solution |
|---|---|
| **JSON Reliability** | LLMs are not guaranteed to output valid JSON. | Use a library like `instructor` or rigorous regex parsing in the Adapter. |
| **Context Window** | Local PDFs might be huge. | Use the **Vector Store** path (Path B) for the Adapter if `case-folder` is large. |
| **Speed** | Deep research takes time. | Run research asynchronously or in parallel phases where possible. |

---

## 6. Action Items

1.  [ ] Create `api/` directory.
2.  [ ] Draft `api/research_adapter.py`.
3.  [ ] Write `tests/poc_legal_research_api.py`.
4.  [ ] Run POC and refine prompts.
