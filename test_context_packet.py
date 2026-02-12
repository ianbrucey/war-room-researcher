
import asyncio
import os
from gpt_researcher.agent import GPTResearcher
from gpt_researcher.utils.enum import ReportType

async def test_context_packet():
    # Define a mock context packet
    context_packet = {
        "parties": {
            "plaintiff": "Ian Bruce", 
            "defendant": "CPS Recovery Services"
        },
        "jurisdiction": "Georgia (N.D. Ga.)",
        "claims": ["FDCPA violation"],
        "opposing_argument": "Defendant argues plaintiff lacks standing because the debt was not personally incurred for household purposes.",
        "key_statutes": ["15 U.S.C. § 1692"],
        "our_position": "We have standing as assignee and the debt is consumer in nature."
    }

    print("Initializing GPT Researcher with context packet...")
    researcher = GPTResearcher(
        query="Research defenses against standing argument in FDCPA case",
        report_type=ReportType.ResearchReport.value,
        context_packet=context_packet
    )

    print(f"Context packet stored in researcher: {researcher.context_packet is not None}")
    
    # We want to test if the context packet is passed to plan_research
    # Since we can't easily mock the LLM call without external libraries, 
    # we'll check if the packet flows to plan_research using a monkeypatch or just by inspecting object state
    # But better yet, let's just see if it runs without error. The prompt generation happens inside an async call.
    
    # Let's try to generate the prompt directly to verify logic
    from gpt_researcher.prompts import PromptFamily
    
    print("\nGenerating search queries prompt with context packet...")
    prompt = PromptFamily.generate_search_queries_prompt(
        question="Research defenses against standing argument",
        parent_query="",
        report_type=ReportType.ResearchReport.value,
        context_packet=context_packet
    )
    
    print("\n--- Generated Prompt Snippet ---")
    print(prompt)
    print("-------------------------------")
    
    if "Ian Bruce" in prompt and "CPS Recovery Services" in prompt:
        print("\nSUCCESS: Context packet data found in generated prompt!")
    else:
        print("\nFAILURE: Context packet data NOT found in prompt.")

    if "target the specific legal issue in the opposing argument" in prompt.lower():
        print("SUCCESS: Legal instructions found in prompt!")
    else:
        print("FAILURE: Legal instructions NOT found in prompt.")

if __name__ == "__main__":
    asyncio.run(test_context_packet())
