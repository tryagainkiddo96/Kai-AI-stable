"""Self-Improving System — Kai learns from errors and never gives up."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path


class SelfImprover:
    """Automatically researches errors, attempts fixes, and stores learned patterns."""

    def __init__(self, workspace: Path, search_web_fn=None, run_shell_fn=None) -> None:
        self.workspace = workspace
        self.knowledge_path = workspace / "memory" / "self_knowledge.json"
        self.knowledge = self._load_knowledge()
        self.search_web_fn = search_web_fn
        self.run_shell_fn = run_shell_fn
        self.max_retry_loops = 3
        self.failure_patterns = self._build_failure_patterns()

    def _load_knowledge(self) -> dict:
        if self.knowledge_path.exists():
            try:
                data = json.loads(self.knowledge_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                pass
        return {"patterns": [], "fixes": [], "tool_workarounds": [], "last_pruned": None}

    def _save_knowledge(self) -> None:
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_path.write_text(json.dumps(self.knowledge, indent=2), encoding="utf-8")

    def _build_failure_patterns(self) -> list[dict]:
        return [
            {"regex": r"command not found|not recognized", "type": "missing_tool", "severity": "low"},
            {"regex": r"permission denied|access denied|unauthorized", "type": "permissions", "severity": "medium"},
            {"regex": r"connection refused|timed out|unreachable", "type": "network", "severity": "medium"},
            {"regex": r"no such file|does not exist|file not found", "type": "missing_file", "severity": "low"},
            {"regex": r"out of memory|memory limit|oom", "type": "resource", "severity": "high"},
            {"regex": r"syntax error|invalid syntax|parse error", "type": "syntax", "severity": "medium"},
            {"regex": r"dependency|import error|module not found", "type": "dependency", "severity": "medium"},
            {"regex": r"port.*in use|address already in use", "type": "port_conflict", "severity": "low"},
            {"regex": r"certificate|ssl|tls", "type": "ssl", "severity": "medium"},
            {"regex": r"rate limit|too many requests|429", "type": "rate_limit", "severity": "medium"},
        ]

    def diagnose(self, error_text: str, command: str = "") -> dict:
        """Analyze an error and return diagnosis with suggested fixes."""
        diagnosis = {"error": error_text[:500], "command": command, "patterns": [], "suggestions": [], "past_fixes": [], "confidence": 0}
        for pattern in self.failure_patterns:
            if re.search(pattern["regex"], error_text, re.IGNORECASE):
                diagnosis["patterns"].append(pattern)
                diagnosis["confidence"] = max(diagnosis["confidence"], 0.6)
        for past_fix in self.knowledge.get("fixes", []):
            if any(word in error_text.lower() for word in past_fix.get("keywords", [])):
                diagnosis["past_fixes"].append(past_fix)
                diagnosis["confidence"] = max(diagnosis["confidence"], 0.7)
        for workaround in self.knowledge.get("tool_workarounds", []):
            if workaround.get("tool") and command and workaround["tool"].lower() in command.lower():
                diagnosis["suggestions"].append({"type": "workaround", "action": workaround.get("action", ""), "notes": workaround.get("notes", "")})
        if not diagnosis["patterns"] and not diagnosis["past_fixes"]:
            diagnosis["suggestions"].append({"type": "research", "action": "search_web_and_retry", "notes": "No known pattern, will research"})
        return diagnosis

    def suggest_fix(self, diagnosis: dict, original_command: str = "") -> str | None:
        """Return a fix command or action based on diagnosis."""
        if diagnosis.get("past_fixes"):
            past_fix = diagnosis["past_fixes"][0]
            if past_fix.get("fix_command"):
                return past_fix["fix_command"]
        for suggestion in diagnosis.get("suggestions", []):
            if suggestion.get("action"):
                return suggestion["action"]
        for pattern in diagnosis.get("patterns", []):
            if pattern["type"] == "missing_tool":
                return "apt-get install -y $(command_that_failed)" if "kali" in original_command.lower() else None
            if pattern["type"] == "permissions":
                return "sudo " + original_command if original_command else None
            if pattern["type"] == "dependency":
                return "pip install -r requirements.txt" if "python" in original_command.lower() else None
        return None

    def research_error(self, error_text: str, command: str = "", context: str = "") -> list[dict]:
        """Research an error online and return findings."""
        if not self.search_web_fn:
            return []
        query = error_text[:200].replace("\n", " ")
        if command:
            query = f"{command} {query}"[:300]
        try:
            result = self.search_web_fn(f"fix {query}")
            data = json.loads(result)
            if data.get("ok"):
                return data.get("results", [])[:5]
        except Exception:
            pass
        return []

    def attempt_fix(self, original_command: str, error_text: str, diagnosis: dict, attempt: int = 1) -> dict:
        """Try to fix the error and return result."""
        if attempt > self.max_retry_loops:
            return {"ok": False, "error": f"Max retry loops ({self.max_retry_loops}) exhausted", "attempts": attempt}
        suggested_fix = self.suggest_fix(diagnosis, original_command)
        if not suggested_fix:
            return {"ok": False, "error": "No fix available, researching...", "needs_research": True, "attempts": attempt}
        if not self.run_shell_fn:
            return {"ok": False, "error": "No shell available to attempt fix", "attempts": attempt}
        fixed_command = suggested_fix.replace("$(command_that_failed)", original_command.split()[0] if original_command else "unknown")
        result = self.run_shell_fn(fixed_command)
        try:
            data = json.loads(result)
            if data.get("returncode") == 0:
                self._record_success(original_command, error_text, fixed_command)
                return {"ok": True, "fix_applied": fixed_command, "result": data, "attempts": attempt}
            return {"ok": False, "error": f"Fix failed: {data.get('stderr', '')}", "needs_research": True, "attempts": attempt}
        except Exception:
            return {"ok": False, "error": "Could not parse fix result", "needs_research": True, "attempts": attempt}

    def recover(self, original_command: str, error_text: str, context: str = "") -> dict:
        """Full recovery loop: diagnose → try known fixes → research → retry."""
        diagnosis = self.diagnose(error_text, original_command)
        if diagnosis["confidence"] >= 0.7 and diagnosis.get("past_fixes"):
            result = self.attempt_fix(original_command, error_text, diagnosis, attempt=1)
            if result.get("ok"):
                return result
        if diagnosis.get("needs_research") or not diagnosis.get("suggestions"):
            findings = self.research_error(error_text, original_command, context)
            if findings:
                diagnosis["suggestions"].extend([{"type": "research_finding", "action": f.get("snippet", ""), "source": f.get("url", "")} for f in findings])
        result = self.attempt_fix(original_command, error_text, diagnosis, attempt=2)
        if result.get("ok"):
            return result
        return {"ok": False, "error": error_text, "diagnosis": diagnosis, "findings": findings if 'findings' in locals() else [], "recovery_failed": True, "attempts": 2}

    def _record_success(self, original_command: str, error_text: str, fix_command: str) -> None:
        """Store a successful fix for future use."""
        keywords = self._extract_keywords(error_text)
        fix_entry = {
            "original_command": original_command,
            "error": error_text[:300],
            "fix_command": fix_command,
            "keywords": keywords,
            "success_count": 1,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_used": datetime.now(timezone.utc).isoformat(),
        }
        existing = self.knowledge.get("fixes", [])
        for entry in existing:
            if entry.get("error") == error_text[:300]:
                entry["success_count"] = entry.get("success_count", 0) + 1
                entry["last_used"] = datetime.now(timezone.utc).isoformat()
                self._save_knowledge()
                return
        existing.append(fix_entry)
        self.knowledge["fixes"] = existing[-50:]
        self._save_knowledge()

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
        stop_words = {"the", "and", "for", "was", "not", "but", "are", "with", "this", "that", "from", "have", "has", "had", "been", "were", "will", "would", "could", "should", "can", "may", "might", "must", "shall"}
        return list(set(w for w in words if w not in stop_words))[:10]

    def get_knowledge_summary(self) -> str:
        """Return a summary of learned knowledge."""
        fixes = self.knowledge.get("fixes", [])
        workarounds = self.knowledge.get("tool_workarounds", [])
        lines = [f"Self-knowledge summary:", f"  Learned fixes: {len(fixes)}", f"  Tool workarounds: {len(workarounds)}"]
        if fixes:
            lines.append("  Recent fixes:")
            for fix in fixes[-5:]:
                lines.append(f"    - {fix.get('error', '')[:80]} → {fix.get('fix_command', '')[:60]}")
        return "\n".join(lines)

    def learn_pattern(self, tool_name: str, error_pattern: str, solution: str, notes: str = "") -> None:
        """Manually add a learned pattern."""
        workarounds = self.knowledge.get("tool_workarounds", [])
        workarounds.append({"tool": tool_name, "error_pattern": error_pattern, "action": solution, "notes": notes, "added_at": datetime.now(timezone.utc).isoformat()})
        self.knowledge["tool_workarounds"] = workarounds[-50:]
        self._save_knowledge()

    def prune_old_knowledge(self, max_age_days: int = 90) -> None:
        """Remove old, unused knowledge entries."""
        cutoff = time.time() - (max_age_days * 86400)
        self.knowledge["fixes"] = [f for f in self.knowledge.get("fixes", []) if f.get("last_used") and self._parse_iso(f["last_used"]) > cutoff]
        self.knowledge["last_pruned"] = datetime.now(timezone.utc).isoformat()
        self._save_knowledge()

    def _parse_iso(self, iso_str: str) -> float:
        try:
            return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
