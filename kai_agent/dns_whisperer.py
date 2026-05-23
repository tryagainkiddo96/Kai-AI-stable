"""DNS Whisperer — logs every DNS resolution with process tracking."""
from __future__ import annotations

import re
import subprocess
import threading
import time


class DNSWhisperer:
    """Polls DNS cache, logs queries + owning process."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._seen = set()

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _poll(self):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-DnsClientCache | Select-Object Name, Entry | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if not r.stdout.strip():
                return
            import json as j
            entries = j.loads(r.stdout.strip())
            if isinstance(entries, dict):
                entries = [entries]
            for e in entries:
                domain = (e.get("Name") or e.get("Entry") or "").strip().lower()
                if domain and domain not in self._seen:
                    self._seen.add(domain)
                    proc = self._get_process_for_domain(domain)
                    self.db.log_dns_query(domain, process_name=proc)
        except Exception:
            pass

    def _get_process_for_domain(self, domain: str) -> str:
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-NetUDPEndpoint -LocalPort 53 -ErrorAction SilentlyContinue | Select-Object OwningProcess -First 1 | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=3)
            if r.stdout.strip():
                import json as j
                d = j.loads(r.stdout.strip())
                pid = d.get("OwningProcess", "")
                if pid:
                    r2 = subprocess.run(["powershell", "-NoProfile", "-Command",
                                         f"Get-Process -Id {pid} | Select-Object -ExpandProperty ProcessName"],
                                        capture_output=True, text=True, timeout=2)
                    return r2.stdout.strip()
        except Exception:
            pass
        return ""

    def _loop(self):
        while self._enabled:
            self._poll()
            time.sleep(30)

    def get_history(self, search: str = "", limit: int = 100) -> list[dict]:
        return self.db.query_dns_history(search=search, limit=limit)

    def get_top_domains(self, limit: int = 20) -> list[dict]:
        return self.db.top_domains(limit=limit)
