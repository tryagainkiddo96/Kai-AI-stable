#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

test_files = [
    "tests/test_assistant_smoke.py",
    "test_learning_system.py",
    "test_web_automation.py",
    "test_web_simple.py",
    "test_cloud_simple.py",
    "test_cloud_connection.py",
    "test_simple_masterpiece.py",
]

with open("all_test_results.txt", "w") as out:
    out.write("=" * 60 + "\n")
    out.write("KAI AI — COMPREHENSIVE TEST SUITE\n")
    out.write("=" * 60 + "\n")

    results = {}
    for tf in test_files:
        if not Path(tf).exists():
            out.write(f"\n⚠️  {tf} not found, skipping\n")
            continue
        
        out.write(f"\n📋 Testing: {tf}\n")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", tf, "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
        )
        
        out.write(result.stdout + "\n")
        if result.stderr:
            out.write("STDERR:\n" + result.stderr + "\n")
        
        if result.returncode == 0:
            out.write(f"   ✅ PASS\n")
            results[tf] = "PASS"
        else:
            out.write(f"   ❌ FAIL (exit {result.returncode})\n")
            results[tf] = "FAIL"

    out.write("\n" + "=" * 60 + "\n")
    out.write("SUMMARY\n")
    out.write("=" * 60 + "\n")
    for tf, status in results.items():
        icon = "✅" if status == "PASS" else "❌"
        out.write(f"  {icon} {tf}: {status}\n")

    pass_count = sum(1 for s in results.values() if s == "PASS")
    fail_count = sum(1 for s in results.values() if s == "FAIL")
    out.write(f"\nTotal: {pass_count} passed, {fail_count} failed out of {len(results)} tested\n")

print("Results written to all_test_results.txt")
