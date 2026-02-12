#!/usr/bin/env python3
"""
Strategy Relay (Defensive) - The "Relay Race" for Defensive Legal Strategy

This script orchestrates multiple LLM calls to analyze attacks from opposing counsel
and build rebuttals. Each phase uses a different "costume" (role) but passes artifacts
(files) as the baton.

PHASES:
  0. Attack Detector     - (Optional) Auto-extract attacks from opposing motion
  A. Evidence Analyst    - Analyze what evidence they provided, identify gaps
  B. Counter-Requirement + Fact Matching - Extract counter-requirements AND map case facts to each
  D. Viability Analyst   - Score rebuttal strength, adversarial check
  E. Gap Reporter        - Aggregate into gap analysis

Usage:
    # Full automation - auto-detect attacks from a motion
    python scripts/strategy_relay_defensive.py --case-folder ./app-context/case-123 --workspace ws_name --strategy my_strategy --auto-detect --motion "Motion to Dismiss"

    # Manual - use existing ATTACKS.json
    python scripts/strategy_relay_defensive.py --case-folder ./app-context/case-123 --workspace ws_name --strategy 001_defensive_strategy

    # Process single attack
    python scripts/strategy_relay_defensive.py --case-folder ./app-context/case-123 --workspace ws_name --strategy 001_defensive_strategy --attack 002
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import shared utilities with monitoring support
from strategy_utils import (
    log,
    run_agent,
    load_json_file,
    build_context_string,
)

# Configuration
DEFAULT_AGENT = "auggie"
SUPPORTED_AGENTS = ["auggie", "gemini"]


# Wrapper function to call strategy_utils.run_agent with monitoring support
def run_agent_defensive(agent: str, role: str, task: str, context: str, cwd: Path,
                        max_retries: int = 5, timeout: int = 600, phase_name: str = "agent_call",
                        output_file: str = None) -> str:
    """
    Wrapper to call strategy_utils.run_agent with monitoring support.

    This enables real-time monitoring via .strategy_monitor/ directory.
    When output_file is set, the agent writes directly to that file.
    """
    return run_agent(
        agent=agent,
        role=role,
        task=task,
        context=context,
        cwd=cwd,
        max_retries=max_retries,
        timeout=timeout,
        phase_name=phase_name,
        output_file=output_file
    )


# =============================================================================
# PHASE 0: ATTACK DETECTOR (Auto-Extract)
# =============================================================================

def phase_0_detect_attacks(
    agent: str,
    case_folder: Path,
    strategy_dir: Path,
    motion_search_term: str,
    file_search_store_id: Optional[str] = None
) -> Path:
    """
    Phase 0: The Attack Detector

    Automatically read the opposing motion and extract attacks.
    Creates ATTACKS.json so the relay can proceed.

    This enables full automation - user just says "analyze the MTD" and we go.
    """
    case_context_dir = case_folder / "case-context"
    documents_dir = case_folder / "documents"

    # Build context from case files
    context_files = [
        case_context_dir / "case_summary.md",
        case_context_dir / "documents_index.json",
        case_context_dir / "user_narrative.md",
    ]
    context = build_context_string(context_files)

    # File search instructions
    if file_search_store_id:
        file_search_note = f"""
You have access to semantic document search via `file_search_query_legal-hub`.
Store ID: {file_search_store_id}

Use this to find and read the opposing motion:
- Query: "What are the arguments in the {motion_search_term}?"
- Query: "What claims does the defendant attack in their motion?"
- Query: "What legal theories does the motion rely on?"

You can also query for specific details about each argument.
"""
    else:
        file_search_note = f"""
Review the documents_index.json to find the {motion_search_term}.
Read the document to extract the attacks.
"""

    output_file = strategy_dir / "ATTACKS.json"

    task = f"""You are analyzing an opposing motion to extract the ATTACKS we must defend against.

Search Term: "{motion_search_term}"

Your job:
1. FIND the opposing motion in the case documents
2. READ the motion carefully
3. EXTRACT each distinct attack/argument they make
4. For each attack, identify:
   - What claims/counts it targets
   - Their core argument
   - Cases they cite
   - How dangerous this attack is (high/medium/low)

{file_search_note}

