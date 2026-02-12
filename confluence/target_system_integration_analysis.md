# Target System Integration Analysis

This document analyzes the architecture of the **Justice Quest / AionUI** application and outlines how to integrate GPT Researcher as a "Legal Research API."

---

## 1. System Overview (From Orientation Docs)

*   **Identity**: Single-tenant legal workspace ("Justice Quest").
*   **Tech Stack**:
    *   **Frontend**: React + TypeScript (Vite).
    *   **Backend**: Node.js + Express.
    *   **Database**: SQLite (local, synchronous).
    *   **AI Layer**: Gemini / Mistral / Auggie.
*   **Agent Execution Model**:
    *   **Interactive**: Agents (Gemini/Auggie) chat with the user in the WebUI.
    *   **Non-Interactive (Scripted)**: Agents are called via CLI with `-P` (prompt) flag to execute discrete tasks without user interaction.
    *   **Orchestration**: Python scripts (like `strategy_relay_defensive.py`) act as "Relay Runners," calling agents sequentially to perform multi-step workflows.

## 2. The Defensive Strategy Use Case (`strategy_relay_defensive.py`)

This script illustrates the "Relay Race" pattern we need to fit into.

### The Workflow
It breaks a complex legal task (responding to a specific motion) into discrete **Phases**:

| Phase | Role | Input | Output |
|---|---|---|---|
| **0. Attack Detector** | `Legal Analyst` | Opposing Motion (PDF) | `ATTACKS.json` (List of arguments/claims) |
| **A. Evidence Analyst** | `Evidence Analyst` | Attack Details + Case Docs | `EVIDENCE_ANALYSIS.json` (Gaps, burden analysis) |
| **B. Counter-Reqs** | `Legal Research Clerk` | Evidence + Legal Std | `counter_requirements.json` (What we must prove + **Case Match**) |
| **D. Viability** | `Senior Litigator` | Analysis + Reqs | `analysis.md` (Scoring, strategic advice) |
| **E. Gap Reporter** | `Partner` | All Artifacts | `GAP_ANALYSIS.md` (Consolidated report) |

### Current Research Implementation
Currently, the script relies on **MCP Tools** (Model Context Protocol) provided to the agent:
*   `file_search_query_legal-hub`: Semantic search over local case files.
*   `search_cases_legal-hub`: searching external case law.
*   `lookup_citation_legal-hub`: verifying citations.

### The Problem / Opportunity
The user wants to **replace/augment** these individual tool calls with **GPT Researcher**. Instead of the agent manually calling `search_cases` 5 times, the script could call a "Research API" (GPT Researcher) to produce a comprehensive report for a specific phase (e.g., Phase B: "Find case law supporting this counter-requirement").

---

## 3. Integration Plan: GPT Researcher as an API

To fit into this "Relay Race," GPT Researcher needs to act as a **specialized sub-agent** or **service** that takes a structured query and returns a structured result (or a markdown report), without hanging the script or requiring human input.

### Required Adaptations

1.  **Headless Mode**: We need a clean way to invoke GPTR from Python *without* the `cli.py` outputting to `outputs/uuid.md`. We need the return value directly. (We confirmed `write_report()` returns a string, so this is easy).
2.  **Structured Output**: The "Relay" script expects JSON artifacts (`EVIDENCE_ANALYSIS.json`). GPT Researcher generates Markdown reports.
    *   *Option A*: GPT Researcher generates a Markdown report, and the calling agent parses it.
    *   *Option B (Better)*: We modify GPTR (or use a custom prompt) to output JSON directly.
3.  **Local Context Injection**: The "Defensive" script heavily relies on **local case files** (`case-folder/documents`).
    *   We must use the `DOC_PATH` (or `DocumentLoader`) feature we analyzed to point GPTR at the specific case folder context.
    *   We likely need **Hybrid Mode**: Search *local* docs for facts, search *web/legal hub* for case law.

### Proposed Architecture

```mermaid
graph TD
    Script[strategy_relay_defensive.py] -->|Call| Adapter[GPTR_Adapter.py]
    
    subgraph GPT_Researcher
        Adapter -->|Config| Config[Local Docs + Web]
        Adapter -->|Query| Runner[Conduct Research]
        Runner -->|Docs| Loader[DocumentLoader (Local Case)]
        Runner -->|Web| Tavily[Tavily/LegalHub]
        Runner -->|Context| Context[ContextCompressor]
        Context -->|Aggregated| LLM
    end
    
    LLM -->|JSON/Markdown| Adapter
    Adapter -->|Artifact| Script
```

### Next Steps

1.  **Create a Proof-of-Concept Adapter**: Write a Python script that instantiates `GPTResearcher`, points it at a dummy case folder, runs a "hybrid" query (facts + law), and returns the output.
2.  **Refactor for JSON**: Experiment with `custom_prompt` to force GPT Researcher to output the specific JSON schema required by `strategy_relay_defensive.py` (e.g., matching the `counter_requirements.json` schema).
