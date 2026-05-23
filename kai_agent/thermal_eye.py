"""Thermal Imaging — CPU/GPU temp tracking with sparkline history."""
from __future__ import annotations

import subprocess
import threading
import time
import re


class ThermalEye:
    """Polls CPU/GPU temperatures and logs to CTOS DB."""

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
                temps = self._get_temps()
                for zone, celsius in temps.items():
                    self.db.log_temperature(zone, celsius)
            except Exception:
                pass
            time.sleep(30)

    def _get_temps(self) -> dict[str, float]:
        temps = {}
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-CimInstance MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object InstanceName, Temperature | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get("InstanceName", "CPU").split("\\")[-1][:20]
                    k = item.get("Temperature", 0)
                    celsius = round((k - 2731.5) / 10.0, 1) if k > 1000 else round(k / 10.0, 1)
                    if 0 < celsius < 120:
                        temps[name] = celsius
        except Exception:
            pass
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>$null"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                val = r.stdout.strip()
                temps["GPU"] = float(val)
        except Exception:
            pass
        return temps

    def get_current(self) -> dict:
        return self.db.latest_temps()

    def get_history(self, zone: str = "", hours: int = 24) -> list[dict]:
        return self.db.query_temperatures(zone=zone, hours=hours)