**IMPORTANT**:
- Each attack should be a DISTINCT argument, not a sub-point
- Group related sub-arguments under one attack
- Identify the governing standard (e.g., Rule 12(b)(6) for MTD)

OUTPUT: Write a JSON file to {output_file} with this exact structure:

{{
  "strategy_id": "{strategy_dir.name}",
  "strategy_type": "defensive",
  "responding_to": {{
    "document": "[Full name of the motion]",
    "filed_by": "[Who filed it]",
    "filed_date": "[Date if known, otherwise null]"
  }},
  "governing_standard": "[e.g., Rule 12(b)(6) - Failure to State a Claim]",
  "attacks": [
    {{
      "id": "001",
      "name": "[Short descriptive name for this attack]",
      "targets": ["Count I", "Count II"],
      "opposing_argument": "[Their argument in 2-3 sentences]",
      "cases_cited_by_opponent": ["Case 1", "Case 2"],
      "danger_level": "high|medium|low",
      "status": "confirmed"
    }}
  ],
  "auto_detected": true,
  "detected_at": "{datetime.now().isoformat()}"
}}

Be thorough - capture ALL distinct attacks in the motion."""

    log(f"Phase 0: Auto-detecting attacks from '{motion_search_term}'", "PHASE")

    run_agent_defensive(
        agent=agent,
        role="Legal Analyst - Motion decomposition specialist",
        task=task,
        context=context,
        cwd=case_folder,
        phase_name="Phase_0_Attack_Detection",
        output_file=str(output_file)
    )

    # Verify the agent wrote the file
    if not output_file.exists():
        log(f"Agent did not create ATTACKS.json at {output_file}", "ERROR")
        return None

    # Validate it's parseable JSON
    data = load_json_file(output_file)
    if not data or not data.get("attacks"):
        log(f"ATTACKS.json is empty or has no attacks", "ERROR")
        return None

    num_attacks = len(data.get("attacks", []))
    log(f"  → Detected {num_attacks} attacks", "DONE")
    log(f"  → Created: ATTACKS.json", "DONE")

    return output_file


# =============================================================================
# PHASE A: EVIDENCE ANALYST
# =============================================================================

def phase_a_evidence_analysis(
    agent: str,
    attack: dict,
    case_folder: Path,
    output_dir: Path,
    file_search_store_id: Optional[str] = None
) -> Path:
    """
    Phase A: The Evidence Analyst

    Analyze what evidence opposing counsel provided (or failed to provide).
    Identify gaps in their proof. Apply burden-shifting frameworks.

    This is the CRITICAL phase that surfaces arguments like:
    - "CPS not named as assignee in contract"
    - "No chain of title documentation"
    - "Burden not met under O.C.G.A. § 11-3-308"
    """
    attack_id = attack["id"]
    attack_name = attack["name"]
    targets = attack.get("targets", [])
    their_argument = attack.get("opposing_argument", attack.get("their_argument", ""))

    # Build context from case documents
    case_context_dir = case_folder / "case-context"
    documents_dir = case_folder / "documents"

    context_files = [
        case_context_dir / "case_summary.md",
        case_context_dir / "documents_index.json",
    ]
    context = build_context_string(context_files)

    # Add attack details to context
    context += f"""

=== ATTACK BEING ANALYZED ===
Attack ID: {attack_id}
Attack Name: {attack_name}
Claims Targeted: {', '.join(targets)}
Their Argument: {their_argument}
"""

    # File search instructions
    if file_search_store_id:
        file_search_note = f"""
You have access to semantic document search via `file_search_query_legal-hub`.
Store ID: {file_search_store_id}

Use this to query case documents, e.g.:
- "What does the contract say about assignment?"
- "Who is named as the creditor in the contract?"
- "What documents did CPS provide in their validation response?"
"""
    else:
        file_search_note = """
Review the documents_index.json to understand what documents are available.
Read specific documents as needed using their file paths.
"""

    output_file = output_dir / "EVIDENCE_ANALYSIS.json"

    task = f"""You are analyzing the EVIDENCE that opposing counsel relies on for this attack.

Your job is to:

1. IDENTIFY what evidence they cite or rely on
   - What documents did they attach?
   - What facts do they assert?
   - What do they claim their evidence proves?

