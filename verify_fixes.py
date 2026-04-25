#!/usr/bin/env python3
"""Verify datetime fixes and run quick smoke test."""

import sys
from pathlib import Path

results = []

# Check syntax of fixed files
files = [
    'kai_agent/memory.py',
    'kai_agent/autonomy.py',
    'kai_agent/emotional_state.py',
    'kai_agent/social_timing.py',
    'kai_agent/relationship_model.py',
    'kai_agent/inner_monologue.py',
    'kai_agent/logger.py',
    'kai_agent/mood_journal.py',
]

import ast

for f in files:
    try:
        ast.parse(Path(f).read_text(encoding='utf-8'))
        results.append(f"SYNTAX OK: {f}")
    except SyntaxError as e:
        results.append(f"SYNTAX ERROR: {f}: {e}")
        sys.exit(1)

# Check no utcnow remains
utcnow_count = 0
for f in files:
    content = Path(f).read_text(encoding='utf-8')
    count = content.count('utcnow()')
    if count:
        results.append(f"WARNING: {f} still has {count} utcnow() calls")
        utcnow_count += count

if utcnow_count == 0:
    results.append("ALL utcnow() calls removed!")

# Try importing the modules
try:
    from kai_agent.memory import KaiMemory
    results.append("IMPORT OK: kai_agent.memory")
except Exception as e:
    results.append(f"IMPORT FAIL: kai_agent.memory: {e}")
    sys.exit(1)

try:
    from kai_agent.mood_journal import MoodJournal
    results.append("IMPORT OK: kai_agent.mood_journal")
except Exception as e:
    results.append(f"IMPORT FAIL: kai_agent.mood_journal: {e}")
    sys.exit(1)

# Write results
Path('verify_results.txt').write_text('\n'.join(results), encoding='utf-8')
print("Verification complete. See verify_results.txt")
