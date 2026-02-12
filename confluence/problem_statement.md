# Problem Statement: Legal Research API

*Distilled from the discussion transcription and orientation documents.*

---

## What We Are Building

We have **two applications**:

- **WarRoom** (Laravel) — The main application. This is where reasoning, drafting, and case management happens. AI agents (Gemini CLI, Auggie CLI) live here and perform multi-step legal workflows.
- **GPT Researcher** (Python) — An open-source research engine. It takes a query, generates sub-queries, searches the web, scrapes URLs, and synthesizes results into a report.

**The goal**: Turn GPT Researcher into a **Legal Research API** that WarRoom can call. But not as-is — we want to **supercharge** the workflow by leveraging the AI agents and case documents that already exist on the WarRoom side.

---

## The Three Core Problems

### Problem 1: Sub-Query Generation Is the Foundation

> *"The sub-queries are pretty much the foundation of the research. You get the best information based on the questions that you ask."*

**Current behavior**: GPT Researcher takes a bare query string and uses an LLM to break it into sub-queries. It has zero awareness of the case — who the parties are, what claims are at issue, what the opposing motion argues.

**What we need**: Sub-queries that are informed by case context — the complaint, the motion, the user's narrative, the specific legal standards.

**The core question**: Should we generate sub-queries on the **WarRoom side** (where the agent already has full case context), or should we pass case context to the **GPT Researcher side** and let it generate smarter sub-queries?

This is not trivial. The quality of research depends entirely on the quality of the questions asked.

---

### Problem 2: Search & Scrape — Leave It Alone (For Now)

> *"The scraping is pretty well thought out. I don't think we need to [change it] at this stage."*

**Current behavior**: GPT Researcher uses Tavily for search and Playwright/BeautifulSoup for scraping.

**Assessment**: This works. We *could* use Gemini CLI or Auggie CLI's web search capabilities, but there's no strong reason to change this right now. The real gaps are elsewhere.

**Decision**: Keep Tavily + Playwright for web search/scrape. Focus energy on Problems 1 and 3.

---

### Problem 3: Synthesis — Replace RAG with Agent-Driven Full-Context Reading

> *"We have these CLI agents that can live on the machine and they can read a document or a set of documents, rather than utilizing a RAG API to possibly be accurate."*

**This is the biggest opportunity.**

**Current behavior**: GPT Researcher uses a RAG pipeline:
1. Chunk scraped content (1000 chars).
2. Embed chunks on-the-fly.
3. Query embeddings by similarity (≥ 0.35).
4. Pass only matching chunks to the LLM for synthesis.

**The problem for legal work**: A 30-page Motion to Dismiss becomes ~100 chunks. The LLM sees maybe 15 of them. It loses the thread of the argument. It can't connect Paragraph 12 to Exhibit B because they're in different chunks.

**What we want instead**: An **agent swarm** (or a single agent with a massive context window) that reads the **full text** of:
- The scraped web research results.
- The actual case documents (motions, contracts, correspondence).

And produces a synthesis that understands the entire context.

**Why this is feasible now**: Gemini has a 2 million token context window. A 30-page PDF is ~15,000 tokens. We can skip chunking and embedding entirely for most use cases.

**The question**: Do we replace the RAG pipeline entirely, or keep it as a fallback? Should we use an **agent swarm** (multiple agents each reading a subset) or a **single large-context agent**?

---

## The Practical Question: Case Documents Are Already Extracted

> *"We've been using Mistral API to extract the text. So we can get a motion, a 20 or 30 page motion, and we can literally provide that in full text form for an agent to read."*

We don't need to solve OCR or PDF extraction — that's already handled by Mistral on the WarRoom side. Every case document already has an `extracted-text.txt` file sitting next to it.

**The question is purely about transfer**: How do we get those extracted text files to the GPT Researcher side?

**Answer**: If both apps are on the **same server** (which is the plan), we just point GPT Researcher's `DOC_PATH` at the case folder. No serialization, no API transfer of megabytes of text. Just file paths.

---

## Summary of Open Questions

| # | Question | Options |
|---|---|---|
| 1 | **Where do sub-queries get generated?** | WarRoom-side (has context) vs. Python-side (single pipeline) vs. hybrid (WarRoom sends "seed" context) |
| 2 | **How do we replace the synthesis step?** | Agent swarm reading full docs vs. single large-context agent vs. keep RAG as fallback |
| 3 | **What does the API look like?** | REST endpoint vs. CLI subprocess vs. shared filesystem |
| 4 | **What format does the output take?** | Structured JSON (for strategy relay consumption) vs. Markdown (for human review) vs. both |
| 5 | **Same server confirmed?** | If yes, case docs are just file paths. If no, we need a data transfer strategy. |