2. ANALYZE what their evidence ACTUALLY shows
   - Read the actual documents (use file search or local files)
   - What do the documents actually say vs. what they claim?
   - Who is named in the documents?
   - What's MISSING from the documents?

3. APPLY burden-shifting analysis
   - Under the applicable legal standard, who has the burden of proof?
   - Has opposing counsel met their burden?
   - What gaps exist in their proof?

4. SURFACE additional arguments
   - Based on evidence gaps, what arguments can we make?
   - What did they fail to prove?
   - What assumptions are they making without support?
   - For legal basis of arguments, use the `search_cases_legal-hub` tool or `quick_search_legal-hub` tool to find real authority. Never invent citations.

{file_search_note}

OUTPUT: Write a JSON file to {output_file} with this exact structure:

{{
  "attack_id": "{attack_id}",
  "attack_name": "{attack_name}",
  "evidence_they_rely_on": [
    {{
      "document": "[Document name/description]",
      "what_they_claim": "[What they say it proves]",
      "what_it_actually_shows": "[What it actually says]",
      "gaps_identified": ["Gap 1", "Gap 2"],
      "document_level_findings": {{
        "parties_named": "[Who is named]",
        "key_missing_elements": ["Missing 1", "Missing 2"]
      }}
    }}
  ],
  "burden_analysis": {{
    "applicable_standard": "[Legal standard/statute]",
    "who_has_burden": "[Which party]",
    "burden_met": false,
    "why_not": "[Explanation]"
  }},
  "additional_arguments_surfaced": [
    {{
      "argument": "[The argument]",
      "legal_basis": "[Statute or case law]",
      "factual_support": "[What facts support this]"
    }}
  ]
}}"""

    log(f"Phase A: Analyzing evidence for Attack {attack_id}: {attack_name}", "PHASE")

    run_agent_defensive(
        agent=agent,
        role="Evidence Analyst - Document examiner and gap identifier",
        task=task,
        context=context,
        cwd=case_folder,
        phase_name=f"Phase_A_Evidence_{attack_id}",
        output_file=str(output_file)
    )

    # Verify the agent wrote the file
    if output_file.exists():
        log(f"  → Created: {output_file.name}", "DONE")
    else:
        log(f"Agent did not create {output_file.name}", "ERROR")

    return output_file


# =============================================================================
# PHASE B: COUNTER-REQUIREMENT EXTRACTOR + FACT MATCHING (merged)
# =============================================================================

def phase_b_counter_requirements(
    agent: str,
    attack: dict,
    evidence_analysis_file: Path,
    case_folder: Path,
    output_dir: Path,
    file_search_store_id: Optional[str] = None
) -> Path:
    """
    Phase B: Counter-Requirement Extraction + Fact Matching (merged)

    Based on the evidence analysis:
    1. Extract what we must prove to rebut this attack (counter-requirements)
    2. Research legal standards for each counter-requirement
    3. Map case document facts to each counter-requirement with evidence strength

    Previously this was two phases (B + C). Merged to save one full agent call per attack.
    """
    attack_id = attack["id"]
    attack_name = attack["name"]
    jurisdiction = attack.get("jurisdiction", "Georgia")

    # Load evidence analysis
    evidence_analysis = load_json_file(evidence_analysis_file)

    # Build document manifest for fact matching
    case_context_dir = case_folder / "case-context"
    documents_index = load_json_file(case_context_dir / "documents_index.json")

    # Build context
    context = f"""
=== EVIDENCE ANALYSIS (from Phase A) ===
{json.dumps(evidence_analysis, indent=2)}

=== ATTACK DETAILS ===
Attack ID: {attack_id}
Attack Name: {attack_name}
Their Argument: {attack.get('opposing_argument', attack.get('their_argument', ''))}

=== AVAILABLE CASE DOCUMENTS ===
{json.dumps(documents_index, indent=2)}
"""

    # File search instructions
    if file_search_store_id:
        file_search_note = f"""
You have semantic document search via the `file_search_query_legal-hub` tool.
Store ID: {file_search_store_id}

Use this to find facts in case documents:
- "What evidence supports [requirement]?"
- "What does the contract say about [topic]?"
- "What facts relate to [issue]?"
"""
    else:
        file_search_note = """
