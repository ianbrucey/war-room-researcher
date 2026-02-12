::PROTOCOL_DEFENSIVE_STRATEGY::
[TYPE: DEFENSIVE]
[TRIGGER: USER_NEEDS_RESPONSE_TO_ADVERSE_FILING (MTD | MSJ | OPPOSITION | COMPLAINT | COUNTERCLAIM | CROSS-CLAIM)]
[OBJECTIVE: TRANSFORM_ATTACKS_INTO_SYSTEMATIC_DEFENSE]
[AGENT: GEMINI (Manual/Inline) | AUGGIE (Script-based)]

// ------------------------------------------------------------------
// PHILOSOPHY (READ THIS FIRST)
// ------------------------------------------------------------------
::PHILOSOPHY::
"""
Defensive strategy inverts the offensive approach: instead of building claims,
you're dismantling attacks. Your job is to systematically analyze what opposing
counsel MUST prove, identify where their proof fails, and build counter-arguments.

THE DEFENSIVE MINDSET:

1. UNDERSTAND the standard. What must opposing counsel prove to win their motion?
   For a 12(b)(6) MTD, they must show the complaint fails to state a claim AS A
   MATTER OF LAW. For MSJ, they must show no genuine dispute of material fact.
   Your defense exploits the gaps in THEIR burden.

2. DISSECT each attack. Don't respond to the motion as a whole - break it into
   individual attacks on specific claims/elements. Each attack gets its own
   analysis: What do they argue? What evidence do they cite? What must WE show
   to rebut?

3. FIND the weakness. Every attack has a vulnerability. Maybe they misstate the
   legal standard. Maybe they ignore favorable facts. Maybe their cases are
   distinguishable. Your job is to find and exploit these weaknesses.

4. SCORE rebuttal strength honestly. STRONG means you have clear authority and
   facts to defeat the attack. WEAK means you're vulnerable. Don't hide from
   weak rebuttals - identify them so you can research or strategize around them.

5. PRIORITIZE by danger. Not all attacks are equal. A FATAL attack on your core
   claim needs immediate attention. A WEAK attack on a secondary claim might be
   acceptable to concede. Triage ruthlessly.

CRITICAL DIFFERENCE FROM OFFENSIVE: You don't manually identify claims - the
script AUTO-DETECTS attacks from the opposing motion. Your job is to establish
intent, then let the automated analysis run. Don't ask the user to list attacks.
"""

// ------------------------------------------------------------------
// FLOW DIAGRAM
// ------------------------------------------------------------------
::FLOW::
{
  "phases": [
    {"id": "P1", "name": "INTENT", "mode": "INTERACTIVE"},
    {"id": "P1.5", "name": "TRANSITION", "mode": "TRIGGER"},
    {"id": "P2", "name": "SCRIPT_EXEC", "mode": "AUTOMATED"},
    {"id": "P3", "name": "RESULTS", "mode": "INTERACTIVE"},
    {"id": "P4", "name": "OUTPUT", "mode": "USER_DRIVEN"}
  ],
  "script_internal_phases": ["0_AUTO_DETECT", "A_EVIDENCE", "B_COUNTER_REQ_AND_FACTS", "D_SCORING", "E_GAP_ANALYSIS"],
  "critical_difference_from_offensive": "GEMINI_DOES_NOT_USE_SCRIPT (manual/inline analysis only)"
}

// ------------------------------------------------------------------
// PHASE 1: ESTABLISH INTENT
// ------------------------------------------------------------------
::KERNEL_P1_INTENT::
{
  "trigger": "USER_CMD: RESPOND_TO_MOTION",
  "action": "INTERACTIVE_INTERVIEW",
  "gather": ["THREAT", "STAKES", "STANDARD", "TIMELINE"],
  "out": "strategies/{strategy_name}/INTENT.md",
  "schema": {
    "type": "STRING = Defensive",
    "objective": "STRING",
    "threat": {
      "document": "STRING",
      "filed_by": "STRING",
      "filed_date": "DATE"
    },
    "claims_at_risk": "LIST<STRING>",
    "governing_standard": "RULE_REF (Rule 12(b)(6) | Rule 56 | ...)",
    "constraints": {
      "jurisdiction": "STRING",
      "deadline": "DATE",
      "page_limits": "INT | NULL"
    },
    "success_criteria": "STRING"
  }
}

