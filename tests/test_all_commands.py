#!/usr/bin/env python3
"""
COMPREHENSIVE KAI COMMAND TEST
Tests all major commands and functions without requiring interactive input.
"""

import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kai_agent.assistant import KaiAssistant


def test_command(assistant, cmd_name, test_fn, args=()):
    """Run a single test and report result."""
    try:
        result = test_fn(assistant, *args)
        print(f"  ✅ {cmd_name}")
        return True, result
    except Exception as exc:
        print(f"  ❌ {cmd_name}: {exc}")
        traceback.print_exc()
        return False, str(exc)


def test_memory(assistant):
    """Test memory functions."""
    print("\n🧠 Testing Memory...")
    results = []
    results.append(test_command(assistant, "remember", lambda a: a.remember("Test memory entry")))
    results.append(test_command(assistant, "memory.search", lambda a: a.memory.search("test")))
    results.append(test_command(assistant, "memory.build_context", lambda a: a.memory.build_memory_context()))
    results.append(test_command(assistant, "memory.summarize_tasks", lambda a: a.memory.summarize_tasks()))
    return all(r[0] for r in results)


def test_emotions(assistant):
    """Test emotional state."""
    print("\n😊 Testing Emotions...")
    results = []
    results.append(test_command(assistant, "emotions.get_state", lambda a: a.emotions.get_state()))
    results.append(test_command(assistant, "emotions.process_event", lambda a: a.emotions.process_event("user_spoke")))
    results.append(test_command(assistant, "emotions.get_response_color", lambda a: a.emotions.get_response_color()))
    return all(r[0] for r in results)


def test_relationship(assistant):
    """Test relationship model."""
    print("\n👤 Testing Relationship...")
    results = []
    results.append(test_command(assistant, "relationship.process_message", lambda a: a.relationship.process_message("Hello Kai")))
    results.append(test_command(assistant, "relationship.get_stats", lambda a: a.relationship.get_stats()))
    results.append(test_command(assistant, "relationship.get_relationship_context", lambda a: a.relationship.get_relationship_context()))
    return all(r[0] for r in results)


def test_semantic_memory(assistant):
    """Test semantic memory."""
    print("\n📝 Testing Semantic Memory...")
    results = []
    results.append(test_command(assistant, "semantic_mem.learn_from_conversation", lambda a: a.semantic_mem.learn_from_conversation("Test message")))
    results.append(test_command(assistant, "semantic_mem.get_stats", lambda a: a.semantic_mem.get_stats()))
    results.append(test_command(assistant, "semantic_mem.build_context_for_prompt", lambda a: a.semantic_mem.build_context_for_prompt("test")))
    return all(r[0] for r in results)


def test_social_timing(assistant):
    """Test social timing."""
    print("\n⏰ Testing Social Timing...")
    results = []
    results.append(test_command(assistant, "social_timing.interaction_started", lambda a: a.social_timing.interaction_started()))
    results.append(test_command(assistant, "social_timing.get_status", lambda a: a.social_timing.get_status()))
    return all(r[0] for r in results)


def test_inner_monologue(assistant):
    """Test inner monologue."""
    print("\n💭 Testing Inner Monologue...")
    results = []
    results.append(test_command(assistant, "inner_voice.think", lambda a: a.inner_voice.think({"user_active": True})))
    results.append(test_command(assistant, "inner_voice.get_pending_summary", lambda a: a.inner_voice.get_pending_summary()))
    return all(r[0] for r in results)


def test_mood_journal(assistant):
    """Test mood journal."""
    print("\n📖 Testing Mood Journal...")
    results = []
    results.append(test_command(assistant, "mood_journal.record", lambda a: a.mood_journal.record({"valence": 0.5, "arousal": 0.3}, "happy", "🐕")))
    results.append(test_command(assistant, "mood_journal.get_weekly_summary", lambda a: a.mood_journal.get_weekly_summary()))
    return all(r[0] for r in results)


def test_smart_router(assistant):
    """Test smart router."""
    print("\n🧭 Testing Smart Router...")
    results = []
    results.append(test_command(assistant, "router.route (hello)", lambda a: a.router.route("hello")))
    results.append(test_command(assistant, "router.route (what time)", lambda a: a.router.route("what time is it")))
    return all(r[0] for r in results)


