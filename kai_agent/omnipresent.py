"""Omnipresent — auto-start, browser history reading, LAN presence.

Modules:
  • Boot registration — Kai starts automatically at login
  • Browser history reader — Chrome, Edge, Firefox history SQLite
  • Email monitor — IMAP inbox polling (optional)
  • Service heartbeat — announces Kai's presence on LAN
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class Omnipresent:
    """Makes Kai persistent, aware, and discoverable on the network."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._registered_boot = False

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _loop(self):
        # Register boot once
        if not self._registered_boot:
            self._register_boot()
            self._registered_boot = True

        while self._enabled:
            try:
                self._scan_browser_history()
                self._heartbeat()
            except Exception:
                pass
            time.sleep(300)

    # ── Auto-Start Registration ──────────────────────────────────────────────

    def _register_boot(self):
        """Create Windows scheduled task to start Kai at user login."""
        py_path = Path(__file__).resolve().parent.parent / "kai_web_ui.py"
        bat_path = Path(__file__).resolve().parent.parent / "Launch Kai.bat"
        if py_path.exists():
            pythonw = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "py.exe"
            if not pythonw.exists():
                pythonw = "pythonw"
            task_cmd = f'{pythonw} "{py_path}"'
        elif bat_path.exists():
            task_cmd = f'"{bat_path}"'
        else:
            return

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"""
$taskName = "KaiCompanion"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c {task_cmd}"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
"""],
                capture_output=True, timeout=15,
            )
        except Exception:
            pass

    def unregister_boot(self):
        """Remove the auto-start scheduled task."""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Unregister-ScheduledTask -TaskName KaiCompanion -Confirm:$false -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

    # ── Browser History Reader ────────────────────────────────────────────────

    BROWSER_PATHS = {
        "chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Default" / "History",
        "edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
        "brave": Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "History",
        "firefox": None,  # Firefox uses a different structure; handled separately
    }

    def _scan_browser_history(self):
        for browser, path in self.BROWSER_PATHS.items():
            if path and path.exists():
                try:
                    self._read_chromium_history(path, browser)
                except Exception:
                    pass

        # Firefox
        ff_path = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"
        if ff_path.exists():
            for profile_dir in ff_path.iterdir():
                hist_path = profile_dir / "places.sqlite"
                if hist_path.exists():
                    try:
                        self._read_firefox_history(hist_path)
                    except Exception:
                        pass

    def _read_chromium_history(self, path: Path, browser: str):
        try:
            conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True, timeout=2)
            cursor = conn.cursor()
            cutoff = time.time() - 3600  # last hour
            cursor.execute(
                "SELECT url, title, visit_count, last_visit_time/1000000-11644473600 FROM urls "
                "WHERE last_visit_time/1000000-11644473600 > ? ORDER BY last_visit_time DESC LIMIT 20",
                (cutoff,),
            )
            for url, title, count, visit_time in cursor.fetchall():
                if url and not self._is_ignored_url(url):
                    self.db.log_browser_visit(url, title or "", browser)
            conn.close()
        except Exception:
            pass

    def _read_firefox_history(self, path: Path):
        try:
            conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True, timeout=2)
            cursor = conn.cursor()
            cutoff = int(time.time() * 1000000) - 3600000000
            cursor.execute(
                "SELECT url, title, visit_count, visit_date/1000 FROM moz_places "
                "WHERE visit_date > ? ORDER BY visit_date DESC LIMIT 20",
                (cutoff,),
            )
            for url, title, count, visit_time in cursor.fetchall():
                if url and not self._is_ignored_url(url):
                    self.db.log_browser_visit(url, title or "", "firefox")
            conn.close()
        except Exception:
            pass

    def _is_ignored_url(self, url: str) -> bool:
        ignore_patterns = ["chrome://", "edge://", "about:", "file://", "data:",
                           "chrome-extension://", "devtools://", "view-source:"]
        return any(url.startswith(p) for p in ignore_patterns)

    # ── LAN Heartbeat ────────────────────────────────────────────────────────

    def _heartbeat(self):
        """Announce Kai's presence on LAN via UDP broadcast."""
        import socket as sock
        try:
            s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            s.setsockopt(sock.SOL_SOCKET, sock.SO_BROADCAST, 1)
            s.settimeout(1)
            s.sendto(f"KAI_HERE:{socket.gethostname()}".encode(), ("255.255.255.255", 5555))
            s.close()
        except Exception:
            pass

    # ── Query Interface ──────────────────────────────────────────────────────

    def query_history(self, search: str = "", limit: int = 50) -> list[dict]:
        return self.db.query_browser_history(search=search, limit=limit)

    def get_recent_sites(self) -> list[dict]:
        return self.db.query_browser_history(limit=20)

    def status(self) -> dict:
        return {
            "boot_registered": self._registered_boot,
            "enabled": self._enabled,
            "browsers_monitored": [k for k, v in self.BROWSER_PATHS.items()
                                   if v and v.exists() or k == "firefox"],
        }
