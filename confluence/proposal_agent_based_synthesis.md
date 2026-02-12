# Proposal: Replacing RAG Synthesis with Agent-Based Curation

**Status**: Pending Review

---

## What We're Replacing

Currently, after GPT Researcher scrapes web pages, this happens:

```
For each sub-query (7 sub-queries by default):
  1. _scrape_data_by_urls() → search Tavily → get ~5-10 URLs → scrape each
     Output: list of {"raw_content": "...", "url": "..."} dicts
  
  2. context_manager.get_similar_content_by_query() → the RAG step:
     a. RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
     b. Embed each chunk (OpenAI embeddings by default)
     c. EmbeddingsFilter(similarity_threshold ≈ 0.35)
     d. Return top 10 matching chunks as formatted text
  
  3. Combine with any MCP context → return as string

All 7 sub-query context strings are concatenated → passed to generate_report()
```

### Where This Lives In Code

| Step | File | Function | Line |
|---|---|---|---|
| Overall dispatch | [researcher.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/researcher.py#L89-L211) | `conduct_research()` | 89-211 |
| Sub-query processing | [researcher.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/researcher.py#L449-L578) | `_process_sub_query()` | 449-578 |
| **RAG step (insertion point)** | [researcher.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/researcher.py#L527) | `context_manager.get_similar_content_by_query()` | **527** |
| Context compression | [context_manager.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/context_manager.py#L37-L63) | `get_similar_content_by_query()` | 37-63 |
| Chunk → Embed → Filter | [compression.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/context/compression.py#L121-L157) | `ContextCompressor.__get_contextual_retriever()` | 121-140 |
| Report generation | [writer.py](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/writer.py#L49-L121) | `ReportGenerator.write_report()` | 49-121 |

---

## Data Volume: What Are We Actually Working With?

Per research session:

| Metric | Typical Value | Notes |
|---|---|---|
| Sub-queries generated | ~7 | Controlled by `max_iterations` config |
| URLs found per sub-query | 5-10 | Controlled by `max_search_results_per_query` |
| Total unique URLs scraped | 20-50 | After deduplication via `_get_new_urls()` |
| Scraped text per page | 2,000-10,000 tokens | Varies by page |
| **Total raw scraped text** | **~100K-300K tokens** | This is what the RAG pipeline receives |
| After RAG compression | ~10K-30K tokens | Top 10 chunks × 7 sub-queries |
| Case documents (if Hybrid) | 5-50K tokens | Full extracted text from Mistral |

The RAG pipeline compresses ~200K tokens down to ~20K tokens. The question is whether those 20K tokens are the *right* 20K tokens.

---

## Proposed Replacement: Two-Stage Agent Pipeline

### Stage 1: Curation Agent

**When it runs**: After all scraping is complete, *instead of* the chunking/embedding/filtering step.

**What it receives**: All scraped web pages as text files in a temporary directory.

**What it does**: A Gemini or Auggie CLI agent (non-interactive, `-P` flag) reads all scraped documents and extracts only the legally relevant passages.

**What it produces**: A curated document — extracted passages with source citations.

```
┌──────────────────────────────────────────────────────────────┐
│ CURRENT FLOW (RAG)                                           │
│                                                              │
│  scraped_data (list of dicts in memory)                      │
│       ↓                                                      │
│  ContextCompressor (chunk → embed → filter)                  │
│       ↓                                                      │
│  compressed_context (string, ~20K tokens)                    │
│       ↓                                                      │
│  generate_report(context=compressed_context)                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ PROPOSED FLOW (Agent)                                        │
│                                                              │
│  scraped_data (list of dicts in memory)                      │
│    • HTML is parsed by BeautifulSoup during scraping        │
│    • Script/style tags removed, clean text extracted        │
│       ↓                                                      │
│  Write to temp files:  /tmp/research_{session}/scraped/      │
│    ├── source_001.txt  (clean text only)                     │
│    ├── source_002.txt  (clean text only)                     │
│    └── ... (20-50 files)                                     │
│       ↓                                                      │
│  CURATION AGENT (Gemini CLI -P):                             │
│    "Read all files in /tmp/research_{session}/scraped/.      │
│     Extract passages relevant to: {query + context_packet}.  │
│     Output a curated synthesis document."                    │
│       ↓                                                      │
│  curated_context (agent output, ~20-40K tokens)              │
└──────────────────────────────────────────────────────────────┘
```

### Stage 2: Synthesis Agent

**When it runs**: Replaces (or enhances) the current `generate_report()` LLM call.

**What it receives**: The curated web context + full case documents (via file paths on the same server).

**What it does**: Reads everything and produces the final research report.

```
┌──────────────────────────────────────────────────────────────┐
│ SYNTHESIS AGENT (Gemini CLI -P):                             │
│                                                              │
│  Reads:                                                      │
│    • /tmp/research_{session}/curated_context.md               │
│    • /cases/12345/documents/motion/extracted-text.txt         │
│    • /cases/12345/documents/complaint/extracted-text.txt      │
│                                                              │
│  Task: "You are a legal research analyst. Synthesize a       │
│         report addressing: {query}. Use the web research     │
│         and case documents provided."                        │
│                                                              │
│  Output: Final research report (Markdown + optional JSON)    │
└──────────────────────────────────────────────────────────────┘
```

---

## Where Exactly In The Code Does This Happen?

### The Insertion Point

The swap happens in `_process_sub_query()` at [researcher.py:527](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/researcher.py#L527):

```python
# CURRENT (line 527):
web_context = await self.researcher.context_manager.get_similar_content_by_query(
    sub_query, scraped_data
)

# PROPOSED: Replace with agent-based curation
web_context = await self.researcher.context_manager.get_agent_curated_context(
    sub_query, scraped_data, context_packet=self.researcher.context_packet
)
```

### But There's a Better Architectural Option

Instead of swapping at the per-sub-query level, we could intervene **higher up** — in `conduct_research()` itself. Currently, sub-queries run in parallel via `asyncio.gather`, each independently scraping and compressing. With agent-based curation, a better pattern might be:

1. **Run all sub-queries** → collect ALL scraped data (don't compress yet)
2. **Write all scraped data to temp directory** (one file per source)
3. **Run ONE curation agent** across all files (not 7 separate agent calls)
4. **Run ONE synthesis agent** with curated output + case docs

This is **more efficient** than calling an agent 7 times (once per sub-query). The agent sees all the research at once, can cross-reference between sub-query results, and eliminates redundant sources.

**The higher-level insertion point** would be in `_get_context_by_web_search()` at [researcher.py:266-365](file:///Users/ianbruce/code/gpt-researcher/gpt_researcher/skills/researcher.py#L266-L365):

```python
# CURRENT (lines 352-358):
context = await asyncio.gather(
    *[self._process_sub_query(sub_query, scraped_data, query_domains)
      for sub_query in sub_queries]
)
# Each sub-query independently scrapes AND compresses
# Returns: list of compressed context strings

# PROPOSED:
# Step 1: Scrape all sub-queries (keep scraping parallel)
all_scraped = await asyncio.gather(
    *[self._scrape_data_by_urls(sub_query, query_domains)
      for sub_query in sub_queries]
)

# Step 2: Write all scraped data to temp directory
session_dir = write_scraped_to_temp(all_scraped)

# Step 3: One agent curation call
curated = await agent_curate(session_dir, query, context_packet)

# Step 4: Return curated context (goes to generate_report)
return curated
```

---

## Key Design Decisions

### 1. CLI Agent vs. Gemini API Direct

| Approach | Pros | Cons |
|---|---|---|
| **Gemini CLI `-P` flag** | Consistent with WarRoom patterns, can use MCP tools, multi-step reasoning | Slower (process spawn), harder to capture structured output |
| **Gemini API (Python SDK)** | Fast, reliable JSON output, stays in-process | No tool use, single-shot only, requires API key management |

**Recommendation**: Start with **Gemini API direct** (simpler, faster). Upgrade to CLI agent if we need multi-step reasoning or MCP tool access during curation.

### 2. One Agent Call vs. Per-Sub-Query Agent Calls

| Approach | Pros | Cons |
|---|---|---|
| **One agent reads all scraped files** | Cross-referencing, deduplication, efficiency | Larger context window needed |
| **One agent per sub-query** | Smaller context per call, parallelizable | No cross-referencing, 7× latency if serial |

**Recommendation**: **One agent call** for all scraped data. With 20-50 files at ~5K tokens each, that's 100K-250K tokens — well within Gemini's 2M window.

### 3. What Happens To The Existing RAG Pipeline?

**Don't delete it.** Keep it as a fallback/configuration option:

```python
# In config:
SYNTHESIS_MODE = "agent"  # or "rag" (legacy) or "hybrid"
```

This lets us A/B test, fall back if the agent approach has issues, and maintain backward compatibility.

---

## Estimated Token Economics

| Approach | Input Tokens | Output Tokens | Approx Cost (Gemini 2.5 Pro) |
|---|---|---|---|
| Current RAG + generate_report | ~30K (compressed) | ~3K (report) | ~$0.10 |
| Agent curation + synthesis | ~200K (full scraped) + ~50K (case docs) | ~5K (curated) + ~3K (report) | ~$0.80 |

The agent approach costs ~8× more per research session. But for legal research where accuracy is critical, this is likely worth it. A missed case citation or a misunderstood argument from the opposing motion costs far more than $0.70.

---

## Summary

**What changes**:
- Scraped data is written to temp files instead of being chunked/embedded in memory
- An AI agent reads all scraped files and extracts relevant passages (replaces `ContextCompressor`)
- A second agent (or the same one) reads curated passages + case docs and produces the report (enhances `generate_report`)

**What stays the same**:
- Sub-query generation (with the context packet enhancement we already decided)
- Tavily search + Playwright scraping
- The overall `conduct_research()` → `write_report()` flow

**What we need to decide**:
1. Gemini API direct vs. CLI agent for the curation step?
2. Do both stages (curation + synthesis) or just one combined agent call?
3. Cost tolerance — is ~$0.80/session acceptable for legal research?
