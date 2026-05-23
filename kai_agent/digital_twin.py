"""Digital Twin — self-health monitoring, provider status, tool diagnostics."""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from kai_agent.ctos_db import CTOSDatabase


class DigitalTwin:
    """Maintains a real-time model of Kai's own health and capabilities."""

    def __init__(self, db: CTOSDatabase, provider_fn: Callable, tools_fn: Callable):
        self.db = db
        self._get_provider = provider_fn
        self._get_tools = tools_fn
        self._running = False
        self._cache: dict[str, Any] = {
            "provider": "unknown",
            "model": "unknown",
            "tools_online": 0,
            "tools_total": 0,
            "uptime": time.time(),
            "last_check": 0,
        }

    def start(self):
        if self._running:
            return
        self._running = True
        t = threading.Thread(target=self._health_loop, daemon=True)
        t.start()

    def _health_loop(self):
        while self._running:
            try:
                self._check_all()
            except Exception:
                pass
            time.sleep(60)

    def _check_all(self):
        now = time.time()
        checks = {}

        # Provider check
        try:
            p = self._get_provider()
            checks["provider"] = {"status": "ok", "detail": p}
            self._cache["provider"] = p
        except Exception as e:
            checks["provider"] = {"status": "error", "detail": str(e)}

        # Provider model
        try:
            m = self._get_tools()
            checks["tools"] = {"status": "ok", "detail": f"{len(m)} tools registered"}
        except Exception as e:
            checks["tools"] = {"status": "error", "detail": str(e)}

        # Database health
        try:
            dev_count = len(self.db.all_devices())
            checks["database"] = {"status": "ok", "detail": f"{dev_count} devices tracked"}
        except Exception as e:
            checks["database"] = {"status": "error", "detail": str(e)}

        # Disk space
        try:
            import shutil
            usage = shutil.disk_usage(Path.cwd())
            gb_free = usage.free / (1024 ** 3)
            checks["disk"] = {"status": "ok" if gb_free > 1 else "warning", "detail": f"{gb_free:.1f} GB free"}
        except Exception as e:
            checks["disk"] = {"status": "error", "detail": str(e)}

        # System resources
        try:
            cpu = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select -ExpandProperty Average"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            ram = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_OperatingSystem | Select @{N='Pct';E={[math]::Round(($_.TotalVisibleMemorySize - $_.FreePhysicalMemory) / $_.TotalVisibleMemorySize * 100)}} | Select -ExpandProperty Pct"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            checks["system"] = {"status": "ok", "detail": f"CPU: {cpu.strip() or '?'}%, RAM: {ram.strip() or '?'}%"}
        except Exception as e:
            checks["system"] = {"status": "error", "detail": str(e)}

        self._cache["last_check"] = now

        for subsystem, info in checks.items():
            self.db.log_health(subsystem, info["status"], info["detail"])

    def status(self) -> dict:
        """Return current health snapshot."""
        uptime_secs = time.time() - self._cache["uptime"]
        hours, rem = divmod(int(uptime_secs), 3600)
        minutes = rem // 60
        summary = self._summarize_health()
        all_ok = all(s["status"] == "ok" for s in summary.values()) if summary else False
        return {
            "status": "healthy" if all_ok else "degraded",
            "provider": self._cache.get("provider", "unknown"),
            "model": self._cache.get("model", "unknown"),
            "tools": self._cache.get("tools_online", 0),
            "total_tools": self._cache.get("tools_total", 0),
            "uptime": f"{hours}h {minutes}m",
            "last_check": "just now" if time.time() - self._cache["last_check"] < 120 else f"{int(time.time() - self._cache['last_check']) // 60}m ago",
            "recent_health": self.db.get_recent_health(20),
            "subsystems": summary,
        }

    def _summarize_health(self) -> dict:
        health = self.db.get_recent_health(50)
        summary = {}
        for h in health:
            sub = h["subsystem"]
            if sub not in summary:
                summary[sub] = {"status": h["status"], "last_detail": h["detail"], "checks": 0}
            summary[sub]["checks"] += 1
        return summary

    def stop(self):
        self._running = False
