"""Command Registry — replaces fragile string-prefix tool routing.

Commands are registered with regex patterns and handlers.
Dispatch matches user input against patterns in registration order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class CommandEntry:
    pattern: re.Pattern
    name: str
    handler: Callable
    description: str = ""


class CommandRegistry:
    """Register and dispatch slash/user commands to handlers."""

    def __init__(self) -> None:
        self._commands: list[CommandEntry] = []

    def register(self, name: str, pattern: str, handler: Callable, description: str = "") -> None:
        """Register a command with a regex pattern and handler function.

        The handler receives the match object and should return a string result.
        An empty string means 'not handled, try next command'.
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        self._commands.append(CommandEntry(pattern=compiled, name=name, handler=handler, description=description))

    def dispatch(self, user_input: str) -> str:
        """Try each registered command against user input. Return first match result."""
        for entry in self._commands:
            match = entry.pattern.match(user_input.strip())
            if match:
                result = entry.handler(match)
                if result:
                    return result
        return ""

    def list_commands(self) -> list[dict]:
        return [{"name": c.name, "pattern": c.pattern.pattern, "description": c.description} for c in self._commands]


def build_default_registry(assistant) -> CommandRegistry:
    """Build the standard command registry wired to an assistant instance."""
    registry = CommandRegistry()

    registry.register(
        "remember",
        r"^/remember\s+(.+)$",
        lambda m: f"Memory saved: {assistant.remember(m.group(1))}",
        "Save something to Kai's memory",
    )

    registry.register(
        "memory_view",
        r"^/memory$",
        lambda m: _view_memory(assistant),
        "Show stored memory",
    )

    registry.register(
        "memory_search",
        r"^/memory\s+(.+)$",
        lambda m: _search_memory(assistant, m.group(1)),
        "Search memory",
    )

    registry.register(
        "screen",
        r"^/screen",
        lambda m: assistant.tools.capture_screen_ocr(),
        "Capture screen with OCR",
    )

    registry.register(
        "run",
        r"^/run\s+(.+)$",
        lambda m: assistant.tools.run_shell(m.group(1)),
        "Run a shell command",
    )

    registry.register(
        "read",
        r"^/read\s+(.+)$",
        lambda m: assistant.tools.read_file(m.group(1)),
        "Read a file",
    )

    registry.register(
        "ls",
        r"^/ls\s*(.*)$",
        lambda m: assistant.tools.list_files(m.group(1).strip() or "."),
        "List files in a directory",
    )

    registry.register(
        "policy_status",
        r"^/policy\s+status$",
        lambda m: assistant.tools.policy_status(),
        "Show tool policy status",
    )

    registry.register(
        "policy_mode",
        r"^/policy\s+mode\s+(\w[\w-]*)$",
        lambda m: assistant.tools.set_policy_mode(m.group(1)),
        "Set tool policy mode",
    )

    registry.register(
        "capabilities",
        r"^/capabilities$",
        lambda m: assistant.tools.list_capabilities(),
        "List available capabilities",
    )

    registry.register(
        "autonomy_on",
        r"^/autonomy\s+on$",
        lambda m: assistant.autonomy.enable(),
        "Enable guarded autonomy",
    )

    registry.register(
        "autonomy_off",
        r"^/autonomy\s+off$",
        lambda m: assistant.autonomy.disable(),
        "Disable autonomy",
    )

    registry.register(
        "autonomy_tick",
        r"^/autonomy\s+tick$",
        lambda m: assistant.autonomy.tick(),
        "Run one autonomous step",
    )

    registry.register(
        "scan",
        r"^/scan\s+(.+)$",
        lambda m: assistant.tools.active_recon(m.group(1)),
        "Run nmap scan against target",
    )

    registry.register(
        "exploit_search",
        r"^/exploit-search\s+(.+)$",
        lambda m: assistant.tools.search_exploits(m.group(1)),
        "Search for known exploits",
    )

    registry.register(
        "web_recon",
        r"^/web-recon\s+(.+)$",
        lambda m: assistant.tools.web_recon(m.group(1)),
        "Run web reconnaissance (nikto)",
    )

    registry.register(
        "dir_bust",
        r"^/dir-bust\s+(.+)$",
        lambda m: assistant.tools.dir_busting(m.group(1)),
        "Run directory busting (gobuster)",
    )

    registry.register(
        "vuln_scan",
        r"^/vuln-scan\s+(.+)$",
        lambda m: assistant.tools.vulnerability_scan(m.group(1)),
        "Run vulnerability scan",
    )

    registry.register(
        "engagement_create",
        r"^/engagement\s+create\s+(\S+)\s+(\S+)\s+(.+)$",
        lambda m: assistant.tools.create_engagement(m.group(1), m.group(2), m.group(3)),
        "Create a new pentest engagement",
    )

    registry.register(
        "engagement_list",
        r"^/engagements$",
        lambda m: assistant.tools.list_engagements(),
        "List all pentest engagements",
    )

    registry.register(
        "self_knowledge",
        r"^/self-knowledge$",
        lambda m: assistant.self_improver.get_knowledge_summary(),
        "Show learned knowledge and fixes",
    )

    registry.register(
        "learn",
        r"^/learn\s+(\S+)\s+(.+)\s+->\s+(.+)$",
        lambda m: _learn_pattern(assistant, m.group(1), m.group(2), m.group(3)),
        "Teach Kai a fix: /learn <tool> <error> -> <solution>",
    )

    return registry


def _learn_pattern(assistant, tool: str, error: str, solution: str) -> str:
    assistant.self_improver.learn_pattern(tool, error, solution)
    return f"Learned: when {tool} fails with '{error}', try '{solution}'"


def _view_memory(assistant) -> str:
    notes = assistant.memory.load_notes()
    if not notes:
        return "Memory is empty."
    lines = [f"- [{n.get('category', 'general')}] {n.get('content', '')}" for n in notes[-10:]]
    return "\n".join(lines)


def _search_memory(assistant, query: str) -> str:
    results = assistant.memory.search(query)
    if not results:
        return f"No memory matches for: {query}"
    lines = [f"- [{r.get('category', '')}] {r.get('content', '')}" for r in results]
    return f"Memory results for '{query}':\n" + "\n".join(lines)
