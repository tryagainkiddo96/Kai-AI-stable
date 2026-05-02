"""
Kai Autopilot — Clipboard & window monitoring with proactive suggestions.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path


class Autopilot:
    """Monitors clipboard and active window, offers proactive help."""

    def __init__(self, assistant, interval: float = 2.0) -> None:
        self.assistant = assistant
        self.interval = interval
        self.enabled = False
        self._thread: threading.Thread | None = None
        self._last_clipboard = ""
        self._last_window = ""
        self._last_window_text = ""
        self._callbacks: list = []
        self.workspace = assistant.workspace

    def add_callback(self, fn):
        self._callbacks.append(fn)

    def _notify(self, message, data=None):
        for cb in self._callbacks:
            try:
                cb(message, data)
            except Exception:
                pass

    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.enabled = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _get_clipboard(self):
        import subprocess
        try:
            result = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                                    capture_output=True, text=True, timeout=2)
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_active_window(self):
        import subprocess
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$proc = (Get-Process | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -Last 1); "
                 "$proc.MainWindowTitle + '|' + $proc.Name"],
                capture_output=True, text=True, timeout=2)
            parts = result.stdout.strip().split("|", 1)
            return (parts[0], parts[1]) if len(parts) == 2 else ("", "")
        except Exception:
            return ("", "")

    def _analyze(self, text):
        triggers = []

        # Error patterns
        errors = [
            (r"Traceback \(most recent call last\)", "Python traceback detected"),
            (r"ModuleNotFoundError: No module named", "Missing Python module"),
            (r"FileNotFoundError", "File not found error"),
            (r"ConnectionRefusedError", "Connection refused"),
            (r"error C\d+:|fatal error:|undefined reference to", "C/C++ compiler error"),
            (r"npm ERR|yarn error|pnpm ERR", "Node package manager error"),
            (r"docker:|dockerd:", "Docker error"),
            (r"git:(?!/)", "Git error"),
            (r"(?:Exception|Error):\s+.+", "Runtime error detected"),
        ]
        for pattern, label in errors:
            if re.search(pattern, text, re.IGNORECASE):
                triggers.append(("error", label, text[:500]))

        # URL detection
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
        if urls:
            triggers.append(("url", f"Found {len(urls)} URL(s)", {"urls": urls[:5]}))

        # Code detection
        if re.search(r'(def |class |import |from |async |await |return |print\(|console\.log|const |let |var )', text):
            triggers.append(("code", "Code snippet detected", text[:300]))

        # Stack trace
        if re.search(r'at\s+\S+\s+\(.*?:\d+:\d+\)', text):
            triggers.append(("stacktrace", "Stack trace detected", text[:500]))

        # TODO/FIXME
        todos = re.findall(r'(?:TODO|FIXME|HACK|XXX):\s*(.+)', text)
        if todos:
            triggers.append(("todo", f"{len(todos)} TODO(s) found", todos[:5]))

        return triggers

    def _loop(self):
        while self.enabled:
            try:
                clipboard = self._get_clipboard()
                title, proc = self._get_active_window()

                # Check clipboard changes
                if clipboard and clipboard != self._last_clipboard and len(clipboard) > 10:
                    self._last_clipboard = clipboard
                    triggers = self._analyze(clipboard)
                    for trigger_type, label, data in triggers:
                        if trigger_type == "error":
                            self._notify(f"🔴 Error spotted in clipboard: {label}\nWant me to diagnose it?")
                        elif trigger_type == "url":
                            self._notify(f"🌐 URLs detected. Want me to fetch and summarize?")
                        elif trigger_type == "code":
                            self._notify(f"💻 Code copied. Want me to review or improve it?")
                        elif trigger_type == "stacktrace":
                            self._notify(f"📋 Stack trace found. Want me to trace the issue?")
                        elif trigger_type == "todo":
                            self._notify(f"📝 TODOs found: {', '.join(str(t)[:50] for t in data[:2])}")

                # Track window context
                if title and title != self._last_window:
                    self._last_window = title
                    self._notify(f"🪟 Active window: {title} ({proc})")

                # Watch for known dev tools
                dev_tools = ["visual studio", "vscode", "pycharm", "intellij", "cursor", "neovim", "vim"]
                if any(d in title.lower() for d in dev_tools):
                    self._notify("💡 Detected dev environment. I'm ready to help with code.")

            except Exception:
                pass

            time.sleep(self.interval)

    def status(self):
        return {"enabled": self.enabled, "interval": self.interval, "thread_alive": self._thread.is_alive() if self._thread else False}
