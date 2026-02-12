# Strategy Workflow Overview

This document describes how the strategy development workflow operates, from initial user request to final deliverables. It covers both **offensive** (building claims) and **defensive** (responding to attacks) strategies.

---

## 1. Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STRATEGY DEVELOPMENT PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1           PHASE 2              PHASE 3           PHASE 4          │
│  [Intent]    →     [Transition]    →    [Analysis]   →    [Results]        │
│  Interactive       Trigger Point        Automated         Interactive       │
│                                                                             │
│  ┌─────────┐      ┌─────────────┐      ┌──────────┐      ┌──────────┐     │
│  │Converse │  →   │User says    │  →   │Script    │  →   │Present   │     │
│  │with user│      │"proceed" or │      │runs      │      │results & │     │
│  │         │      │"analyze"    │      │(auto)    │      │options   │     │
│  └─────────┘      └─────────────┘      └──────────┘      └──────────┘     │
│       ↓                                      ↓                  ↓          │
│  INTENT.md                            Files created       User decides     │
│  created                              automatically       next step        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Principle**: Phase 1 is conversational. Phase 2 is a trigger point (no conversation). Phase 3 is fully automated. Phase 4 is interactive results presentation.

---

## 2. Initiation: How the Workflow Starts

### Trigger Patterns

The workflow starts when the user expresses intent to build or respond to legal arguments:

| User Says | Workflow Type | Protocol |
|-----------|---------------|----------|
| "Help me file a complaint" | Offensive | `STRATEGY.md` |
| "I need to respond to this Motion to Dismiss" | Defensive | `STRATEGY_DEFENSIVE.md` |
| "Build a strategy for my breach of contract claim" | Offensive | `STRATEGY.md` |
| "They filed a summary judgment motion" | Defensive | `STRATEGY_DEFENSIVE.md` |

### Intent Conversation

The agent asks clarifying questions to establish:

**For Offensive Strategy:**
- What are we trying to accomplish? (file complaint, motion, etc.)
- What triggered this? (new case, deadline, etc.)
- What are the constraints? (jurisdiction, timeline, page limits)

**For Defensive Strategy:**
- What document are we responding to?
- What claims/counts are at risk?
- What's the deadline?
- What legal standard governs? (Rule 12(b)(6), Rule 56, etc.)

### File Created

At the end of the intent conversation, the agent creates:

```
strategies/[strategy_name]/INTENT.md
```

This file documents the objective, context, constraints, and success criteria.

---

## 3. The Transition Point: Conversation → Automation

### Critical Clarification

**There is NO intermediate conversation step between intent and script execution.**

The workflow is:
1. Intent conversation → `INTENT.md` created
2. User says "proceed" or "analyze" → Script runs immediately
3. Script auto-detects claims/attacks → No user confirmation needed

### What Triggers Script Execution

The user says something like:
- "Okay, analyze their motion"
- "Proceed with the analysis"
- "What's next?"
- "Go ahead"

### Agent Behavior at Transition

The agent should:
1. **NOT** ask "How many attacks are there?"
2. **NOT** have a "claim identification" conversation
3. **NOT** wait for user to list attacks/claims manually
4. **IMMEDIATELY** run the script with `--auto-detect` flag

**Example:**
```
User: "Okay, analyze their motion"

Agent: "I'll run the defensive strategy script with auto-detection.
        The script will automatically identify all attacks from the Motion to Dismiss
        and analyze each one. This will take approximately 5-10 minutes per attack."

[Agent runs script - no further conversation until results]
```

---

## 4. Script Execution: What Happens During Automation

### Command the Agent Runs

**Defensive Strategy:**
```bash
python3 scripts/strategy_relay_defensive.py \
  --case-folder . \
  --workspace [workspace_name] \
  --strategy [strategy_name] \
  --agent auggie \
  --auto-detect \
  --motion "Motion to Dismiss"
```

**Offensive Strategy:**
```bash
python3 scripts/strategy_relay.py \
  --case-folder . \
  --workspace [workspace_name] \
  --strategy [strategy_name] \
  --agent auggie
```

### Script Execution Model

**The script runs ONCE. It loops internally.**