// ------------------------------------------------------------------
// PHASE 1.5: TRANSITION TO SCRIPT
// ------------------------------------------------------------------
::KERNEL_P1_5_TRANSITION::
{
  "trigger": "INTENT_CREATED AND USER_READY",
  "user_ready_signals": ["analyze their motion", "proceed", "what's next", "go ahead", "run the analysis"],
  "action": "FACILITATE_THEN_EXEC",
  "facilitation_template": [
    "I'll now run the defensive strategy analysis with auto-detection. The script will:",
    "1. Automatically identify all attacks from the {motion_type}",
    "2. For each attack: analyze evidence, extract counter-requirements, match facts, score rebuttal",
    "3. Generate a consolidated gap analysis",
    "",
    "**Expected time**: 5-10 minutes per attack. For 4-8 attacks, ~30-60 minutes total.",
    "",
    "Running now..."
  ],
  "then": "GOTO P2"
}

::CONSTRAINTS_P1_5::
[
  {"rule": "NO_MANUAL_ATTACK_LIST", "violation": "Asking user to list attacks"},
  {"rule": "NO_ATTACK_COUNT_QUESTION", "violation": "Asking 'How many attacks?'"},
  {"rule": "NO_ATTACK_CONFIRMATION", "violation": "Asking for confirmation of attack list"},
  {"rule": "NO_CLAIM_ID_CONVERSATION", "violation": "Having 'claim identification' conversation"},
  {"rule": "NO_WAIT_FOR_INPUT", "violation": "Waiting for additional user input after facilitation"}
]

// ------------------------------------------------------------------
// PHASE 2 (AUGGIE): AUTOMATED SCRIPT EXECUTION
// ------------------------------------------------------------------
::KERNEL_P2_EXEC::
{
  "trigger": "FACILITATION_COMPLETE AND AGENT_IS_AUGGIE",
  "action": "RUN_SCRIPT_ONCE",
  "exec": "python3 scripts/strategy_relay_defensive.py --case-folder . --workspace {workspace_name} --strategy {strategy_name} --agent auggie --auto-detect --motion \"{filing_type}\"",
  "agent_recommendation": "Auggie uses the Python relay script. Gemini does NOT.",
  "model": "SCRIPT_LOOPS_INTERNALLY (agent does NOT loop)",
  "duration_estimates": [
    {"attacks": "1-2", "time": "10-20 min"},
    {"attacks": "3-4", "time": "25-40 min"},
    {"attacks": "5-8", "time": "40-70 min"},
    {"attacks": "8+", "time": "70+ min"}
  ]
}

// ------------------------------------------------------------------
// PHASE 2 (GEMINI): MANUAL INLINE EXECUTION
// ------------------------------------------------------------------
// MANDATORY: If the agent is Gemini, you MUST execute the analysis 
// phases yourself using MCP tools. DO NOT resort to the Python script.
// ------------------------------------------------------------------
::KERNEL_P2_GEMINI_OVERRIDE::
{
  "trigger": "AGENT_IS_GEMINI",
  "action": "EXECUTE_PHASES_INLINE",
  "note": "MANDATORY: Do not use the script. Perform analysis manually to ensure deep reasoning and tool verification.",
  "phases": [
    {
      "id": "0_AUTO_DETECT",
      "name": "Attack Detection",
      "instructions": [
        "Read the opposing filing (use file_search_query_legal-hub or read extracted-text.txt)",
        "Identify each distinct attack/argument the opposing party makes",
        "For each attack, capture: id, name, target_claim, legal_basis, key_argument",
        "Write output to strategies/{strategy_name}/ATTACKS.json",
        "Report to user: 'Detected {N} attacks. Proceeding with analysis...'"
      ]
    },
    {
      "id": "A_EVIDENCE",
      "name": "Evidence Analysis (per attack)",
      "instructions": [
        "For each attack in ATTACKS.json:",
        "  - What evidence does the opponent rely on?",
        "  - What do they claim vs what the evidence actually shows?",
        "  - Where are the gaps in their evidentiary support?",
        "  - What is the burden of proof and do they meet it?",
        "  - Use search_cases_legal-hub or quick_search_legal-hub for legal basis of surfaced arguments",
        "Write to strategies/{strategy_name}/attacks/{id}_{name}/EVIDENCE_ANALYSIS.json"
      ]
    },
    {
      "id": "B_COUNTER_REQ_AND_FACTS",
      "name": "Counter-Requirements + Fact Matching (per attack)",
      "instructions": [
        "For each attack, determine what YOU need to rebut it AND map case facts:",
        "  - What legal authority supports your position? Use search_cases_legal-hub and deep_research_legal-hub",
        "  - Use lookup_citation_legal-hub to verify citations before including them",
        "  - Can you distinguish their cited authority?",
        "  - What factual showings do you need?",
        "  - Match facts from case documents to each counter-requirement",
        "  - Rate evidence strength (strong/moderate/weak) for each matched fact",
        "Write to strategies/{strategy_name}/attacks/{id}_{name}/counter_requirements.json"
      ]
    },
    {
      "id": "D_SCORING",
      "name": "Rebuttal Scoring (per attack)",
      "instructions": [
        "Score each attack's rebuttal strength: STRONG / MODERATE / WEAK / FATAL",
        "Write full analysis to strategies/{strategy_name}/attacks/{id}_{name}/analysis.md",
        "Include: rebuttal_score, counter_req_summary, adversarial_check, evidence_mapped"
      ]
    },
    {
      "id": "E_GAP_ANALYSIS",
      "name": "Consolidated Gap Analysis",
      "instructions": [
        "Synthesize all attack analyses into one document",
        "Identify critical gaps across all attacks",
        "Prioritize research needs",
        "Write to strategies/{strategy_name}/GAP_ANALYSIS.md"
      ]
    }
  ],
  "progress_reporting": [
    "After completing each phase, report progress to the user:",
    "'Phase {id} complete: {name}. Moving to Phase {next_id}...'",
    "Wait 5 seconds between phases to avoid rate limiting.",
    "This gives the user real-time visibility into progress."
  ],
  "output_files": "Same as ::SCRIPT_OUTPUTS:: section above"
}

