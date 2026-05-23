"""Clipboard Chronomancer — full clipboard history with search and restore."""
from __future__ import annotations

import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional


class ClipboardChron:
    """Logs every clipboard change with source window, provides search + restore."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._last_content = ""
        self._session_id = hex(int(time.time() * 1e6))[2:]

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _get_clipboard(self) -> str:
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                               capture_output=True, text=True, timeout=2)
            return r.stdout.strip()
        except Exception:
            return ""

    def _get_window(self) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$p=Get-Process|Where-Object{$_.MainWindowHandle -ne [IntPtr]::Zero}|Select-Object -Last 1;$p.MainWindowTitle"],
                capture_output=True, text=True, timeout=2)
            return r.stdout.strip()
        except Exception:
            return ""

    def _loop(self):
        while self._enabled:
            try:
                content = self._get_clipboard()
                if content and content != self._last_content and len(content) > 5:
                    self._last_content = content
                    window = self._get_window()
                    self.db.log_clipboard(content, source_window=window, session_id=self._session_id)
            except Exception:
                pass
            time.sleep(1.5)

    def get_history(self, search: str = "", since: float = 0, limit: int = 100) -> list[dict]:
        return self.db.query_clipboard(search=search, since=since, limit=limit)

    def search(self, query: str) -> list[dict]:
        return self.db.query_clipboard(search=query, limit=50)

    def stats(self) -> dict:
        return self.db.clipboard_stats()
