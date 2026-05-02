#!/usr/bin/env python3
import os
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
]

results = {}
for tf in test_files:
    if not Path(tf).exists():
        sys.stderr.write(f"\nWARNING: {tf} not found, skipping\n")
        continue
    
    sys.stderr.write(f"\nTesting: {tf}\n")
    result = subprocess.run(
        [os.path.join(os.getcwd(), "venv", "Scripts", "python.exe"), "-m", "pytest", tf, "-v", "--tb=short", "--no-header"],
        capture_output=True, text=True, encoding="utf-8"
    )
    
    if result.returncode == 0:
        sys.stderr.write(f"   PASS\n")
        results[tf] = "PASS"
    else:
        sys.stderr.write(f"   FAIL (exit {result.returncode})\n")
        results[tf] = "FAIL"

sys.stderr.write("\n" + "=" * 60 + "\n")
sys.stderr.write("SUMMARY\n")
sys.stderr.write("=" * 60 + "\n")
for tf, status in results.items():
    sys.stderr.write(f"  {tf}: {status}\n")

pass_count = sum(1 for s in results.values() if s == "PASS")
fail_count = sum(1 for s in results.values() if s == "FAIL")
sys.stderr.write(f"\nTotal: {pass_count} passed, {fail_count} failed out of {len(results)} tested\n")

# Removing the print to file statement as we are now directing output to stderr
# print("Results written to all_test_results.txt")
