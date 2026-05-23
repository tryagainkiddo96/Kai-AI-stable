"""Digital Bloodhound — error-triggered forensic snapshots."""
from __future__ import annotations

import json
import subprocess
import threading
import time


class Bloodhound:
    """On error detection, snaps a forensic packet of system state."""

    def __init__(self, db):
        self.db = db
        self._recent_errors: list[dict] = []
        self._max_errors = 20

    def trigger(self, source: str, context: str = ""):
        """Called when an error-like reply is detected."""
        snapshot = self._take_snapshot(source, context)
        self.db.log_forensic(source, snapshot)
        self._recent_errors.append({"time": time.time(), "source": source})
        if len(self._recent_errors) > self._max_errors:
            self._recent_errors.pop(0)
        return snapshot

    def _take_snapshot(self, source: str, context: str = "") -> dict:
        snap = {
            "timestamp": time.time(),
            "trigger_source": source,
            "context": context[:500],
            "event_log_errors": self._get_event_log_errors(),
            "process_tree": self._get_process_tree(),
            "network_connections": self._get_network_connections(),
        }
        return snap

    def _get_event_log_errors(self) -> list[dict]:
        errors = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-WinEvent -FilterHashtable @{LogName='Application';Level=2} -MaxEvents 10 -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, ProviderName, Message | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data[:10]:
                    errors.append({"time": str(item.get("TimeCreated", ""))[:19], "id": item.get("Id", ""), "source": item.get("ProviderName", "")})
        except Exception:
            pass
        return errors

    def _get_process_tree(self) -> list[dict]:
        procs = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Name, Id, @{N='CPU_s';E={[math]::Round($_.CPU,1)}}, WorkingSet64 | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    procs.append({"name": item.get("Name", ""), "pid": item.get("Id", ""), "cpu": item.get("CPU_s", 0), "mem_mb": round(item.get("WorkingSet64", 0) / 1e6, 1)})
        except Exception:
            pass
        return procs

    def _get_network_connections(self) -> list[dict]:
        conns = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object State -eq Established | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, OwningProcess | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data[:20]:
                    conns.append({"local": f"{item.get('LocalAddress','')}:{item.get('LocalPort','')}",
                                  "remote": f"{item.get('RemoteAddress','')}:{item.get('RemotePort','')}",
                                  "pid": item.get("OwningProcess", "")})
        except Exception:
            pass
        return conns

    def get_latest(self) -> list[dict]:
        return self.db.get_forensics(limit=5)

    def get_all(self) -> list[dict]:
        return self.db.get_forensics(limit=50)
