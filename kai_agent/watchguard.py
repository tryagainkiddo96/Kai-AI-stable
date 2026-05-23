"""Watchguard — monitors lock screen, screensaver, and idle state."""
from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime


class Watchguard:
    """Detects screen lock/unlock, screensaver, and prolonged idle."""

    def __init__(self, db, notify_fn=None):
        self.db = db
        self._notify = notify_fn
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._was_locked = False
        self._idle_start = 0.0
        self._idle_notified = False

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
                self._check_lock_state()
                self._check_idle()
            except Exception:
                pass
            time.sleep(5)

    def _check_lock_state(self):
        locked = self._is_locked()
        if locked and not self._was_locked:
            self._was_locked = True
            self._on_lock()
        elif not locked and self._was_locked:
            self._was_locked = False
            self._on_unlock()

    def _is_locked(self) -> bool:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$s=Get-Process -Name LogonUI -ErrorAction SilentlyContinue; if($s){'locked'}else{'unlocked'}"],
                capture_output=True, text=True, timeout=3,
            )
            return r.stdout.strip() == "locked"
        except Exception:
            return False

    def _on_lock(self):
        self._idle_start = 0.0
        self._idle_notified = False
        if self.db:
            self.db.journal_entry("screen_lock", {"state": "locked"},
                                  source="watchguard", importance=1)
            self.db.add_urban_event("proximity", "Screen locked",
                                    {"state": "locked"}, source="watchguard")

    def _on_unlock(self):
        if self.db:
            self.db.journal_entry("screen_lock", {"state": "unlocked"},
                                  source="watchguard", importance=1)
            self.db.add_urban_event("proximity", "Screen unlocked",
                                    {"state": "unlocked"}, source="watchguard")

    def _check_idle(self):
        idle_secs = self._get_idle_seconds()
        if idle_secs > 900 and not self._idle_notified:
            self._idle_notified = True
            if self.db:
                self.db.journal_entry("idle_detect",
                                      {"idle_seconds": idle_secs},
                                      source="watchguard", importance=0)

    def _get_idle_seconds(self) -> int:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[PInvoke.UserInput]::IdleTime | Select-Object -ExpandProperty TotalSeconds"],
                capture_output=True, text=True, timeout=3,
            )
            return int(float(r.stdout.strip())) if r.stdout.strip() else 0
        except Exception:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "$t=[PInvoke.UserInput]::IdleTime; $t.TotalSeconds"],
                    capture_output=True, text=True, timeout=3,
                )
                return int(float(r.stdout.strip())) if r.stdout.strip() else 0
            except Exception:
                return 0

    def is_locked(self) -> bool:
        return self._was_locked

    def status(self) -> dict:
        return {
            "locked": self._was_locked,
            "enabled": self._enabled,
            "idle_seconds": self._get_idle_seconds(),
        }