Review the documents_index.json above and read specific documents as needed to find supporting facts.
"""

    output_file = output_dir / "counter_requirements.json"

    task = f"""Based on the evidence analysis, extract the COUNTER-REQUIREMENTS needed to rebut this attack,
AND map specific facts from case documents to each counter-requirement.

A counter-requirement is something WE must prove to defeat THEIR argument.

## PART 1: Counter-Requirement Extraction

For each counter-requirement, determine:
1. What must we prove?
2. What is the legal basis? Use the `search_cases_legal-hub` tool and `deep_research_legal-hub` tool to find REAL statutes and case law. Never invent citations.
3. How do we establish this?

Consider:
- Arguments that REFRAME their attack (e.g., "This isn't 'show me the note' - it's contract authenticity")
- Arguments based on EVIDENCE GAPS (e.g., "No assignment documentation")
- Arguments based on BURDEN-SHIFTING (e.g., "They failed to meet their burden under § 11-3-308")
- Arguments that the FACTUAL DISPUTE survives the motion standard

## PART 2: Fact Matching

For EACH counter-requirement you identify, search the case documents for supporting facts:
1. Find the specific fact from our documents
2. Note the source document
3. Rate evidence strength (strong/moderate/weak)
4. Update status based on evidence found (proven/disputed/unproven)

{file_search_note}

Be thorough but accurate. Only cite facts that actually exist in the documents.

Jurisdiction: {jurisdiction}

## IMPORTANT: Tool Usage
- Use the `search_cases_legal-hub` tool to find relevant case law for each counter-requirement
- Use the `deep_research_legal-hub` tool for complex legal questions requiring comprehensive analysis
- Use the `lookup_citation_legal-hub` tool to verify any specific citation before including it
- Use the `quick_search_legal-hub` tool for quick factual lookups on statutes or standards

OUTPUT: Write a JSON file to {output_file} with this exact structure:

{{
  "attack_id": "{attack_id}",
  "attack_name": "{attack_name}",
  "jurisdiction": "{jurisdiction}",
  "counter_requirements": [
    {{
      "id": "CR1",
      "requirement": "[What we must prove/argue]",
      "legal_basis": "[Statute or case citation - MUST BE REAL, verified via MCP tools]",
      "how_to_prove": "[How we establish this]",
      "our_facts": [
        {{
          "fact": "[Specific fact from case documents]",
          "source": "[Document name/path]",
          "strength": "strong|moderate|weak",
          "notes": "[Any relevant notes]"
        }}
      ],
      "status": "proven|disputed|unproven"
    }}
  ],
  "rebuttal_summary": "[2-3 sentence summary of our rebuttal strategy]"
}}"""

    log(f"Phase B: Extracting counter-requirements + fact matching for Attack {attack_id}", "PHASE")

    run_agent_defensive(
        agent=agent,
        role="Legal Research Clerk - Counter-argument and fact-mapping specialist",
        task=task,
        context=context,
        cwd=case_folder,
        phase_name=f"Phase_B_Counter_Req_{attack_id}",
        output_file=str(output_file)
    )

    # Verify the agent wrote the file
    if output_file.exists():
        log(f"  → Created: {output_file.name}", "DONE")
    else:
        log(f"Agent did not create {output_file.name}", "ERROR")

    return output_file


# =============================================================================
# PHASE D: VIABILITY ANALYST
# =============================================================================

def phase_d_viability_analysis(
    agent: str,
    attack: dict,
    evidence_analysis_file: Path,
    counter_req_file: Path,
    output_dir: Path,
    case_folder: Path
) -> Path:
    """
    Phase D: The Viability Analyst

    Score rebuttal strength and run adversarial check.
    Generate analysis.md for this attack.
    """
    attack_id = attack["id"]
    attack_name = attack["name"]

    # Load artifacts
    evidence_analysis = load_json_file(evidence_analysis_file)
    counter_reqs = load_json_file(counter_req_file)

    context = f"""
=== EVIDENCE ANALYSIS ===
{json.dumps(evidence_analysis, indent=2)}

=== COUNTER-REQUIREMENTS ===
{json.dumps(counter_reqs, indent=2)}
"""

    output_file = output_dir / "analysis.md"

    task = f"""Analyze the rebuttal strength for Attack {attack_id}: {attack_name}

