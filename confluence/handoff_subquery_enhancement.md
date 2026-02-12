# Handoff: Sub-Query Context Enhancement

**Status**: Implemented & Ready for Integration
**Date**: 2026-02-12

---

## Overview

We have enhanced GPT Researcher's sub-query generation to accept an optional **context packet** from WarRoom. This allows the agent to generate legally-specific, jurisdiction-aware, and case-informed research queries, rather than generic ones.

## Key Changes

### 1. New Data Structure: `context_packet`

A dictionary containing structured legal context integration is now supported.

```python
context_packet = {
    "parties": {"plaintiff": "...", "defendant": "..."},
    "jurisdiction": "Georgia (N.D. Ga.)",
    "claims": ["FDCPA violation"],
    "opposing_argument": "...",
    "key_statutes": ["15 U.S.C. § 1692"],
    "our_position": "..."
}
```

### 2. Modified Files

| File | Change |
|---|---|
| `gpt_researcher/agent.py` | `GPTResearcher.__init__` now accepts `context_packet` and stores it in `self.context_packet`. |
| `gpt_researcher/skills/researcher.py` | `ResearchConductor.plan_research` now threads `self.researcher.context_packet` to `plan_research_outline`. |
| `gpt_researcher/actions/query_processing.py` | `plan_research_outline` and `generate_sub_queries` now accept and pass `context_packet`. |
| `gpt_researcher/prompts.py` | `generate_search_queries_prompt` now injects `CASE CONTEXT` and `INSTRUCTIONS FOR LEGAL RESEARCH` into the prompt if `context_packet` is present. |

### 3. Usage Example

```python
from gpt_researcher import GPTResearcher

# 1. Prepare context from WarRoom
context = {
    "opposing_argument": "Plaintiff lacks standing...",
    "jurisdiction": "N.D. Ga."
}

# 2. Initialize Researcher with context
researcher = GPTResearcher(
    query="Standing in FDCPA cases",
    context_packet=context
)

# 3. Run Research (sub-queries will now be context-aware)
report = await researcher.conduct_research()
```

## Verification Scenarios

We created a test script `test_context_packet.py` to verify the logic.

**Prompt enhancement logic verified:**
- When `context_packet` is provided, the prompt includes:
  - "CASE CONTEXT" section with parties, jurisdiction, etc.
  - "INSTRUCTIONS FOR LEGAL RESEARCH" (Target specific legal issues, include statute numbers, etc.)
- When `context_packet` is missing, behavior remains **100% backward compatible** (standard generic prompt).

## Next Steps

1. **Integrate with WarRoom**: Update the WarRoom controller to construct this `context_packet` from `metadata.json`, `ATTACKS.json`, etc., and pass it when instantiating `GPTResearcher`.
2. **Test Real Scenarios**: Run a full research task with a real case context to see quality improvements in sub-queries.
