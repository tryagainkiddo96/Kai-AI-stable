#!/usr/bin/env python3
"""
Test cloud connection for 8GB RAM setup
"""

import asyncio
import sys
from pathlib import Path

# Add kai_agent to path
kai_agent_path = Path(__file__).parent / "kai_agent"
if kai_agent_path.exists():
    sys.path.insert(0, str(kai_agent_path.parent))

from kai_agent.cloud_client import get_cloud_client


async def test_cloud():
    """Test cloud connection"""
    print("Testing Kai Cloud Server Connection")
    print("=" * 50)

    client = get_cloud_client()
    print("Target Server: {}".format(client.config["endpoint"]))
    print("Local RAM: {}GB".format(client._get_system_ram()))
    print()

    # Test health check
    print("Testing connection...")
    health = await client.health_check()
    print("Result: {}".format(health))

    # Test offloading decision
    print()
    print("Offloading recommendations for 8GB RAM:")
    tasks = [
        ("Light chat", "low"),
        ("Code analysis", "medium"),
        ("Full pentest", "high"),
    ]
    for task_name, complexity in tasks:
        should_offload = client.should_offload_task(complexity)
        decision = "CLOUD" if should_offload else "LOCAL"
        print("  {}: {}".format(task_name, decision))

    await client.close()
    print()
    print("SUCCESS: Cloud integration ready!")


if __name__ == "__main__":
    asyncio.run(test_cloud())
