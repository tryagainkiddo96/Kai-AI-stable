"""Typeprint — keystroke dynamics / typing rhythm anomaly detection."""
from __future__ import annotations

import json
import math
import threading
import time


class Typeprint:
    """Builds a baseline of the user's typing rhythm and flags anomalies.

    Uses inter-keystroke timing captured from Windows events.
    Baseline model: mean + std dev of inter-key latencies per bigram.
    """

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._baseline: dict[str, list[float]] = {}
        self._recent_times: list[float] = []
        self._recent_chars: list[str] = []
        self._anomaly_count = 0
        self._min_samples = 5

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._load_baseline, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _load_baseline(self):
        if self.db:
            try:
                existing = self.db.query_journal(event_type="typeprint_baseline", limit=1)
                if existing:
                    self._baseline = existing[0].get("data", {}).get("baseline", {})
            except Exception:
                pass

    def record_key(self, char: str, timestamp: float):
        """Record a keypress at a given timestamp. Called from input listener."""
        self._recent_chars.append(char)
        self._recent_times.append(timestamp)
        if len(self._recent_chars) > 200:
            self._recent_chars = self._recent_chars[-100:]
            self._recent_times = self._recent_times[-100:]

        if len(self._recent_chars) >= 2 and len(self._recent_times) >= 2:
            prev_char = self._recent_chars[-2]
            curr_char = self._recent_chars[-1]
            bigram = f"{prev_char}{curr_char}"
            latency = self._recent_times[-1] - self._recent_times[-2]

            if 0.01 < latency < 2.0:
                if bigram not in self._baseline:
                    self._baseline[bigram] = []
                self._baseline[bigram].append(latency)
                if len(self._baseline[bigram]) > 50:
                    self._baseline[bigram] = self._baseline[bigram][-50:]

                self._check_anomaly(bigram, latency)

    def _check_anomaly(self, bigram: str, latency: float):
        samples = self._baseline.get(bigram, [])
        if len(samples) < self._min_samples:
            return
        mean = sum(samples) / len(samples)
        variance = sum((x - mean) ** 2 for x in samples) / len(samples)
        std = math.sqrt(variance) if variance > 0 else 0.001
        z_score = abs(latency - mean) / std
        if z_score > 3.0:
            self._anomaly_count += 1
            if self._anomaly_count > 3:
                if self.db:
                    self.db.journal_entry("typing_anomaly",
                                          {"bigram": bigram, "latency": round(latency, 3),
                                           "mean": round(mean, 3), "z_score": round(z_score, 2)},
                                          source="typeprint", importance=2)
                self._anomaly_count = 0

    def save_baseline(self):
        if self.db:
            summary = {k: {"mean": round(sum(v) / len(v), 4),
                           "count": len(v)}
                       for k, v in self._baseline.items() if len(v) >= self._min_samples}
            if summary:
                self.db.journal_entry("typeprint_baseline",
                                      {"baseline": summary, "bigrams": len(summary)},
                                      source="typeprint", importance=0)

    def analyze(self) -> dict:
        total_bigrams = sum(len(v) for v in self._baseline.values())
        learned = sum(1 for v in self._baseline.values() if len(v) >= self._min_samples)
        return {
            "bigrams_learned": learned,
            "total_samples": total_bigrams,
            "anomalies_detected": self._anomaly_count,
            "confidence": min(1.0, learned / 50),
        }

    def status(self) -> dict:
        return {
            **self.analyze(),
            "enabled": self._enabled,
            "recent_buffer": len(self._recent_chars),
        }
