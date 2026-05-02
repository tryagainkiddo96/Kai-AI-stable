"""Message Builder — assembles context and builds LLM message payloads."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path


class MessageBuilder:
    """Builds message payloads for the LLM with context caching."""

    def __init__(
        self,
        system_prompt: str,
        max_system_chars: int = 3200,
        cache_ttl: float = 2.0,
    ) -> None:
        self.system_prompt = system_prompt
        self.max_system_chars = max_system_chars
        self.cache_ttl = cache_ttl
        self._cache: dict = {}
        self._cache_time: float = 0

    def invalidate_cache(self) -> None:
        self._cache = {}
        self._cache_time = 0.0

    def build(
        self,
        user_input: str,
        history: list[dict],
        memory_context: str = "",
        tool_context: str = "",
        semantic_context: str = "",
        emotion_context: str = "",
        relationship_context: str = "",
        conversation_summary: str = "",
        inner_thought: str = "",
    ) -> list[dict]:
        now = time.time()
        if self._cache and (now - self._cache_time) < self.cache_ttl:
            return [*self._cache["messages"], {"role": "user", "content": user_input}]

        system_parts: list[str] = []
        if tool_context:
            system_parts.append(tool_context)
        if memory_context:
            system_parts.append(memory_context)
        if conversation_summary:
            system_parts.append(f"Session summary:\n{conversation_summary}")
        if semantic_context:
            system_parts.append(semantic_context)
        if relationship_context:
            system_parts.append(relationship_context)
        if emotion_context:
            system_parts.append(emotion_context)
        if inner_thought:
            system_parts.append(inner_thought)

        dynamic_context = "\n\n".join(p for p in system_parts if p)
        combined_system = self.system_prompt
        if dynamic_context:
            combined_system = f"{combined_system}\n\n---\n\n{dynamic_context}"
        if len(combined_system) > self.max_system_chars:
            combined_system = combined_system[: self.max_system_chars - 100] + "\n[...trimmed...]"

        messages = [{"role": "system", "content": combined_system}] + history[1:] + [{"role": "user", "content": user_input}]
        self._cache = {"messages": [{"role": "system", "content": combined_system}, *history[1:]], "timestamp": now}
        self._cache_time = now
        return messages

    @staticmethod
    def compact_text(text: str, limit: int = 180) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."

    def compose_summary(
        self,
        history: list[dict],
        turn_window: int = 8,
        char_limit: int = 1200,
        active_task: dict | None = None,
        recent_preferences: list[str] | None = None,
        task_snapshot: str = "",
    ) -> str:
        recent_turns = history[1:][-(turn_window * 2):]
        recent_user = [
            self.compact_text(str(turn.get("content", "")), 140)
            for turn in recent_turns
            if turn.get("role") == "user" and str(turn.get("content", "")).strip()
        ][-4:]
        recent_assistant = [
            self.compact_text(str(turn.get("content", "")), 140)
            for turn in recent_turns
            if turn.get("role") == "assistant" and str(turn.get("content", "")).strip()
        ][-2:]

        lines: list[str] = []
        if active_task:
            lines.append(f"Active task: {self.compact_text(str(active_task.get('title', '')), 120)}")
        if recent_user:
            lines.append("Recent user intent: " + " | ".join(recent_user))
        if recent_assistant:
            lines.append("Recent Kai replies: " + " | ".join(recent_assistant))
        if recent_preferences:
            lines.append("Known user preferences: " + " | ".join(recent_preferences))
        if task_snapshot and task_snapshot != "No saved tasks.":
            lines.append(f"Task memory: {self.compact_text(task_snapshot, 180)}")

        summary = "\n".join(lines).strip()
        if len(summary) > char_limit:
            summary = summary[: char_limit - 3].rstrip() + "..."
        return summary

    def save_summary(self, summary: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": summary,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def load_summary(path: Path) -> str:
        if not path.exists():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return ""
        if not isinstance(data, dict):
            return ""
        summary = data.get("summary", "")
        return summary.strip() if isinstance(summary, str) else ""
