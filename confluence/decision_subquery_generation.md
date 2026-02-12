# DECISION: Sub-Query Generation Approach

**Status**: Pending Approval

---

## Decision

Sub-queries will be generated **inside GPT Researcher**, using its **existing `plan_research()` mechanism** with an enhanced prompt that accepts an optional **context packet** from WarRoom.

No new agent, no CLI subprocess, no swarm — just a smarter prompt.

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│  WARROOM (Laravel / CLI Agent)                      │
│                                                     │
│  Assembles context packet from:                     │
│    • ATTACKS.json    → opposing argument summary    │
│    • INTENT.md       → our position / objective     │
│    • metadata.json   → document summaries, statutes │
│    • case_summary.md → parties, jurisdiction        │
│                                                     │
│  Sends to GPT Researcher:                           │
│  {                                                  │
│    "query": "Research defenses against ...",         │
│    "context_packet": { ... },  // ~500-2000 tokens  │
│    "research_type": "opposition_brief"              │
│  }                                                  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  GPT RESEARCHER                                     │
│                                                     │
│  plan_research(query, context_packet)               │
│    → Single LLM call with enriched prompt           │
│    → Returns: ["query 1", "query 2", ..., "query 7"]│
│                                                     │
│  Then proceeds normally:                            │
│    → Tavily search on each sub-query                │
│    → Scrape results                                 │
│    → Synthesis (TBD — Problem 3)                    │
└─────────────────────────────────────────────────────┘
```

---

## What Goes In The Context Packet

The context packet is built by WarRoom from **existing structured data** — no raw documents, no full-text extraction at this stage.

| Field | Source | Example |
|---|---|---|
| `parties` | `case_summary.md` | `{"plaintiff": "Ian Bruce", "defendant": "CPS Recovery"}` |
| `jurisdiction` | `case_summary.md` | `"Georgia (N.D. Ga.)"` |
| `claims` | `case_summary.md` / `ATTACKS.json` | `["FDCPA violation", "breach of contract"]` |
| `opposing_argument` | `ATTACKS.json` → attack entry | `"CPS argues plaintiff lacks standing..."` |
| `key_statutes` | `metadata.json` | `["15 U.S.C. § 1692", "O.C.G.A. § 11-3-308"]` |
| `our_position` | `INTENT.md` | `"We have standing as assignee..."` |
| `key_facts` | `ATTACKS.json` / `metadata.json` | `"CPS sent collection letter for $5K debt..."` |

**Size**: ~500–2,000 tokens depending on case complexity. Well under any context window limit.

---

## What Changes In GPT Researcher

Two files need modification:

### 1. `gpt_researcher/actions/query_processing.py`

Add optional `context_packet` parameter to `plan_research()`. If present, pass it to the prompt generator.

### 2. `gpt_researcher/prompts.py`

Enhance `generate_search_queries_prompt()` to incorporate the context packet when provided. The prompt shifts from:

> *"Write 7 google search queries for: {query}"*

To:

> *"You are a legal research specialist. Given the following case context and research task, generate 7 highly specific search queries optimized for finding relevant case law and statutes."*
>
> *(includes: parties, jurisdiction, claims, opposing argument, key statutes, our position)*

**If no context_packet is provided**, the function behaves exactly as it does today. Zero breaking changes.

---

## Why This Approach (And Not The Alternatives)

| Alternative | Why Not |
|---|---|
| **WarRoom generates all sub-queries** | Tight coupling. WarRoom would need to know how to format search-engine-optimized queries. Legal reasoning ≠ query formulation. |
| **Dedicated CLI agent inside GPTR** | Overkill. Sub-query generation is a translation task, not a reasoning task. An agent adds 30-60 seconds of latency for no benefit. |
| **Pass full documents to sub-query step** | Confuses the LLM. It starts *analyzing* the motion instead of *generating search queries*. Also wastes tokens — summaries are sufficient. |

---

## Why Context Packet (Not Full Documents)

The `metadata.json` summaries and `ATTACKS.json` entries already contain everything the sub-query generator needs:

- **What they argue** → from `ATTACKS.json`
- **What statutes are at play** → from `metadata.json`
- **Who the parties are** → from `case_summary.md`

Full documents enter the pipeline later, at the **synthesis** stage, where the agent needs to read everything and produce an integrated analysis.

**Sub-query generation is a translation task**: "Given this legal need + context, produce search queries." It does not require deep document analysis.

---

## Example Input → Output

**Input**:
```json
{
  "query": "Research defenses against standing argument in MTD",
  "context_packet": {
    "parties": {"plaintiff": "Ian Bruce", "defendant": "CPS Recovery Services"},
    "jurisdiction": "Georgia (N.D. Ga.)",
    "claims": ["FDCPA violation"],
    "opposing_argument": "Defendant argues plaintiff lacks standing because CPS is not the original creditor and has not proven valid assignment",
    "key_statutes": ["15 U.S.C. § 1692", "O.C.G.A. § 11-3-308"],
    "our_position": "CPS acquired the debt through valid assignment and has standing"
  }
}
```

**Generated Sub-Queries**:
```json
[
  "FDCPA standing debt buyer assignee 15 USC 1692",
  "proof of assignment debt collection lawsuit Georgia",
  "debt buyer standing sue FDCPA Eleventh Circuit",
  "OCGA 11-3-308 burden proof holder due course",
  "CPS Recovery Services FDCPA standing cases",
  "assignment chain of title debt collection motion dismiss",
  "factual dispute standing 12(b)(6) motion debt assignee"
]
```

These queries are jurisdiction-aware, statute-specific, party-aware, and search-optimized — none of which would happen with a bare query string.
