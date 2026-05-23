"""The Butler — learns daily routines and preps your environment."""
from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime


class Butler:
    """Tracks active window patterns and builds daily activity models."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._last_window = ""
        self._window_start = 0.0
        self._patterns_added = 0

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _loop(self):
        while self._enabled:
            try:
                window = self._get_active_window()
                now = datetime.now()
                if window and window != self._last_window:
                    if self._last_window and self._window_start > 0:
                        duration = time.time() - self._window_start
                        if duration > 60:
                            activity = self._classify_window(self._last_window)
                            self.db.record_activity(now.weekday(), now.hour, activity)
                            self._patterns_added += 1
                    self._last_window = window
                    self._window_start = time.time()
            except Exception:
                pass
            time.sleep(30)

    def _get_active_window(self) -> str:
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "$p=Get-Process|Where-Object{$_.MainWindowHandle -ne [IntPtr]::Zero}|Select-Object -Last 1;$p.MainWindowTitle"],
                               capture_output=True, text=True, timeout=2)
            return r.stdout.strip()
        except Exception:
            return ""

    def _classify_window(self, title: str) -> str:
        t = title.lower()
        if any(x in t for x in ["visual studio", "code", "vscode", "pycharm", "intellij", "cursor", "neovim"]):
            return "coding"
        if any(x in t for x in ["chrome", "firefox", "edge", "brave", "opera", "browser"]):
            return "browsing"
        if any(x in t for x in ["slack", "discord", "teams", "telegram", "whatsapp", "messenger"]):
            return "chat"
        if any(x in t for x in ["outlook", "thunderbird", "mail"]):
            return "email"
        if any(x in t for x in ["spotify", "vlc", "music", "media", "youtube"]):
            return "media"
        if any(x in t for x in ["terminal", "powershell", "cmd", "wsl", "console"]):
            return "terminal"
        if any(x in t for x in ["word", "excel", "powerpoint", "notion", "obsidian"]):
            return "productivity"
        return "other"

    def get_patterns(self) -> list[dict]:
        return self.db.get_patterns()

    def suggest_routine(self) -> list[str]:
        now = datetime.now()
        patterns = self.db.get_patterns(day_of_week=now.weekday())
        current_hour_patterns = [p for p in patterns if p.get("hour") == now.hour]
        next_hour_patterns = [p for p in patterns if p.get("hour") == (now.hour + 1) % 24]

        suggestions = []
        for p in current_hour_patterns:
            if p.get("probability", 0) > 0.5:
                suggestions.append(f"You usually spend this time on {p['activity_type']} ({(p['probability']*100):.0f}% confidence)")
        for p in next_hour_patterns:
            if p.get("probability", 0) > 0.5:
                suggestions.append(f"Next hour is typically {p['activity_type']} — I'll be ready")
        return suggestions

    def stats(self) -> dict:
        patterns = self.db.get_patterns()
        return {"patterns_learned": len(patterns), "total_records": self._patterns_added}
