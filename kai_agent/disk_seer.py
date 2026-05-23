"""Disk Seer — SMART health monitoring and capacity prediction."""
from __future__ import annotations

import subprocess
import threading
import time
import re


class DiskSeer:
    """Monitors disk health, capacity trends, predicts full dates."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False

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
                disks = self._get_disks()
                for d in disks:
                    self.db.log_disk(d["drive"], d["total"], d["free"], smart_wear=d.get("wear", 0), label=d.get("label", ""))
            except Exception:
                pass
            time.sleep(3600)

    def _get_disks(self) -> list[dict]:
        disks = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free, @{N='Total';E={$_.Used+$_.Free}}, Root | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    total = item.get("Total", 0) or 0
                    free = item.get("Free", 0) or 0
                    disks.append({
                        "drive": item.get("Root", item.get("Name", "?")),
                        "total": float(total),
                        "free": float(free),
                        "label": "",
                        "wear": 0.0,
                    })
        except Exception:
            pass
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-PhysicalDisk -ErrorAction SilentlyContinue | Select-Object FriendlyName, MediaType, @{N='Wear';E={($_.Wear|Select-Object -First 1)}} | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for i, item in enumerate(data):
                    if i < len(disks):
                        disks[i]["wear"] = float(item.get("Wear", 0) or 0)
        except Exception:
            pass
        return disks

    def get_status(self) -> list[dict]:
        return self.db.latest_disk()

    def get_history(self, drive: str) -> list[dict]:
        return self.db.disk_history(drive)

    def predict_full(self, drive: str) -> dict:
        hist = self.db.disk_history(drive, limit=48)
        if len(hist) < 2:
            return {"drive": drive, "days_remaining": None, "confidence": "insufficient data"}
        rates = []
        for i in range(len(hist) - 1):
            time_diff = hist[i]["timestamp"] - hist[i + 1]["timestamp"]
            space_diff = hist[i + 1]["free_bytes"] - hist[i]["free_bytes"]
            if time_diff > 0 and space_diff < 0:
                rates.append(abs(space_diff) / time_diff)
        if not rates:
            return {"drive": drive, "days_remaining": None, "confidence": "stable"}
        avg_rate = sum(rates) / len(rates)
        if avg_rate <= 0:
            return {"drive": drive, "days_remaining": None, "confidence": "stable"}
        latest = hist[0]
        free = latest["free_bytes"]
        seconds_left = free / avg_rate if avg_rate > 0 else float("inf")
        days = round(seconds_left / 86400, 1)
        return {"drive": drive, "days_remaining": days, "confidence": "high" if len(hist) > 10 else "medium"}