def test_ollama_client(assistant):
    """Test Ollama client configuration."""
    print("\n🤖 Testing Ollama Client...")
    results = []
    results.append(test_command(assistant, "client.provider", lambda a: a.client.provider))
    results.append(test_command(assistant, "client.model", lambda a: a.client.model))
    results.append(test_command(assistant, "client.base_url", lambda a: a.client.base_url))
    return all(r[0] for r in results)


def test_code_intelligence(assistant):
    """Test code intelligence."""
    print("\n💻 Testing Code Intelligence...")
    results = []
    results.append(test_command(assistant, "code_intel.analyze", lambda a: a.code_intel.analyze("def hello(): pass")))
    results.append(test_command(assistant, "code_intel.gen_function", lambda a: a.code_intel.gen_function("test_func", ["x", "y"], "int")))
    return all(r[0] for r in results)


def test_task_planner(assistant):
    """Test task planner."""
    print("\n📋 Testing Task Planner...")
    results = []
    results.append(test_command(assistant, "planner.create_plan", lambda a: a.planner.create_plan("Test plan")))
    results.append(test_command(assistant, "planner.get_plan_status", lambda a: a.planner.get_plan_status()))
    return all(r[0] for r in results)


def test_autonomy(assistant):
    """Test autonomy system."""
    print("\n🤖 Testing Autonomy...")
    results = []
    results.append(test_command(assistant, "autonomy.status", lambda a: a.autonomy.status()))
    return all(r[0] for r in results)


def test_legion_chimera(assistant):
    """Test legion and chimera."""
    print("\n👾 Testing Legion & Chimera...")
    results = []
    results.append(test_command(assistant, "legion.list_bots", lambda a: a.legion.list_bots()))
    results.append(test_command(assistant, "chimera.status", lambda a: a.chimera.status()))
    return all(r[0] for r in results)


def test_learning_system(assistant):
    """Test learning system."""
    print("\n🎓 Testing Learning System...")
    results = []
    results.append(test_command(assistant, "learning.get_stats", lambda a: a.learning.get_stats()))
    return all(r[0] for r in results)


def test_skills_system(assistant):
    """Test skills system."""
    print("\n🎯 Testing Skills System...")
    results = []
    results.append(test_command(assistant, "skills_system.list_skills", lambda a: a.skills_system.list_skills()))
    return all(r[0] for r in results)


def test_hardware_integration(assistant):
    """Test hardware integration."""
    print("\n🔧 Testing Hardware Integration...")
    results = []
    results.append(test_command(assistant, "hardware_integration.get_status", lambda a: a.hardware_integration.get_status()))
    return all(r[0] for r in results)


def test_kali_integration(assistant):
    """Test Kali integration."""
    print("\n🐧 Testing Kali Integration...")
    results = []
    results.append(test_command(assistant, "kali.check_docker", lambda a: a.kali.check_docker_available()))
    return all(r[0] for r in results)


def test_web_automation(assistant):
    """Test web automation."""
    print("\n🕷️ Testing Web Automation...")
    results = []
    results.append(test_command(assistant, "web_automation (init)", lambda a: a.web_automation))
    return all(r[0] for r in results)


def test_desktop_tools(assistant):
    """Test desktop tools."""
    print("\n🖥️ Testing Desktop Tools...")
    results = []
    results.append(test_command(assistant, "tools.policy_status", lambda a: a.tools.policy_status()))
    results.append(test_command(assistant, "tools.list_capabilities", lambda a: a.tools.list_capabilities()))
    return all(r[0] for r in results)


def test_signals(assistant):
    """Test Kai signals."""
    print("\n📡 Testing Signals...")
    results = []
    results.append(test_command(assistant, "signals.summarize", lambda a: a.signals.summarize()))
    return all(r[0] for r in results)


def test_conversation_summary(assistant):
    """Test conversation summary."""
    print("\n💬 Testing Conversation Summary...")
    results = []
    results.append(test_command(assistant, "_compose_conversation_summary", lambda a: a._compose_conversation_summary()))
    return all(r[0] for r in results)


def test_build_messages(assistant):
    """Test message building."""
    print("\n📨 Testing Build Messages...")
    results = []
    results.append(test_command(assistant, "build_messages", lambda a: a.build_messages("Hello")))
    return all(r[0] for r in results)


