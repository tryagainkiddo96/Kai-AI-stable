"""Knowledge Base — persistent RAG for Kai. Learns from every interaction.

No external dependencies. Uses TF-IDF scoring with Python built-ins.
Stores everything: chat, scan results, commands, errors, environment data.
Retrieves relevant past knowledge on each query and injects into context.
Gets smarter every session without API costs.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional


class KnowledgeBase:
    """Persistent knowledge base with local TF-IDF search."""

    def __init__(self, storage_dir: Path, max_entries: int = 10000):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.entries_file = self.storage_dir / "knowledge.jsonl"
        self.max_entries = max_entries
        self._entries: list[dict] = []
        self._entry_id_counter = 0
        self._load()

    # ── I/O ────────────────────────────────────────────────────────────────

    def _load(self):
        if self.entries_file.exists():
            try:
                with self.entries_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            self._entries.append(entry)
                            eid = entry.get("id", 0)
                            if eid > self._entry_id_counter:
                                self._entry_id_counter = eid
            except:
                pass

    def _save(self):
        tmp = self.entries_file.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for entry in self._entries:
                f.write(json.dumps(entry, default=str) + "\n")
        tmp.replace(self.entries_file)

    # ── Add knowledge ──────────────────────────────────────────────────────

    def add(self, entry_type: str, input_text: str, output_text: str, context: str = "", tags: Optional[list[str]] = None):
        self._entry_id_counter += 1
        entry = {
            "id": self._entry_id_counter,
            "type": entry_type,
            "timestamp": time.time(),
            "input": input_text[:2000],
            "output": output_text[:2000],
            "context": context[:1000],
            "tags": tags or [],
            "keywords": self._extract_keywords(f"{input_text} {output_text} {context}"),
        }
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        self._save()

    def add_chat(self, user_input: str, reply: str, context: str = ""):
        self.add("chat", user_input, reply, context, ["chat"])

    def add_scan(self, scan_type: str, target: str, result: str):
        self.add("scan", f"{scan_type}: {target}", result, "", ["scan", scan_type])

    def add_command(self, command: str, result: str, success: bool):
        self.add("command" if success else "error", command, result, "", ["command"])

    def add_error(self, error_context: str, error_msg: str):
        self.add("error", error_context, error_msg, "", ["error"])

    def add_knowledge(self, topic: str, content: str):
        self.add("knowledge", topic, content, "", ["knowledge"])

    # ── Retrieve ───────────────────────────────────────────────────────────

    def search(self, query: str, top_n: int = 5) -> list[dict]:
        if not self._entries or not query.strip():
            return []
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return []
        scored = []
        for entry in self._entries:
            score = self._similarity(query_keywords, entry.get("keywords", {}))
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        results = []
        seen_inputs = set()
        for score, entry in scored[:top_n * 2]:
            inp = entry.get("input", "")
            if inp in seen_inputs:
                continue
            seen_inputs.add(inp)
            entry["_score"] = round(score, 3)
            results.append(entry)
            if len(results) >= top_n:
                break
        return results

    def build_context(self, query: str, max_results: int = 3) -> str:
        results = self.search(query, top_n=max_results)
        if not results:
            return ""
        parts = ["[KNOWLEDGE BASE — past interactions relevant to this query]"]
        for r in results:
            rtype = r.get("type", "note")
            inp = r.get("input", "")[:200]
            out = r.get("output", "")[:300]
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("timestamp", 0)))
            parts.append(f"  [{ts}] ({rtype}): \"{inp}\" → {out}")
        return "\n".join(parts)

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        types = Counter(e.get("type", "unknown") for e in self._entries)
        return {
            "total_entries": len(self._entries),
            "by_type": dict(types),
            "storage": str(self.entries_file),
        }

    # ── Internal: TF-IDF scoring ───────────────────────────────────────────

    @staticmethod
    def _extract_keywords(text: str) -> dict[str, float]:
        text = text.lower()
        # Remove common noise
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        words = text.split()
        # Filter stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "just", "because", "but", "and", "or",
            "if", "while", "although", "this", "that", "these", "those", "it",
            "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
            "his", "she", "her", "they", "them", "their", "what", "which",
            "who", "whom", "about", "up", "get", "got", "like", "make", "made",
            "want", "know", "think", "see", "look", "come", "come", "go", "take",
            "let", "say", "tell", "ask", "try", "leave", "call", "give", "use",
            "find", "need", "set", "put", "move", "work", "show", "turn", "run",
        }
        filtered = [w for w in words if w not in stopwords and len(w) > 2]
        total = len(filtered)
        if not total:
            return {}
        counts = Counter(filtered)
        # TF = term frequency
        return {word: count / total for word, count in counts.items()}

    @staticmethod
    def _similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
        if not v1 or not v2:
            return 0.0
        # Intersection scoring with TF-IDF weighting
        common = set(v1) & set(v2)
        if not common:
            return 0.0
        dot = sum(v1[w] * v2[w] for w in common)
        norm1 = math.sqrt(sum(v ** 2 for v in v1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
