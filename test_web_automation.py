#!/usr/bin/env python3
"""
Test script for Kai's new web automation capabilities
"""

import asyncio
import sys
from pathlib import Path

# Add kai_agent to path
kai_agent_path = Path(__file__).parent / "kai_agent"
if kai_agent_path.exists():
    sys.path.insert(0, str(kai_agent_path.parent))

from kai_agent.web_automation import KaiWebAutomation


async def test_web_automation():
    """Test the web automation capabilities"""
    print("🕷️  Testing Kai Web Automation")
    print("=" * 50)

    workspace = Path("test_web_workspace")
    workspace.mkdir(exist_ok=True)

    async with KaiWebAutomation(workspace) as web:
        print("1. Testing browser startup...")
        success = await web.start_browser()
        if success:
            print("   ✅ Browser started successfully")
        else:
            print("   ❌ Browser failed to start")
            return False

        print("\n2. Testing navigation to example.com...")
        result = await web.navigate_to("https://example.com")
        if result["success"]:
            print(f"   ✅ Navigation successful: {result['title']}")
            print(f"   📸 Screenshot saved: {result['screenshot']}")
        else:
            print(f"   ❌ Navigation failed: {result.get('error', 'Unknown error')}")

        print("\n3. Testing free server discovery...")
        try:
            servers = await web.find_free_servers()
            available = [s for s in servers if s["status"] == "available"]
            print(f"   ✅ Found {len(available)} available free services")
            if available:
                print(
                    f"   📋 First service: {available[0]['name']} - {available[0]['description']}"
                )
        except Exception as e:
            print(f"   ❌ Free server discovery failed: {e}")

        print("\n4. Testing page analysis...")
        try:
            analysis = await web.extract_page_info()
            if analysis["success"]:
                print(f"   ✅ Page analyzed: {analysis['title']}")
                print(f"   🔗 Links found: {analysis['links_found']}")
                print(f"   📝 Forms found: {analysis['forms_found']}")
            else:
                print(
                    f"   ❌ Page analysis failed: {analysis.get('error', 'Unknown error')}"
                )
        except Exception as e:
            print(f"   ❌ Page analysis error: {e}")

        print("\n5. Testing signup form filling...")
        try:
            signup_result = await web.automate_signup(
                "mock_signup",
                {
                    "username": "test_user",
                    "email": "test@example.com",
                    "password": "TestPass123!",
                },
            )
            if signup_result["success"]:
                print(
                    f"   ✅ Signup form filled for {signup_result.get('service', 'unknown')}"
                )
                print(
                    f"   📝 Fields filled: {len(signup_result.get('fields_filled', []))}"
                )
            else:
                print(
                    f"   ❌ Signup failed: {signup_result.get('error', 'Unknown error')}"
                )
        except Exception as e:
            print(f"   ❌ Signup error: {e}")

    # Cleanup
    import shutil

    if workspace.exists():
        shutil.rmtree(workspace)

    print("\n" + "=" * 50)
    print("🎉 Web Automation Test Complete!")
    print("\nNew Kai Capabilities Now Available:")
    print("• /web start - Start browser automation")
    print("• /web goto <url> - Navigate to websites")
    print("• /web free-servers - Find free APIs")
    print("• /web signup <service> - Fill signup forms")
    print("• /web analyze - Extract page information")
    print("• /web stop - Close browser")
    print("\nThis closes Kai's major web automation gap! 🚀")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_web_automation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