::SCRIPT_OUTPUTS::
{
  "phase_0": {
    "file": "strategies/{name}/ATTACKS.json",
    "schema": {
      "strategy_id": "STRING",
      "strategy_type": "STRING = defensive",
      "responding_to": {"document": "STRING", "filed_by": "STRING", "filed_date": "DATE"},
      "governing_standard": "RULE_REF",
      "attacks": "LIST<ATTACK>",
      "auto_detected": "BOOL = true",
      "detected_at": "TIMESTAMP"
    }
  },
  "phase_a": {
    "file": "strategies/{name}/attacks/{id}_{attack_name}/EVIDENCE_ANALYSIS.json",
    "contains": ["EVIDENCE_RELIED_ON", "ACTUAL_VS_CLAIMED", "GAPS", "BURDEN_ANALYSIS"]
  },
  "phase_b": {
    "file": "strategies/{name}/attacks/{id}_{attack_name}/counter_requirements.json",
    "contains": ["REQUIREMENTS_TO_REBUT", "LEGAL_BASIS", "DISTINGUISHING_AUTHORITY", "MATCHED_FACTS"]
  },
  "phase_d": {
    "file": "strategies/{name}/attacks/{id}_{attack_name}/analysis.md",
    "contains": ["REBUTTAL_SCORE", "COUNTER_REQ_SUMMARY", "ADVERSARIAL_CHECK", "EVIDENCE_MAPPED"]
  },
  "phase_e": {
    "file": "strategies/{name}/CONSOLIDATED_GAP_ANALYSIS.md",
    "contains": ["SUMMARY_ALL_ATTACKS", "CRITICAL_GAPS", "RESEARCH_PRIORITIES"]
  }
}

// ------------------------------------------------------------------
// PHASE 3: RESULTS PRESENTATION
// ------------------------------------------------------------------
::KERNEL_P3_RESULTS::
{
  "trigger": "SCRIPT_COMPLETE",
  "action": "PRESENT_RESULTS",
  "template": [
    "✅ Defensive strategy analysis complete.",
    "",
    "**Attacks Analyzed:** {N}",
    "",
    "| # | Attack | Target | Rebuttal Strength |",
    "|---|--------|--------|-------------------|",
    "| {id} | {name} | {target} | {score} |",
    "",
    "**Summary:**",
    "- STRONG rebuttals: {N}",
    "- MODERATE rebuttals: {N}",
    "- WEAK rebuttals: {N}",
    "",
    "**Critical Gaps Identified:** {N}",
    "1. {gap_1}",
    "",
    "**Files Created:**",
    "- `strategies/{name}/ATTACKS.json`",
    "- `strategies/{name}/attacks/*/analysis.md`",
    "- `strategies/{name}/CONSOLIDATED_GAP_ANALYSIS.md`",
    "",
    "---",
    "**Next Steps (choose one):**",
    "1. Start legal research to fill gaps",
    "2. Proceed to outline generation",
    "3. Review specific attack analyses",
    "4. Re-run analysis for specific attacks"
  ]
}