Your analysis must include:

1. REBUTTAL STRENGTH SCORE
   - STRONG: All counter-requirements proven, evidence gaps identified, burden analysis favorable
   - MODERATE: Most counter-requirements supported, some gaps in our evidence
   - WEAK: Critical counter-requirements unproven
   - FATAL: Cannot rebut this attack

2. COUNTER-REQUIREMENT SUMMARY TABLE
   For each CR: Status (✅/⚠️/❌) and evidence strength

3. THE CRITICAL DISTINCTIONS
   How do we distinguish our position from what they claim?
   (e.g., "This is contract authenticity, not 'show me the note'")

4. ADVERSARIAL CHECK
   Role-play as opposing counsel responding to our rebuttal.
   - What will they say?
   - How do we handle their surrebuttal?

5. EVIDENCE MAPPED
   List all evidence supporting our rebuttal, organized by category.

6. GAPS AND RECOMMENDATIONS
   - What's still missing?
   - What discovery would help?

OUTPUT: Write a MARKDOWN file to {output_file}. Start the file with this header:

# Analysis: {attack_name}

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Attack ID**: {attack_id}

---

Then write the full analysis with clear sections."""

    log(f"Phase D: Analyzing viability for Attack {attack_id}", "PHASE")

    run_agent_defensive(
        agent=agent,
        role="Senior Litigator - Strategic case analyst",
        task=task,
        context=context,
        cwd=case_folder,
        phase_name=f"Phase_D_Viability_{attack_id}",
        output_file=str(output_file)
    )

    # Verify the agent wrote the file
    if output_file.exists():
        log(f"  → Created: {output_file.name}", "DONE")
    else:
        log(f"Agent did not create {output_file.name}", "ERROR")

    return output_file


# =============================================================================
# PHASE E: GAP REPORTER
# =============================================================================

def phase_e_gap_analysis(
    agent: str,
    strategy_dir: Path,
    case_folder: Path
) -> Path:
    """
    Phase E: The Gap Reporter

    Aggregate all attack analyses into a consolidated gap analysis.
    """
    # Gather all artifacts
    evidence_files = list(strategy_dir.glob("attacks/*/EVIDENCE_ANALYSIS.json"))
    counter_req_files = list(strategy_dir.glob("attacks/*/counter_requirements.json"))
    analysis_files = list(strategy_dir.glob("attacks/*/analysis.md"))

    # Load ATTACKS.json for overview
    attacks_file = strategy_dir / "ATTACKS.json"
    attacks_data = load_json_file(attacks_file)

    # Build context
    context = f"""
=== ATTACKS OVERVIEW ===
{json.dumps(attacks_data, indent=2)}

"""

    for ef in evidence_files:
        context += f"\n=== {ef.parent.name}/EVIDENCE_ANALYSIS.json ===\n"
        context += json.dumps(load_json_file(ef), indent=2)

    for cf in counter_req_files:
        context += f"\n=== {cf.parent.name}/counter_requirements.json ===\n"
        context += json.dumps(load_json_file(cf), indent=2)

    for af in analysis_files:
        context += f"\n=== {af.parent.name}/analysis.md ===\n"
        context += af.read_text(encoding="utf-8")

    output_file = strategy_dir / "GAP_ANALYSIS.md"

    task = f"""Create a consolidated GAP ANALYSIS report across all attacks.

Include:

1. EXECUTIVE SUMMARY
   - Overall defense strength
   - Number of attacks and rebuttal scores
   - Critical risks

2. ATTACK STATUS TABLE
   | Attack | Rebuttal Strength | Key Argument | Key Risk |

3. EVIDENCE INVENTORY
   | Evidence | Supports Which Attack | Strength |

4. CRITICAL GAPS
   For each gap:
   - Which attack it affects
   - What's missing
   - How to address it

5. PRIORITY ACTIONS
   Ordered list of next steps

6. STRATEGIC RECOMMENDATION
   Overall recommendation for the response

OUTPUT: Write a MARKDOWN file to {output_file}. Start the file with this header:

# Gap Analysis - Defensive Strategy

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Strategy**: {strategy_dir.name}

---