```
Script called ONCE by agent
    ↓
Phase 0: Auto-detect attacks/claims (creates ATTACKS.json or CLAIMS.json)
    ↓
FOR EACH attack/claim:
    ├─ Phase A: Evidence/Element Analysis
    ├─ Phase B: Counter-Requirements/Element Extraction
    ├─ Phase C: Fact Matching
    ├─ Phase D: Viability/Rebuttal Scoring
    └─ Wait 5 seconds (rate limit protection)
    ↓
Phase E: Consolidated Gap Analysis
    ↓
Script exits
```

**The agent does NOT:**
- Call the script multiple times (once per attack)
- Manually loop through attacks
- Wait for user input between phases

### Phase Breakdown (Defensive)

| Phase | Name | Duration | Output |
|-------|------|----------|--------|
| 0 | Attack Detection | 2-3 min | `ATTACKS.json` |
| A | Evidence Analysis | 2-3 min | `EVIDENCE_ANALYSIS.json` |
| B | Counter-Requirements | 1-2 min | `counter_requirements.json` |
| C | Fact Matching | 2-3 min | Updates `counter_requirements.json` |
| D | Viability Analysis | 2-3 min | `analysis.md` |
| E | Gap Analysis | 2-3 min | `CONSOLIDATED_GAP_ANALYSIS.md` |

**Total time**: ~7-10 minutes per attack + 2-3 minutes for consolidation

### Error Handling

If a phase fails, the script:
1. Retries with exponential backoff (2s, 4s, 8s, 16s, 32s)
2. After 5 retries, logs the error and continues to next attack
3. Reports failures at the end

---

## 5. Files Produced

### Defensive Strategy Output

```
strategies/[strategy_name]/
├── INTENT.md                           # Phase 1 (conversation)
├── ATTACKS.json                        # Phase 0 (auto-detected)
├── CONSOLIDATED_GAP_ANALYSIS.md        # Phase E (final summary)
└── attacks/
    ├── 001_[attack_name]/
    │   ├── EVIDENCE_ANALYSIS.json      # Phase A
    │   ├── counter_requirements.json   # Phase B + C
    │   └── analysis.md                 # Phase D
    └── 002_[attack_name]/
        ├── EVIDENCE_ANALYSIS.json
        ├── counter_requirements.json
        └── analysis.md
```

### Offensive Strategy Output

```
strategies/[strategy_name]/
├── INTENT.md                           # Phase 1 (conversation)
├── CLAIMS.json                         # Phase 2 (conversation)
├── GAP_ANALYSIS.md                     # Phase 3 (final summary)
└── claims/
    ├── 001_[claim_name]/
    │   ├── elements.json               # Phase 3A
    │   └── analysis.md                 # Phase 3B-D
    └── 002_[claim_name]/
        ├── elements.json
        └── analysis.md
```

---

## 6. Results Presentation

After the script completes, the agent presents:

```
✅ Defensive strategy complete. Here's the summary:

**Attacks Analyzed: 8**

| Attack | Rebuttal Strength |
|--------|-------------------|
| 001 - Accord & Satisfaction | STRONG ✅ |
| 002 - Declaratory Judgment | MODERATE ⚠️ |
| ... | ... |

**Critical Gaps Identified: [N]**

Would you like me to:
1. Start legal research to fill the gaps
2. Proceed to outline generation
3. Review specific attack analyses
```

---

## 7. Key Differences: Offensive vs. Defensive

| Aspect | Offensive | Defensive |
|--------|-----------|-----------|
| **Trigger** | "File complaint", "Build claim" | "Respond to motion", "Defend against" |
| **Phase 2** | Claim identification (interactive) | Attack detection (automated) |
| **Root folder** | `claims/` | `attacks/` |
| **JSON file** | `CLAIMS.json` | `ATTACKS.json` |
| **Analysis focus** | What we must prove | What we must rebut |
| **Scoring** | Viability (can we win?) | Rebuttal strength (can we defend?) |
| **Script** | `strategy_relay.py` | `strategy_relay_defensive.py` |

**Critical Difference**: Offensive strategy has an interactive Phase 2 (user confirms claims). Defensive strategy auto-detects attacks in Phase 0 (no user confirmation needed).

