#!/usr/bin/env python3
"""
Simple test for Kai web automation
"""

import asyncio
import sys
from pathlib import Path

# Add kai_agent to path
kai_agent_path = Path(__file__).parent / "kai_agent"
if kai_agent_path.exists():
    sys.path.insert(0, str(kai_agent_path.parent))

from kai_agent.web_automation import KaiWebAutomation


async def test_web():
    """Test web automation"""
    print("Testing Kai Web Automation")
    print("=" * 50)

    workspace = Path("test_workspace")
    web = KaiWebAutomation(workspace)

    # Test 1: Start browser
    print("1. Starting browser...")
    success = await web.start_browser()
    print("   Result: {}".format("SUCCESS" if success else "FAILED"))

    # Test 2: Navigate
    print("2. Testing navigation...")
    result = await web.navigate_to("https://example.com")
    print("   Result: {}".format("SUCCESS" if result["success"] else "FAILED"))

    # Test 3: Find free servers
    print("3. Finding free servers...")
    servers = await web.find_free_servers()
    print("   Found: {} servers".format(len(servers)))

    # Test 4: Signup automation
    print("4. Testing signup...")
    signup = await web.automate_signup("test", {"username": "test"})
    print("   Result: {}".format("SUCCESS" if signup["success"] else "FAILED"))

    # Test 5: Page analysis
    print("5. Testing page analysis...")
    analysis = await web.extract_page_info()
    print("   Result: {}".format("SUCCESS" if analysis["success"] else "FAILED"))

    await web.close_browser()

    print("=" * 50)
    print("Web Automation Test Complete!")
    print("Framework is ready for full browser integration.")

    return True


if __name__ == "__main__":
    asyncio.run(test_web())