Then write the full gap analysis with clear sections."""

    log(f"Phase E: Generating gap analysis", "PHASE")

    run_agent_defensive(
        agent=agent,
        role="Senior Litigation Partner - Strategic advisor",
        task=task,
        context=context,
        cwd=case_folder,
        phase_name="Phase_E_Gap_Analysis",
        output_file=str(output_file)
    )

    # Verify the agent wrote the file
    if output_file.exists():
        log(f"  → Created: GAP_ANALYSIS.md", "DONE")
    else:
        log(f"Agent did not create GAP_ANALYSIS.md", "ERROR")

    return output_file


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Strategy Relay (Defensive) - Legal Defense Analysis Pipeline"
    )
    parser.add_argument(
        "--case-folder",
        required=True,
        help="Path to the case folder (e.g., ./app-context/consumer-portfolio-123)"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Name of the workspace (e.g., mtd_response_20260127)"
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Name of the strategy to analyze (e.g., 001_defensive_strategy)"
    )
    parser.add_argument(
        "--agent",
        default=DEFAULT_AGENT,
        choices=SUPPORTED_AGENTS,
        help="Which agent to use (default: gemini)"
    )
    parser.add_argument(
        "--attack",
        help="Process only a specific attack ID (e.g., 002)"
    )
    parser.add_argument(
        "--skip-evidence",
        action="store_true",
        help="Skip evidence analysis (use existing EVIDENCE_ANALYSIS.json)"
    )
    parser.add_argument(
        "--skip-counter-req",
        action="store_true",
        help="Skip counter-requirement extraction (use existing)"
    )
    # Auto-detect options
    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="Auto-detect attacks from the opposing motion (creates ATTACKS.json)"
    )
    parser.add_argument(
        "--motion",
        default="Motion to Dismiss",
        help="Search term to find the opposing motion (default: 'Motion to Dismiss')"
    )

    args = parser.parse_args()

    # Resolve paths
    case_folder = Path(args.case_folder).resolve()
    workspace_dir = case_folder / "workspaces" / args.workspace
    strategy_dir = workspace_dir / "strategies" / args.strategy
    attacks_file = strategy_dir / "ATTACKS.json"

    # Validate paths
    if not case_folder.exists():
        log(f"Case folder not found: {case_folder}", "ERROR")
        sys.exit(1)

    if not workspace_dir.exists():
        log(f"Workspace not found: {workspace_dir}", "ERROR")
        sys.exit(1)

    # Create strategy directory if it doesn't exist
    strategy_dir.mkdir(parents=True, exist_ok=True)

    # Check for file search store ID
    settings_file = case_folder / "case-context" / "settings.json"
    settings = load_json_file(settings_file)
    file_search_store_id = settings.get("file_search_store_id")

    # Phase 0: Auto-detect attacks if requested
    if args.auto_detect:
        log(f"=" * 60, "INFO")
        log(f"PHASE 0: AUTO-DETECT ATTACKS", "START")
        log(f"=" * 60, "INFO")
        log(f"Searching for: {args.motion}")

        attacks_file = phase_0_detect_attacks(
            agent=args.agent,
            case_folder=case_folder,
            strategy_dir=strategy_dir,
            motion_search_term=args.motion,
            file_search_store_id=file_search_store_id
        )

        if attacks_file is None:
            log("Failed to auto-detect attacks. Check the raw output.", "ERROR")
            sys.exit(1)

    # Validate ATTACKS.json exists
    if not attacks_file.exists():
        log(f"ATTACKS.json not found: {attacks_file}", "ERROR")
        log("Either run with --auto-detect or create ATTACKS.json manually", "INFO")
        sys.exit(1)

    # Load attacks
    attacks_data = load_json_file(attacks_file)
    attacks = attacks_data.get("attacks", [])

    if not attacks:
        log("No attacks found in ATTACKS.json", "ERROR")
        sys.exit(1)

    # Filter to specific attack if requested
    if args.attack:
        attacks = [a for a in attacks if a["id"] == args.attack]
        if not attacks:
            log(f"Attack {args.attack} not found", "ERROR")
            sys.exit(1)

    # Start the relay
    log(f"=" * 60, "INFO")
    log(f"DEFENSIVE STRATEGY RELAY", "START")
    log(f"=" * 60, "INFO")
    log(f"Case Folder: {case_folder.name}")
    log(f"Workspace: {args.workspace}")
    log(f"Strategy: {args.strategy}")
    log(f"Agent: {args.agent}")
    log(f"Attacks to process: {len(attacks)}")
    if file_search_store_id:
        log(f"File Search: {file_search_store_id}")
    log(f"=" * 60, "INFO")

    # Process each attack
    for attack in attacks:
        attack_id = attack["id"]
        attack_name_slug = attack["name"].lower().replace(" ", "_").replace("-", "_")[:30]
        attack_dir = strategy_dir / "attacks" / f"{attack_id}_{attack_name_slug}"
        attack_dir.mkdir(parents=True, exist_ok=True)

        log(f"\n{'='*40}", "INFO")
        log(f"Processing Attack {attack_id}: {attack['name']}", "PHASE")
        log(f"{'='*40}", "INFO")

        # Phase A: Evidence Analysis
        evidence_file = attack_dir / "EVIDENCE_ANALYSIS.json"
        if args.skip_evidence and evidence_file.exists():
            log(f"Skipping Phase A (using existing EVIDENCE_ANALYSIS.json)", "INFO")
        else:
            evidence_file = phase_a_evidence_analysis(
                agent=args.agent,
                attack=attack,
                case_folder=case_folder,
                output_dir=attack_dir,
                file_search_store_id=file_search_store_id
            )

        # Delay between phases to avoid rate limits
        log(f"  ⏳ Waiting 5s before Phase B...", "INFO")
        time.sleep(5)

        # Phase B: Counter-Requirements + Fact Matching (merged B+C)
        counter_req_file = attack_dir / "counter_requirements.json"
        if args.skip_counter_req and counter_req_file.exists():
            log(f"Skipping Phase B (using existing counter_requirements.json)", "INFO")
        else:
            counter_req_file = phase_b_counter_requirements(
                agent=args.agent,
                attack=attack,
                evidence_analysis_file=evidence_file,
                case_folder=case_folder,
                output_dir=attack_dir,
                file_search_store_id=file_search_store_id
            )

        # Delay between phases to avoid rate limits
        log(f"  ⏳ Waiting 5s before Phase D...", "INFO")
        time.sleep(5)

        # Phase D: Viability Analysis
        phase_d_viability_analysis(
            agent=args.agent,
            attack=attack,
            evidence_analysis_file=evidence_file,
            counter_req_file=counter_req_file,
            output_dir=attack_dir,
            case_folder=case_folder
        )

        log(f"Attack {attack_id} complete!", "DONE")

        # Add delay between attacks to avoid rate limits (only if more attacks to process)
        if attack != attacks[-1]:
            delay_between_attacks = 5  # seconds
            log(f"Waiting {delay_between_attacks}s before next attack to avoid rate limits...", "INFO")
            time.sleep(delay_between_attacks)

    # Phase E: Gap Analysis (across all attacks)
    log(f"\n{'='*40}", "INFO")
    log(f"Generating Gap Analysis", "PHASE")
    log(f"{'='*40}", "INFO")

    # Delay before final aggregation phase
    log(f"  ⏳ Waiting 5s before Phase E...", "INFO")
    time.sleep(5)

    phase_e_gap_analysis(
        agent=args.agent,
        strategy_dir=strategy_dir,
        case_folder=case_folder
    )

    # Final summary
    log(f"\n{'='*60}", "INFO")
    log(f"DEFENSIVE STRATEGY RELAY COMPLETE", "DONE")
    log(f"{'='*60}", "INFO")
    log(f"Results in: {strategy_dir}")
    log(f"")
    log(f"Files created/updated:")
    for attack in attacks:
        attack_id = attack["id"]
        attack_name_slug = attack["name"].lower().replace(" ", "_").replace("-", "_")[:30]
        attack_dir = strategy_dir / "attacks" / f"{attack_id}_{attack_name_slug}"
        log(f"  - {attack_dir.name}/EVIDENCE_ANALYSIS.json")
        log(f"  - {attack_dir.name}/counter_requirements.json")
        log(f"  - {attack_dir.name}/analysis.md")
    log(f"  - GAP_ANALYSIS.md")


if __name__ == "__main__":
    main()

