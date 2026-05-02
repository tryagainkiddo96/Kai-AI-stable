"""Fallback Handler — model fallback and web research recovery."""
from __future__ import annotations

import json


class FallbackHandler:
    """Handles LLM failures by trying fallback models, then web research."""

    def __init__(self, ollama_client_cls, fallback_models: list[str], fallback_timeout: int = 25) -> None:
        self.ollama_client_cls = ollama_client_cls
        self.fallback_models = fallback_models
        self.fallback_timeout = fallback_timeout

    def try_fallback(
        self,
        user_input: str,
        prompt: str,
        primary_error: str,
        primary_model: str,
        base_url: str,
        messages: list[dict] | None = None,
        search_web_fn=None,
    ) -> str:
        """Try fallback models, then web research. Returns reply or empty string."""
        available_models = self._discover_models(base_url)
        prompt_messages = messages or []

        for fallback_model in self.fallback_models:
            if available_models is not None and fallback_model not in available_models:
                continue
            try:
                backup_client = self.ollama_client_cls(base_url=base_url, model=fallback_model)
                reply = backup_client.chat(prompt_messages, timeout=self.fallback_timeout)
                return (
                    f"[Recovery mode] Primary model `{primary_model}` failed, switched to `{fallback_model}`.\n\n"
                    f"{reply}"
                )
            except Exception:
                continue

        if search_web_fn:
            return self._fallback_web_research(user_input, primary_model, primary_error, search_web_fn)
        return ""

    def _discover_models(self, base_url: str) -> set[str] | None:
        try:
            client = self.ollama_client_cls(base_url=base_url)
            return set(client.list_models(timeout=5))
        except Exception:
            return None

    def _fallback_web_research(self, user_input: str, primary_model: str, primary_error: str, search_web_fn) -> str:
        try:
            research = json.loads(search_web_fn(user_input))
        except Exception:
            research = {"ok": False}
        if not research.get("ok"):
            return ""
        answer = str(research.get("answer", "")).strip()
        results = research.get("results", [])[:5]
        lines = [
            "[Recovery mode] Switched to web research.",
            "[High confidence] Best available evidence:",
        ]
        if answer:
            lines.append(answer)
        if results:
            lines.append("Sources:")
            for item in results:
                lines.append(f"- {item.get('title', '')} - {item.get('url', '')}")
        return "\n".join(lines)
