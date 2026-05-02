#!/usr/bin/env python3
"""
Test script for Kai cloud server connection
For trapdoorkid.cybermods.com integration
"""

import asyncio
import sys
from pathlib import Path

# Add kai_agent to path
kai_agent_path = Path(__file__).parent / "kai_agent"
if kai_agent_path.exists():
    sys.path.insert(0, str(kai_agent_path.parent))

from kai_agent.cloud_client import get_cloud_client


async def test_cloud_connection():
    """Test connection to Kai cloud server"""
    print("🔗 Testing Kai Cloud Server Connection")
    print("=" * 50)

    client = get_cloud_client()

    print(f"Target Server: {client.config['endpoint']}")
    print(f"Local RAM: {client._get_system_ram()}GB")
    print()

    # Test health check
    print("1. Health Check...")
    health = await client.health_check()
    print(f"   Status: {health.get('status', 'unknown')}")

    if health.get("status") == "healthy":
        print("   ✅ Server is responding")
        print(f"   Response time: {health.get('response_time', 'N/A')}")
    else:
        print("   ❌ Server not responding")
        print(f"   Error: {health.get('error', 'Unknown')}")
        print()
        print("💡 Troubleshooting:")
        print("   - Check if server is running: systemctl status kai-enterprise")
        print("   - Check nginx: systemctl status nginx")
        print("   - Check certificates: certbot certificates")
        print("   - Check firewall: ufw status")
        return False

    # Test offloading decision
    print()
    print("2. Task Offloading Analysis...")
    tasks = [
        ("Simple chat", "low"),
        ("Code analysis", "medium"),
        ("Full pentest", "high"),
    ]

    for task_name, complexity in tasks:
        should_offload = client.should_offload_task(complexity)
        decision = "🌐 CLOUD" if should_offload else "💻 LOCAL"
        print(f"   {task_name}: {decision}")

    print()
    print("3. Configuration...")
    print(f"   Endpoint: {client.config['endpoint']}")
    print(f"   Timeout: {client.config['timeout']}s")
    print(f"   Retries: {client.config['retry_attempts']}")
    print(f"   SSL Verify: {client.config['verify_ssl']}")

    await client.close()

    print()
    print("=" * 50)
    print("✅ Cloud integration test completed!")
    print()
    print("🎯 Recommendations for 8GB RAM system:")
    print("   - Use cloud for: Full pentests, complex analysis")
    print("   - Use local for: Chat, simple commands, quick tasks")
    print("   - Monitor RAM usage and offload when needed")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_cloud_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
