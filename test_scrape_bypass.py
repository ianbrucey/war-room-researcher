#!/usr/bin/env python3
"""
Test script for the scrape bypass feature.
Calls the REST API on port 8000 and runs a simple research query.
"""

import requests
import time
import sys
import os


def test_research_with_bypass():
    """Test the research API with scrape bypass enabled."""

    # REST API URL for the Docker container
    api_url = "http://localhost:8000/report/"

    # Research request payload
    request_data = {
        "task": "What are the key legal precedents for motion to dismiss in federal court?",
        "report_type": "research_report",
        "report_source": "web",
        "tone": "Objective",
        "headers": {},
        "repo_name": "",
        "branch_name": "",
        "generate_in_background": False  # Wait for completion
    }

    print("=" * 80)
    print("🧪 Testing GPT Researcher with SKIP_EMBEDDING_COMPRESSION=True")
    print("=" * 80)
    print(f"Query: {request_data['task']}")
    print(f"API URL: {api_url}")
    print("=" * 80)
    print()

    try:
        # Send POST request
        print("📤 Sending research request...")
        response = requests.post(api_url, json=request_data, timeout=300)

        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return 1

        result = response.json()
        print("✅ Request completed!\n")

        # Check the response
        report = result.get("report", "")
        research_id = result.get("research_id", "")

        print(f"📄 Report generated ({len(report)} chars)")
        print(f"🆔 Research ID: {research_id}")
        print("=" * 80)
        print(report[:500] + "..." if len(report) > 500 else report)
        print("=" * 80)

        # Now check the Docker container logs for bypass indicators
        print("\n🔍 Checking Docker logs for bypass indicators...")
        print("Run this command to see the logs:")
        print("  docker logs $(docker ps -q --filter ancestor=gptresearcher/gpt-researcher) 2>&1 | grep -E 'SCRAPE CAPTURE|Scraped output captured'")

        # Check if scraped files exist
        print("\n📁 Checking for scraped output files...")
        print("Run this command to check:")
        print("  docker exec $(docker ps -q --filter ancestor=gptresearcher/gpt-researcher) ls -lah /tmp/research_*/scraped/ 2>/dev/null || echo 'No scraped files found'")

        print("\n" + "=" * 80)
        print("🎯 TEST COMPLETED")
        print("=" * 80)
        print("✅ API call successful")
        print("✅ Report generated")
        print("\nTo verify bypass is working:")
        print("1. Check Docker logs for 'SCRAPE CAPTURE SUMMARY'")
        print("2. Check /tmp inside container for research_*/scraped/ directory")
        print("3. Look for _manifest.txt with diagnostics")

        return 0

    except requests.exceptions.Timeout:
        print(f"\n❌ Request timeout (>300s)")
        print("The research query may be taking too long")
        return 2

    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Is the Docker container running? (docker ps)")
        print("2. Is port 8000 accessible? (curl http://localhost:8000)")
        print("3. Check Docker logs: docker logs <container-id>")
        return 3

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    print("\n🚀 Starting REST API test...\n")
    exit_code = test_research_with_bypass()
    sys.exit(exit_code)