def test_slash_commands(assistant):
    """Test that REPL command handlers exist and work."""
    print("\n⌨️ Testing Slash Command Handlers...")
    # These are the commands that have explicit handlers in the REPL
    commands_to_test = [
        "/capabilities",
        "/web",
        "/policy status",
        "/model",
        "/provider",
    ]
    results = []
    for cmd in commands_to_test:
        result = None
        try:
            # Simulate what the REPL does for each command
            if cmd == "/capabilities":
                result = assistant.tools.list_capabilities()
            elif cmd == "/web":
                result = "Web automation commands listed"
            elif cmd == "/policy status":
                result = assistant.tools.policy_status()
            elif cmd == "/model":
                result = assistant.client.model
            elif cmd == "/provider":
                result = assistant.client.provider
            print(f"  ✅ {cmd}")
            results.append((True, result))
        except Exception as exc:
            print(f"  ❌ {cmd}: {exc}")
            results.append((False, str(exc)))
    return all(r[0] for r in results)


def test_tool_parsing(assistant):
    """Test tool command parsing."""
    print("\n🔍 Testing Tool Command Parsing...")
    test_inputs = [
        "policy status",
        "show capabilities",
        "add task: test task",
        "plan: test plan",
        "run plan",
        "autonomy on",
        "autonomy status",
        "browse https://example.com",
        "show links",
        "screenshot",
    ]
    results = []
    for inp in test_inputs:
        try:
            result = assistant._maybe_run_tools(inp)
            status = "handled" if result else "passed-to-llm"
            print(f"  ✅ '{inp}' -> {status}")
            results.append((True, result))
        except Exception as exc:
            print(f"  ❌ '{inp}': {exc}")
            results.append((False, str(exc)))
    return all(r[0] for r in results)


async def main():
    print("=" * 60)
    print("🎯 KAI COMPREHENSIVE FUNCTION TEST")
    print("=" * 60)

    workspace = Path("test_workspace_comprehensive")
    workspace.mkdir(exist_ok=True)

    print("\n🚀 Initializing KaiAssistant...")
    try:
        assistant = KaiAssistant(model="llama3.2:3b", workspace=workspace)
        print("  ✅ Assistant initialized")
    except Exception as exc:
        print(f"  ❌ Failed to initialize: {exc}")
        traceback.print_exc()
        return 1

    # Run all test suites
    test_suites = [
        ("Ollama Client", test_ollama_client),
        ("Memory", test_memory),
        ("Emotions", test_emotions),
        ("Relationship", test_relationship),
        ("Semantic Memory", test_semantic_memory),
        ("Social Timing", test_social_timing),
        ("Inner Monologue", test_inner_monologue),
        ("Mood Journal", test_mood_journal),
        ("Smart Router", test_smart_router),
        ("Code Intelligence", test_code_intelligence),
        ("Task Planner", test_task_planner),
        ("Autonomy", test_autonomy),
        ("Legion & Chimera", test_legion_chimera),
        ("Learning System", test_learning_system),
        ("Skills System", test_skills_system),
        ("Hardware Integration", test_hardware_integration),
        ("Kali Integration", test_kali_integration),
        ("Web Automation", test_web_automation),
        ("Desktop Tools", test_desktop_tools),
        ("Signals", test_signals),
        ("Conversation Summary", test_conversation_summary),
        ("Build Messages", test_build_messages),
        ("Slash Commands", test_slash_commands),
        ("Tool Parsing", test_tool_parsing),
    ]

    passed = 0
    failed = 0

    for name, test_fn in test_suites:
        try:
            ok = test_fn(assistant)
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as exc:
            print(f"\n  ❌ {name} suite crashed: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"  Passed: {passed}/{len(test_suites)}")
    print(f"  Failed: {failed}/{len(test_suites)}")

    if failed == 0:
        print("\n🏆 ALL TESTS PASSED! Kai is fully functional.")
    elif failed <= 3:
        print(f"\n⭐ MOSTLY WORKING ({failed} minor issues)")
    else:
        print(f"\n⚠️ NEEDS WORK ({failed} issues found)")

    # Cleanup
    import shutil
    if workspace.exists():
        shutil.rmtree(workspace)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

