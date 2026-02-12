Let me think through this systematically. This is a critical architectural decision that affects everything downstream.

## The Core Tension

**WarRoom Side Generation:**

- ✅ Has full case context already loaded
- ✅ Agent already understands parties, claims, legal standards
- ✅ Can generate legally sophisticated queries
- ❌ Creates tight coupling between systems
- ❌ WarRoom agent must "know" how to generate good research queries

**GPT Researcher Side Generation:**

- ✅ Keeps research engine self-contained
- ✅ Single responsibility: "given context + query → produce research"
- ✅ Can evolve query generation independently
- ❌ Must receive and process case documents
- ❌ Adds latency (document transfer + context loading)

## My Assessment: **Hybrid Approach with GPT Researcher Doing the Heavy Lifting**

Here's why:

### 1. **Separation of Concerns (Architectural Principle)**

The WarRoom agent's job is **legal reasoning and drafting**. It should know:

- "I need research on qualified immunity for this motion"
- "I need case law on Twombly pleading standards"
- "I need research on damages calculations in employment discrimination"

The GPT Researcher's job is **research execution**. It should know:

- "Given this legal issue + case context, what are the 5-7 specific questions I need to answer?"
- "How do I translate 'qualified immunity' into searchable queries that will find relevant case law?"

**Why this matters:** Legal reasoning ≠ Research query formulation. They're different skills.

A WarRoom agent might think: "I need to argue that the plaintiff failed to state a claim under Twombly/Iqbal."

But the *research queries* should be:

- "Twombly Iqbal pleading standard motion to dismiss"
- "factual allegations plausibility standard federal courts"
- "dismissal failure to state claim Rule 12(b)(6) recent cases"
- "heightened pleading requirements [specific circuit]"

The WarRoom agent shouldn't have to know how to decompose its legal need into optimal search queries. That's the researcher's job.

### 2. **The Local Documents Question: They Should HEAVILY Inform Sub-Queries**

This is critical. Here's the flow I envision:

**Input to GPT Researcher:**

```json
{
  "main_query": "Research qualified immunity defense for Officer Johnson's motion to dismiss",
  "case_context": {
    "complaint_text": "full text of complaint",
    "motion_text": "full text of defendant's motion", 
    "case_summary": "plaintiff alleges excessive force during arrest..."
  },
  "research_goal": "opposition_brief" // or "motion_support", "discovery_strategy", etc.
}
```

**Sub-Query Generation Process (Inside GPT Researcher):**

The sub-query generator should:

1. **Read the motion** to understand what arguments the defendant is making
2. **Read the complaint** to understand what facts are alleged
3. **Understand the legal posture** (motion to dismiss vs. summary judgment vs. trial)
4. **Generate queries that directly address the gaps**

Example: If the motion argues "no clearly established right," the sub-queries should include:

- "clearly established law excessive force [specific circuit] [year range]"
- "qualified immunity factual disputes motion to dismiss"
- "Hope v. Pelzer clearly established right standard"

**Why this is better than WarRoom-side generation:**

- The WarRoom agent can stay high-level: "I need to oppose this qualified immunity argument"
- The GPT Researcher reads the actual motion and generates queries that respond to the *specific arguments made*
- If the motion cites 3 cases, the researcher can generate queries to find distinguishing authority

### 3. **The Practical Implementation**

**Step 1: WarRoom sends a research request**

```python
# WarRoom side (simplified)
research_request = {
    "query": "Research to oppose qualified immunity defense",
    "case_id": "12345",
    "doc_paths": [
        "/cases/12345/documents/complaint/extracted-text.txt",
        "/cases/12345/documents/motion-to-dismiss/extracted-text.txt"
    ],
    "research_type": "opposition_brief"
}
```

**Step 2: GPT Researcher loads documents and generates sub-queries**

```python
# GPT Researcher side
async def plan_research_with_context(query, case_docs, research_type):
    # Load the actual case documents
    complaint = read_file(case_docs['complaint'])
    motion = read_file(case_docs['motion'])
  
    # Generate context-aware sub-queries
    prompt = f"""
    You are a legal research specialist. 
  
    CASE CONTEXT:
    Complaint: {complaint}
    Motion to Dismiss: {motion}
  
    RESEARCH GOAL: {query}
    PURPOSE: {research_type}
  
    Generate 5-7 specific search queries that will find:
    1. Case law that directly addresses the arguments in the motion
    2. Distinguishing authority for cases cited by defendant
    3. Factual parallels to this case
    4. Recent developments in this area of law
  
    Return as JSON array of query strings.
    """
  
    sub_queries = await llm.generate(prompt)
    return sub_queries
```

**Step 3: Execute research with those queries**

- Use Tavily to search each sub-query
- Scrape the results
- Synthesize (we'll address this in Problem 3)

### 4. **Why Not WarRoom-Side Generation?**

If WarRoom generates the queries, you get:

**Option A: Generic queries (bad)**

```python
# WarRoom agent generates:
queries = [
    "qualified immunity",
    "excessive force",
    "motion to dismiss"
]
# These are too broad, will return garbage
```

**Option B: Detailed queries (tight coupling)**

```python
# WarRoom agent generates:
queries = [
    "qualified immunity clearly established law Ninth Circuit 2020-2024",
    "excessive force handcuffing arrest qualified immunity",
    "Hope v. Pelzer clearly established right standard"
]
# Now WarRoom needs to know:
# - How to format search queries
# - What date ranges to use
# - What jurisdictional filters to apply
# - How many queries to generate
# This is research engine logic leaking into the legal reasoning layer
```

### 5. **The Feedback Loop Benefit**

With GPT Researcher doing sub-query generation:

**Iteration 1:** Basic implementation

- Takes case docs + main query
- Generates sub-queries
- Returns research

**Iteration 2:** Learn from results

- Track which sub-queries produced useful results
- Refine the sub-query generation prompt
- Add domain-specific query patterns (e.g., "always include circuit + year range for case law")

**Iteration 3:** Specialization

- Different sub-query strategies for different research types:
  - Motion to dismiss → focus on pleading standards + factual sufficiency
  - Summary judgment → focus on genuine disputes of material fact
  - Damages → focus on calculation methods + comparable cases

**If WarRoom does it:** You have to update the WarRoom agent every time you improve research query generation.

**If GPT Researcher does it:** You improve the research engine once, all WarRoom agents benefit.

## My Recommendation

**Architecture:**

```
WarRoom Agent (Legal Reasoning)
    ↓
    Sends: {
        main_query: "high-level legal need",
        case_docs: [file paths],
        research_type: "opposition_brief"
    }
    ↓
GPT Researcher (Research Execution)
    ↓
    1. Load case documents (full text)
    2. Generate 5-7 context-aware sub-queries
    3. Execute searches (Tavily)
    4. Scrape results
    5. Synthesize (Problem 3)
    ↓
    Returns: Research report + sources
    ↓
WarRoom Agent (Legal Reasoning)
    Uses research to draft opposition brief
```

**Key Principles:**

1. **WarRoom stays high-level:** "I need research on X"
2. **GPT Researcher reads case docs:** Understands the specific arguments and facts
3. **Sub-queries are context-aware:** Generated based on actual motion arguments, not generic legal topics
4. **Single responsibility:** Research engine owns the entire research pipeline
5. **Loose coupling:** WarRoom doesn't need to know how research works internally

**The Local Documents Role:**

- **Critical for sub-query generation:** The motion/complaint should heavily inform what questions to ask
- **Also used in synthesis:** The agent should read them alongside web research to produce integrated analysis

Does this align with your thinking, or do you see flaws in this approach?