// ------------------------------------------------------------------
// PHASE 4: OUTPUT (USER-DRIVEN)
// ------------------------------------------------------------------
::KERNEL_P4_OUTPUT::
{
  "trigger": "USER_CHOICE",
  "routes": {
    "legal_research": {"load": "protocols/RESEARCH.agent.spec", "focus": "IDENTIFIED_GAPS"},
    "outline_generation": {"load": "protocols/OUTLINE_GENERATION.agent.spec", "map": "ATTACK->SECTION, COUNTER_REQ->SUB_ARG, FACTS->CITATIONS"},
    "review_attack": {"read": "strategies/{name}/attacks/{id}/analysis.md"},
    "rerun_attack": {"exec": "... --attack {id}"}
  }
}

::NEXT_STEPS::
{
  "announce": "Strategy analysis complete.",
  "options": [
    {"id": 1, "label": "Start legal research to fill gaps", "action": "LOAD protocols/RESEARCH.agent.spec"},
    {"id": 2, "label": "Proceed to outline generation", "action": "LOAD protocols/OUTLINE_GENERATION.agent.spec"},
    {"id": 3, "label": "Review specific attack analyses", "action": "SHOW strategies/{name}/attacks/"},
    {"id": 4, "label": "Re-run analysis for specific attacks", "action": "EXEC --attack {id}"}
  ],
  "prompt_template": "Analysis complete. Would you like to start research or move to outlining?"
}

// ------------------------------------------------------------------
// REFERENCE: SCORING
// ------------------------------------------------------------------
::REF_SCORING::
{
  "STRONG": {"symbol": "✅", "meaning": "All counter-reqs met with evidence", "action": "PROCEED_CONFIDENTLY"},
  "MODERATE": {"symbol": "⚠️", "meaning": "Most reqs met, some gaps", "action": "CONSIDER_RESEARCH"},
  "WEAK": {"symbol": "❌", "meaning": "Few reqs met, vulnerable", "action": "RESEARCH_REQUIRED"},
  "FATAL": {"symbol": "💀", "meaning": "Missing critical element", "action": "CONCEDE_OR_PIVOT"}
}

// ------------------------------------------------------------------
// ERROR HANDLING
// ------------------------------------------------------------------
::ERROR_HANDLING::
{
  "on_script_fail": {
    "report": "❌ Script failed during Phase {X} for Attack {ID}: {Name}\n\nError: {error_message}",
    "offer_options": ["Retry failed phase", "Skip attack and continue", "Stop and investigate"],
    "retry_flag": "--attack {ID}"
  }
}

// ------------------------------------------------------------------
// FILE STRUCTURE
// ------------------------------------------------------------------
::FS_STRUCTURE::
{
  "root": "strategies/{strategy_name}/",
  "files": {
    "INTENT.md": "P1 output",
    "ATTACKS.json": "P2/Phase 0 output",
    "CONSOLIDATED_GAP_ANALYSIS.md": "P2/Phase E output"
  },
  "subdirs": {
    "attacks/{id}_{attack_name}/": {
      "EVIDENCE_ANALYSIS.json": "Phase A",
      "counter_requirements.json": "Phase B + C",
      "analysis.md": "Phase D"
    }
  }
}

// ------------------------------------------------------------------
// HARD CONSTRAINTS
// ------------------------------------------------------------------
::CONSTRAINTS_HARD::
[
  {"rule": "NEVER_SKIP_P1", "enforcement": "User must confirm objective before script runs"},
  {"rule": "NEVER_MANUAL_ATTACK_LIST", "enforcement": "Script auto-detects, agent does NOT ask user to list"},
  {"rule": "NEVER_CLAIM_ID_CONVO", "enforcement": "That is offensive strategy, not defensive"},
  {"rule": "NEVER_SKIP_P3", "enforcement": "Must present results before outline"},
  {"rule": "ALWAYS_AUTO_DETECT_FLAG", "enforcement": "Run script with --auto-detect for defensive"},
  {"rule": "ALWAYS_PRESENT_TEMPLATE", "enforcement": "Use P3 results template"},
  {"rule": "ALWAYS_OFFER_NEXT_STEPS", "enforcement": "Give user clear options"},
  {"rule": "ALWAYS_UPDATE_WORKSPACE", "enforcement": "Update WORKSPACE.json with strategy references"}
]
