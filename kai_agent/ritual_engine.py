"""Ritual Engine — learns repeated command patterns and creates single-command macros."""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from typing import Any, Callable

from kai_agent.ctos_db import CTOSDatabase


class RitualEngine:
    """Detects repeated patterns in user commands and creates macros."""

    def __init__(self, db: CTOSDatabase, execute_fn: Callable):
        self.db = db
        self._execute_fn = execute_fn
        self._recent: deque[dict] = deque(maxlen=50)
        self._suggested: set[str] = set()

    def record(self, command: str, intent: str, result: str):
        """Record a command execution for pattern detection."""
        entry = {
            "timestamp": time.time(),
            "command": command,
            "intent": intent,
            "result_preview": result[:100],
            "success": "error" not in result.lower()[:200],
        }
        self._recent.append(entry)
        self._detect_pattern()

    def _detect_pattern(self):
        """Look for repeating 3+ step patterns."""
        if len(self._recent) < 6:
            return
        recent_list = list(self._recent)
        # Check for repeated intent sequences (e.g. nmap → nikto → gobuster)
        intent_seq = tuple(e["intent"] for e in recent_list[-6:])
        # Look for the last 3, then check if it repeats earlier
        for seq_len in range(3, min(6, len(intent_seq) // 2 + 1)):
            suffix = intent_seq[-seq_len:]
            for i in range(len(intent_seq) - seq_len - seq_len + 1):
                if intent_seq[i:i + seq_len] == suffix:
                    # Found a repeating pattern!
                    self._create_ritual(suffix)
                    return

    def _create_ritual(self, intent_seq: tuple):
        """Auto-create a ritual from a detected pattern."""
        name = " → ".join(intent_seq)
        name_clean = name.lower().replace(" ", "_")[:60]
        steps = []
        recent_list = list(self._recent)
        matched = [e for e in recent_list if e["intent"] in intent_seq][-len(intent_seq):]
        for e in matched:
            steps.append({
                "command": e["command"],
                "intent": e["intent"],
            })
        if self.db.save_ritual(f"auto_{name_clean}", steps):
            if f"auto_{name_clean}" not in self._suggested:
                self._suggested.add(f"auto_{name_clean}")
                self.db.add_urban_event(
                    "ritual", f"New ritual detected: {name}",
                    {"ritual": f"auto_{name_clean}", "steps": len(steps)}, "ritual_engine"
                )

    def suggest_ritual(self, command: str) -> str:
        """Check if a command matches a stored ritual."""
        cmd_lower = command.lower()
        for ritual in self.db.all_rituals():
            name = ritual["name"]
            if name.startswith("auto_"):
                continue
            if name.lower() in cmd_lower or cmd_lower in name.lower():
                return f"I know a ritual for that: '{name}'. Say 'run ritual {name}' to execute."
        return ""

    def create_ritual(self, name: str, steps: list[dict]) -> str:
        """Manually create a ritual."""
        if self.db.save_ritual(name, steps):
            return f"Ritual '{name}' saved ({len(steps)} steps)."
        return f"Ritual '{name}' already exists."

    def run_ritual(self, name: str) -> str:
        """Execute a ritual's steps in sequence."""
        ritual = self.db.get_ritual(name)
        if not ritual:
            return f"No ritual found: '{name}'. Say 'list rituals' to see available ones."
        steps = ritual["steps"]
        lines = [f"══ Ritual: {name} ({len(steps)} steps) ══"]
        success = 0
        fail = 0
        for i, step in enumerate(steps, 1):
            cmd = step.get("command", "")
            if not cmd:
                continue
            try:
                result = self._execute_fn(cmd)
                preview = result[:200]
                lines.append(f"  [{i}/{len(steps)}] {cmd[:50]} → {'OK' if 'error' not in preview.lower()[:100] else 'FAIL'}")
                if "error" in preview.lower()[:100]:
                    fail += 1
                else:
                    success += 1
            except Exception as e:
                lines.append(f"  [{i}/{len(steps)}] {cmd[:50]} → ERROR: {e}")
                fail += 1
        self.db.use_ritual(name)
        lines.append(f"── {success} success, {fail} failed ──")
        return "\n".join(lines)

    def list_rituals(self) -> str:
        rituals = self.db.all_rituals()
        if not rituals:
            return "No rituals saved yet."
        lines = ["Available rituals:"]
        for r in rituals:
            lines.append(f"  {r['name']} ({len(r['steps'])} steps, used {r['uses']}x)")
        return "\n".join(lines)

    def delete_ritual(self, name: str) -> str:
        self.db.delete_ritual(name)
        return f"Ritual '{name}' deleted."
