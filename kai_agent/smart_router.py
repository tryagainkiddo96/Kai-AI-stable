"""
Kai Smart Router
Decides how to answer a question instead of always hitting Ollama.
Routes to the cheapest, fastest, most appropriate handler.

Route map:
  Web search -> factual questions (what, when, where, who)
  Direct answer -> simple math, time, greetings
  Ollama -> personality, opinions, conversation, complex reasoning
  Tool -> commands, file ops, code analysis
  Cached -> repeated questions
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


class SmartRouter:
    """
    Routes user input to the best handler instead of always using Ollama.
    """

    DIRECT_PATTERNS = [
        # Greetings — instant reply, no LLM needed
        (re.compile(r"^(?:hi|hello|hey|yo|sup|howdy|greetings|hiya|heya|what's up|wassup)[!\.\?]*$", re.I), "greeting"),
        (re.compile(r"^(?:hi|hello|hey)\s+(?:there|kai|buddy|pal|friend)[!\.\?]*$", re.I), "greeting"),
        (re.compile(r"^(?:good\s+(?:morning|afternoon|evening|night))[!\.\?]*$", re.I), "greeting"),
        (re.compile(r"^what time is it", re.I), "time"),
        (re.compile(r"^(?:what(?:'s| is)?(?: the)? (?:date|day)(?: is it| today)?|what day is it|what date is it|what date today is|what day today is)$", re.I), "date"),
        (re.compile(r"^(\d+\s*[\+\-\*\/\%\^]\s*\d+.*=?\s*)$", re.I), "math"),
        (re.compile(r"^what is (\d+)", re.I), "math"),
        (re.compile(r"^calculate", re.I), "math"),
        (re.compile(r"^\d+\s+(?:plus|minus|times|multiplied by|divided by)\s+\d+", re.I), "math_words"),
        (re.compile(r"^convert \d+", re.I), "conversion"),
    ]

    WEB_PATTERNS = [
        (re.compile(r"^what (?:is|are|was|were) (?:the |a )?([\w\s]+)", re.I), "factual"),
        (re.compile(r"^who (?:is|are|was|were) ", re.I), "person"),
        (re.compile(r"^when (?:did|was|is|were) ", re.I), "historical"),
        (re.compile(r"^where (?:is|are|was|were|do|does) ", re.I), "location"),
        (re.compile(r"^how (?:many|much|old|far|long|tall|fast) ", re.I), "measurement"),
        (re.compile(r"^latest (?:news|price|stock|weather)", re.I), "current"),
        (re.compile(r"^search (?:for )?", re.I), "explicit_search"),
        (re.compile(r"^look up ", re.I), "explicit_search"),
        (re.compile(r"^find (?:out )?(?:about |info )?", re.I), "explicit_search"),
        (re.compile(r"^google ", re.I), "explicit_search"),
    ]

    OLLAMA_PATTERNS = [
        (re.compile(r"^tell me (?:a |about )?", re.I), "conversation"),
        (re.compile(r"^what do you think", re.I), "opinion"),
        (re.compile(r"^explain", re.I), "explanation"),
        (re.compile(r"^help me (?:with |understand)", re.I), "help"),
        (re.compile(r"^how (?:do|can|should|would) (?:I|we)", re.I), "howto"),
        (re.compile(r"^why", re.I), "reasoning"),
        (re.compile(r"^can you", re.I), "request"),
        (re.compile(r"^would you", re.I), "request"),
        (re.compile(r"^I (?:feel|think|want|need|wish)", re.I), "personal"),
        (re.compile(r"^let(?:'s| us)", re.I), "collaboration"),
    ]

    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or Path.cwd() / "memory" / "answer_cache.json"
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 3600
        self._stats = {"direct": 0, "web": 0, "ollama": 0, "cached": 0}
        self._load_cache()

    def _normalize_common_typos(self, text: str) -> str:
        normalized = f" {text.strip().lower()} "
        replacements = {
            " waht ": " what ",
            " whta ": " what ",
            " teh ": " the ",
            " dte ": " date ",
            " daet ": " date ",
            " tiem ": " time ",
            " todai ": " today ",
            " tday ": " today ",
            " wat ": " what ",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return re.sub(r"\s+", " ", normalized).strip()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = data
            except Exception:
                pass

    def save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")

    def _should_bypass_cache(self, text: str) -> bool:
        lowered = text.lower().strip()
        if not lowered:
            return True
        if len(lowered) > 120:
            return True
        conversational_markers = (
            "i ",
            "i'm",
            "i am",
            "my ",
            "we ",
            "we're",
            "we are",
            "you ",
            "can you",
            "would you",
            "help me",
            "let's",
            "lets ",
            "why ",
            "how do",
            "how can",
            "how should",
        )
        return any(lowered.startswith(marker) for marker in conversational_markers)

    def route(self, text: str) -> dict[str, Any]:
        text_clean = text.strip()
        normalized_text = self._normalize_common_typos(text_clean)
        cache_key = hashlib.md5(text_clean.lower().encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if (
            cached
            and not self._should_bypass_cache(text_clean)
            and (time.time() - float(cached.get("time", 0))) < self._cache_ttl
        ):
            self._stats["cached"] += 1
            return {
                "handler": "cached",
                "type": "cached_response",
                "data": {"response": cached["response"]},
            }

        for pattern, answer_type in self.DIRECT_PATTERNS:
            if pattern.search(text_clean) or pattern.search(normalized_text):
                self._stats["direct"] += 1
                return {
                    "handler": "direct",
                    "type": answer_type,
                    "data": self._get_direct_answer(answer_type, normalized_text),
                }

        for pattern, query_type in self.WEB_PATTERNS:
            match = pattern.search(text_clean)
            if match:
                self._stats["web"] += 1
                query = text_clean
                if query_type == "explicit_search":
                    query = re.sub(
                        r"^(?:search|look up|find|google)\s*(?:for|about|info)?\s*",
                        "",
                        text_clean,
                        flags=re.I,
                    )
                return {
                    "handler": "web",
                    "type": query_type,
                    "data": {"query": query.strip()},
                }

        for pattern, conv_type in self.OLLAMA_PATTERNS:
            if pattern.search(text_clean):
                self._stats["ollama"] += 1
                return {
                    "handler": "ollama",
                    "type": conv_type,
                    "data": {"prompt": text_clean},
                }

        self._stats["ollama"] += 1
        return {
            "handler": "ollama",
            "type": "general",
            "data": {"prompt": text_clean},
        }

    def _get_direct_answer(self, answer_type: str, text: str) -> dict[str, Any]:
        from datetime import datetime

        if answer_type == "greeting":
            import random
            hour = datetime.now().hour
            if 5 <= hour < 12:
                time_greeting = "morning"
            elif 12 <= hour < 17:
                time_greeting = "afternoon"
            elif 17 <= hour < 22:
                time_greeting = "evening"
            else:
                time_greeting = "night"
            replies = [
                f"Hey there. Good {time_greeting}.",
                f"Hi. How's it going this {time_greeting}?",
                "Hey. What's on your mind?",
                "Hello. Ready when you are.",
                "Hi there. What are we working on?",
                "Hey. I'm here.",
                f"Good {time_greeting}. What do you need?",
                "Yo. What's up?",
                "Hey. Need something or just saying hi?",
            ]
            return {"response": random.choice(replies)}

        if answer_type == "time":
            now = datetime.now().strftime("%I:%M %p")
            return {"response": f"It's {now}."}

        if answer_type == "date":
            now = datetime.now().strftime("%A, %B %d, %Y")
            return {"response": f"Today is {now}."}

        if answer_type == "math":
            try:
                expr = re.search(r"(\d+\s*[\+\-\*\/\%\^]\s*\d+[\d\s\+\-\*\/\%\^\.]*)", text)
                if expr:
                    result = self._safe_eval_math(expr.group(1))
                    return {"response": f"{result}"}
            except Exception:
                pass
            return {"response": "I'd need to calculate that. Let me think..."}

        if answer_type == "math_words":
            normalized = re.sub(r"\bmultiplied by\b", "*", text, flags=re.I)
            normalized = re.sub(r"\bdivided by\b", "/", normalized, flags=re.I)
            normalized = re.sub(r"\bplus\b", "+", normalized, flags=re.I)
            normalized = re.sub(r"\bminus\b", "-", normalized, flags=re.I)
            normalized = re.sub(r"\btimes\b", "*", normalized, flags=re.I)
            normalized = re.sub(r"[^0-9\+\-\*\/\.\s]", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            try:
                result = self._safe_eval_math(normalized)
                return {"response": f"{result}"}
            except Exception:
                return {"response": "I'd need to calculate that. Let me think..."}

        if answer_type == "conversion":
            return {"response": "I can look that up. What units?"}

        return {"response": ""}

    def _safe_eval_math(self, expression: str) -> float | int:
        parsed = ast.parse(expression.replace("^", "**"), mode="eval")
        return self._eval_math_node(parsed.body)

    def _eval_math_node(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = self._eval_math_node(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(
            node.op,
            (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow),
        ):
            left = self._eval_math_node(node.left)
            right = self._eval_math_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            return left ** right
        raise ValueError("Unsupported math expression")

    def cache_response(self, question: str, response: str) -> None:
        key = hashlib.md5(question.lower().strip().encode()).hexdigest()
        self._cache[key] = {"response": response, "time": time.time()}
        if len(self._cache) > 500:
            oldest = sorted(self._cache.items(), key=lambda item: item[1].get("time", 0))
            for key_to_delete, _ in oldest[:100]:
                del self._cache[key_to_delete]
        self.save_cache()

    def get_stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "cache_size": len(self._cache),
            "total_routed": sum(self._stats.values()),
        }

    def get_route_breakdown(self) -> str:
        total = sum(self._stats.values()) or 1
        return (
            f"Direct: {self._stats['direct']} ({self._stats['direct'] * 100 // total}%) | "
            f"Web: {self._stats['web']} ({self._stats['web'] * 100 // total}%) | "
            f"Ollama: {self._stats['ollama']} ({self._stats['ollama'] * 100 // total}%) | "
            f"Cached: {self._stats['cached']} ({self._stats['cached'] * 100 // total}%)"
        )
