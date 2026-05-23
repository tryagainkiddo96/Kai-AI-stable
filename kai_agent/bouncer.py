"""The Bouncer — ARP-based intruder detection and alerting."""
from __future__ import annotations

import json
import subprocess
import threading
import time


class Bouncer:
    """Watches ARP table for new MACs, detects intruders, logs alerts."""

    def __init__(self, db, ctos=None):
        self.db = db
        self._ctos = ctos
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._known_entries: dict[str, dict] = self._load_known_entries()

    def _load_known_entries(self) -> dict[str, dict]:
        try:
            return {e["ip"]: {"mac": e["mac"], "first_seen": e["first_seen"]} for e in self.db.get_arp_entries()}
        except Exception:
            return {}

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
                entries = self._get_arp_table()
                for ip, mac, vendor in entries:
                    self.db.upsert_arp(ip, mac, vendor)
                    if ip not in self._known_entries:
                        self._known_entries[ip] = {"mac": mac, "first_seen": time.time()}
                        if self._ctos:
                            self._ctos.db.add_urban_event("proximity", f"New device detected: {ip} ({vendor})",
                                                          {"ip": ip, "mac": mac}, source="bouncer")
                    elif self._known_entries[ip]["mac"] != mac:
                        self.db.mark_intruder(ip)
                        if self._ctos:
                            self._ctos.db.add_urban_event("proximity", f"ARP spoof detected on {ip}! MAC changed",
                                                          {"ip": ip, "old_mac": self._known_entries[ip]["mac"], "new_mac": mac},
                                                          source="bouncer")
                        self._known_entries[ip] = {"mac": mac, "first_seen": self._known_entries[ip]["first_seen"]}
            except Exception:
                pass
            time.sleep(15)

    def _get_arp_table(self) -> list[tuple[str, str, str]]:
        entries = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.State -eq 'Reachable'} | Select-Object IPAddress, LinkLayerAddress | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    ip = item.get("IPAddress", "")
                    mac = item.get("LinkLayerAddress", "")
                    vendor = self._oui_lookup(mac[:8].replace("-", "").upper()) if mac else ""
                    if ip and mac and ip != "0.0.0.0":
                        entries.append((ip, mac, vendor))
        except Exception:
            pass
        return entries

    @staticmethod
    def _oui_lookup(prefix: str) -> str:
        oui_db = {
            "00037F": "Intel", "0013CE": "Intel", "001C25": "Intel",
            "0050B6": "Intel", "0050F2": "Intel", "0021E8": "HP",
            "002713": "HP", "001B26": "Apple", "001E52": "Apple",
            "0026B0": "Apple", "003065": "Apple", "005094": "Apple",
            "CC5C75": "Samsung", "0019B7": "Samsung", "00276E": "Samsung",
            "001B10": "Dell", "0021CC": "Dell", "F04DA2": "Dell",
            "00219B": "ASUS", "001EE5": "ASUS", "00177A": "ASUS",
            "001388": "Sony", "0025E0": "Sony", "0022B0": "TP-Link",
            "005E5C": "TP-Link", "C0C1C0": "TP-Link", "001348": "Cisco",
            "0016C2": "Cisco", "00252B": "Cisco", "0026CB": "Cisco",
            "A4D1D2": "Razer", "0011B2": "Microsoft", "0050F2": "Microsoft",
            "000B4D": "HTC", "00F6F3": "Atheros", "001195": "Broadcom",
            "00146B": "Realtek", "0023CD": "Realtek",
        }
        return oui_db.get(prefix, "Unknown")

    def get_entries(self) -> list[dict]:
        return self.db.get_arp_entries()

    def get_intruders(self) -> list[dict]:
        entries = self.db.get_arp_entries()
        return [e for e in entries if e.get("is_intruder")]
