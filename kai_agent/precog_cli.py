"""Precognitive CLI — Markov chain command prediction."""
from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict
from typing import Optional


class PrecogCLI:
    """Tracks command sequences and predicts next command via n-gram model."""

    def __init__(self, db):
        self.db = db
        self._chain: dict[str, dict[str, float]] = {}
        self._rebuild_lock = threading.Lock()

    def record(self, command: str, cwd: str = "", exit_code: int = 0, intent: str = ""):
        self.db.log_command(command[:500], cwd=cwd, exit_code=exit_code, intent=intent)
        with self._rebuild_lock:
            self._chain.clear()

    def predict(self, n: int = 3) -> list[dict]:
        """Return top N next-command predictions based on last command + bigram model."""
        hist = self.db.query_commands(limit=20)
        if len(hist) < 2:
            return []

        self._ensure_markov(hist)

        last_cmd = hist[0]["command"] if hist else ""
        if not last_cmd:
            return []

        with self._rebuild_lock:
            candidates = self._chain.get(last_cmd, {})
        sorted_cands = sorted(candidates.items(), key=lambda x: -x[1])[:n]
        return [{"command": cmd, "confidence": round(conf, 3)} for cmd, conf in sorted_cands]

    def _ensure_markov(self, hist: list[dict]):
        if self._chain:
            return
        with self._rebuild_lock:
            bigrams: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            for i in range(len(hist) - 1):
                a = hist[i]["command"]
                b = hist[i + 1]["command"]
                if a and b:
                    bigrams[a][b] += 1
            for a, followers in bigrams.items():
                total = sum(followers.values())
                self._chain[a] = {b: c / total for b, c in followers.items()}

    def most_common(self, limit: int = 20) -> list[dict]:
        rows = self.db.query_commands(limit=500)
        cmd_counts: dict[str, int] = {}
        for r in rows:
            cmd_counts[r["command"]] = cmd_counts.get(r["command"], 0) + 1
        sorted_cmds = sorted(cmd_counts.items(), key=lambda x: -x[1])[:limit]
        return [{"command": cmd, "count": cnt, "confidence": round(cnt / max(len(rows), 1), 3)} for cmd, cnt in sorted_cmds]
