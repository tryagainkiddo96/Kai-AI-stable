"""CTOS Engine — NetMap, Device Dossiers, Urban Scanner, OS fingerprinting."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from kai_agent.ctos_db import CTOSDatabase


_OUI_DB = {
    "b4:2e:99": "Intel", "34:f1:50": "Intel", "d8:31:34": "Intel",
    "18:a5:ff": "Intel", "e0:01:c7": "Huawei", "10:59:32": "Hon Hai",
    "b4:2e:99": "Intel", "2a:eb:c9": "Amazon", "94:bb:43": "Tenda",
    "7e:62:8b": "Unknown", "da:31:34": "Intel", "00:1a:11": "Cisco",
    "00:0c:29": "VMware", "00:50:56": "VMware", "00:15:5d": "Hyper-V",
    "08:00:27": "VirtualBox", "3c:22:3e": "Furukawa", "ac:84:c6": "Huawei",
    "60:30:d4": "Xiaomi", "00:11:32": "Samsung", "80:2a:a8": "Xiaomi",
    "ec:df:3a": "Espressif", "f4:5c:89": "Espressif", "24:0a:c4": "Espressif",
    "b8:27:eb": "Raspberry Pi", "dc:a6:32": "Raspberry Pi", "e4:5f:01": "Raspberry Pi",
    "00:1b:44": "Roku", "00:aa:bb": "QEMU", "52:54:00": "QEMU",
    "00:23:ae": "SDMC", "bc:6e:4a": "Apple", "f0:18:98": "Apple",
    "70:56:51": "Belkin", "00:17:88": "Apple", "78:4f:43": "Apple",
    "ac:bc:32": "Apple", "00:25:00": "Apple", "00:0a:95": "Apple",
    "38:c9:86": "Google", "8c:de:f9": "Google", "a4:77:33": "Google",
    "18:93:d7": "Google", "00:1e:42": "Google", "f4:f5:d8": "Google",
    "dc:0b:1c": "Amazon", "ac:63:be": "Amazon", "d0:7e:35": "Amazon",
    "44:e9:dd": "HTC", "8c:89:a5": "LG", "00:1a:a0": "LG",
    "90:f8:28": "Sony", "00:24:be": "Sony", "d0:cb:3e": "OnePlus",
    "9c:fc:e8": "OnePlus", "f0:7d:68": "Xiaomi", "a4:9a:58": "HMD/Nokia",
    "50:3e:aa": "Huawei", "d4:3a:2c": "Huawei", "dc:44:6d": "Hikvision",
    "2e:4a:bc": "Hikvision", "b4:a4:e3": "Dahua", "68:54:f3": "Dahua",
    "00:09:45": "Axis", "ac:cc:8e": "Axis", "00:40:8c": "Amcrest",
    "00:12:2b": "Synology", "00:11:32": "Synology", "00:21:2f": "Netgear",
    "c0:3f:0e": "Netgear", "14:cc:20": "TP-Link", "60:a4:4c": "TP-Link",
    "ec:17:66": "ASUS", "10:bf:48": "ASUS", "d4:6e:0e": "ASUS",
    "18:31:bf": "D-Link", "1c:5f:2b": "D-Link", "00:0e:8e": "Ubiquiti",
    "74:83:c2": "Ubiquiti", "68:72:51": "Aruba", "00:0b:86": "Meraki",
    "e0:63:da": "Cisco Meraki", "a0:36:9f": "Canon", "3c:2c:99": "Epson",
    "00:0b:09": "HP", "48:45:20": "HP", "08:00:27": "Oracle",
    "00:50:56": "VMware", "00:0c:29": "VMware", "00:15:5d": "Microsoft",
    "3c:22:3e": "Furukawa", "00:04:f2": "Shenzhen", "8c:ae:4c": "Roku",
}


def _oui_vendor(mac: str) -> str:
    if not mac:
        return "Unknown"
    oui = ":".join(mac.split("-")[:3]).lower() if "-" in mac else mac[:8].lower()
    return _OUI_DB.get(oui, "Unknown")


def _device_type(vendor: str, hostname: str, ports: list) -> str:
    v = vendor.lower()
    h = hostname.lower()
    port_nums = {p["port"] if isinstance(p, dict) else p for p in ports}
    if any(p in port_nums for p in [80, 443, 8080, 8443, 554, 8554]):
        if any(p in port_nums for p in [554, 8554]):
            return "camera"
        if vend_check(v, "hub", "unifi", "meraki", "cisco", "aruba"):
            return "network"
        return "server"
    if vend_check(v, "apple", "samsung", "google", "xiaomi", "oneplus", "htc", "lg", "sony", "nokia"):
        return "phone"
    if vend_check(v, "raspberry", "espressif", "arduino"):
        return "iot"
    if vend_check(v, "vmware", "hyper-v", "virtualbox", "oracle", "qemu"):
        return "server"
    if v in ("Cisco", "Netgear", "TP-Link", "D-Link", "ASUS", "Ubiquiti", "Aruba", "Meraki"):
        return "network"
    if vend_check(v, "canon", "epson", "hp", "brother"):
        return "printer"
    if h and ("phone" in h or "iphone" in h or "samsung" in h or "pixel" in h):
        return "phone"
    return "pc"


def vend_check(vendor: str, *names: str) -> bool:
    vl = vendor.lower()
    return any(n in vl for n in names)


def _guess_os(ttl: int) -> str:
    if ttl <= 64:
        return "Linux/Unix"
    elif ttl <= 128:
        return "Windows"
    elif ttl <= 255:
        return "Network Device"
    return "Unknown"


class CTOSEngine:
    """Central CTOS engine — NetMap data, Breach dossiers, Urban Scanner, device tracking."""

    def __init__(self, db: CTOSDatabase):
        self.db = db
        self._urban_running = False
        self._known_macs: dict[str, str] = {}
        self._scan_in_progress = False
        self._scan_count = 0
        self._scan_done = False
        self._scan_progress: list[str] = []

    # ── NetMap ──────────────────────────────────────────────────────────────────

    def build_netmap(self) -> dict:
        """Build the network map data structure for the d3.js visualization."""
        devices_raw = self.db.all_devices()

        nodes = []
        edges = []
        device_map = {}

        for i, d in enumerate(devices_raw):
            ports = d.get("ports", [])
            ip = d.get("ip", "")
            if not ip:
                continue
            dtype = _device_type(d.get("vendor", ""), d.get("hostname", ""), ports)
            node = {
                "id": ip,
                "index": i,
                "ip": ip,
                "mac": d.get("mac", ""),
                "vendor": d.get("vendor", ""),
                "hostname": d.get("hostname", ""),
                "type": dtype,
                "os": d.get("os_guess", ""),
                "ports": ports,
                "smb_access": bool(d.get("smb_access")),
                "rdp_open": bool(d.get("rdp_open")),
                "first_seen": d.get("first_seen", 0),
                "last_seen": d.get("last_seen", 0),
                "tags": d.get("tags", []),
            }
            nodes.append(node)
            device_map[ip] = node

        # Build edges from port relationships
        for node in nodes:
            ip = node["ip"]
            ports = node.get("ports", [])
            # If has SMB/RDP/WinRM — connect to gateway-like services
            for p in ports:
                pnum = p["port"] if isinstance(p, dict) else p
                if pnum in (445, 139, 3389, 5985, 5986):
                    edges.append({
                        "source": ip,
                        "target": ip,  # will be gateway
                        "type": "service",
                        "port": pnum,
                        "protocol": "tcp",
                    })

        return {"nodes": nodes, "edges": edges, "count": len(nodes)}

    def _quick_scan(self) -> list[dict]:
        """Active network scan: ARP + ping sweep of local /24 subnet."""
        self._scan_progress = []
        try:
            # 1. ARP — grab every IPv4 from arp -a output (locale-proof, format-proof)
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "arp -a | ForEach-Object { ($_.Trim() -split '\\s+',2)[0] }"],
                capture_output=True, text=True, timeout=8
            ).stdout.strip()
            # Filter valid IPv4, exclude loopback/multicast/broadcast
            arp_ips = set()
            for token in out.split():
                t = token.strip()
                if t.count(".") != 3:
                    continue
                parts = t.split(".")
                if not parts[0].isdigit():
                    continue
                n = int(parts[0])
                if n in (127, 224, 239, 0) or n < 1 or n > 254:
                    continue
                # Exclude network (x.x.x.0) and broadcast (x.x.x.255)
                last = parts[-1]
                if last == "0" or last == "255":
                    continue
                arp_ips.add(t)

            # 2. Ping sweep the whole /24 subnet
            sweep_ips = set()
            try:
                first_ip = next(iter(arp_ips), None)
                if not first_ip:
                    gw = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-NetRoute -DestinationPrefix '0.0.0.0/0').NextHop | Select -First 1"],
                        capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                    if gw.count(".") == 3:
                        first_ip = gw
                if first_ip:
                    subnet = ".".join(first_ip.split(".")[:3]) + "."
                    sweep = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"$s='{subnet}';1..254|%{{$ip=$s+$_;try{{if([Net.NetworkInformation.Ping]::new().Send($ip,150).Status -eq 'Success'){{$ip}}}}catch{{}}}}"],
                        capture_output=True, text=True, timeout=60
                    ).stdout.strip()
                    for l in sweep.split():
                        l = l.strip()
                        if l.count(".") == 3:
                            sweep_ips.add(l)
            except Exception:
                pass

            # 3. Merge and dedup
            all_ips = sorted(arp_ips | sweep_ips)[:100]

            # 4. Enrich each device with progress updates
            devices = []
            for ip in all_ips:
                d = self._enrich_device(ip, fast=True)
                if d:
                    devices.append(d)
                    self._scan_progress.append(ip)
                self._scan_count = len(devices)
            return devices
        except Exception:
            return []

    def start_scan(self):
        """Fire off a background scan. Frontend polls get_scan_status()."""
        if self._scan_in_progress:
            return
        self._scan_in_progress = True
        self._scan_done = False
        self._scan_count = 0
        t = threading.Thread(target=_run_bg_scan, args=(self,), daemon=True)
        t.start()

    def get_scan_status(self) -> dict:
        db_count = len(self.db.all_devices()) if self.db else 0
        return {"running": self._scan_in_progress, "done": self._scan_done,
                "count": self._scan_count, "db_count": db_count,
                "progress": list(self._scan_progress)}

    # ── Breach Dossier ──────────────────────────────────────────────────────────

    def breach(self, ip: str) -> dict:
        """Full device dossier — all known intelligence on an IP."""
        device = self.db.get_device(ip)
        if not device:
            device = self._enrich_device(ip)
        # Re-enrich skeleton records (IP-only, no real data)
        elif not device.get("mac") and not device.get("hostname") and not device.get("ports"):
            enriched = self._enrich_device(ip, fast=True)
            if enriched:
                device = enriched
        if not device:
            return {"ip": ip, "error": "Device not found and unreachable"}

        breach_log = self.db.get_breach_log(ip)
        ports = device.get("ports", [])

        # Quick port re-check for key services
        current_services = {p["port"]: p for p in ports}
        for port, svc in [(445, "SMB"), (3389, "RDP"), (22, "SSH"), (80, "HTTP"), (443, "HTTPS"), (5985, "WinRM"), (5986, "WinRM-HTTPS")]:
            if port not in current_services:
                try:
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Test-NetConnection -ComputerName {ip} -Port {port} -WarningAction SilentlyClose | Select -ExpandProperty TcpTestSucceeded"],
                        capture_output=True, text=True, timeout=3
                    ).stdout.strip()
                    if "True" in r:
                        ports.append({"port": port, "service": svc, "state": "open"})
                except Exception:
                    pass

        dossier = {
            "ip": ip,
            "mac": device.get("mac", ""),
            "vendor": device.get("vendor", ""),
            "hostname": device.get("hostname", ""),
            "os": device.get("os_guess", self._fingerprint_os(ip)),
            "type": _device_type(device.get("vendor", ""), device.get("hostname", ""), ports),
            "ports": ports,
            "smb_access": bool(self._check_admin_share(ip)),
            "rdp_open": any(p["port"] == 3389 for p in ports),
            "tailscale_ip": device.get("tailscale_ip", ""),
            "first_seen": device.get("first_seen", 0),
            "last_seen": device.get("last_seen", 0),
            "actions": self._available_actions(ports),
            "breach_history": breach_log,
            "tags": device.get("tags", []),
        }

        # Log the breach query
        self.db.log_breach(ip, "breach_query", f"Dossier generated: {len(ports)} ports")
        self.db.upsert_device(ip, ports=ports, os_guess=dossier["os"],
                              smb_access=1 if dossier["smb_access"] else 0,
                              rdp_open=1 if dossier["rdp_open"] else 0)
        return dossier

    def _fingerprint_os(self, ip: str) -> str:
        """TTL-based OS fingerprint."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"ping -n 1 {ip} | Select-String 'TTL='"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            m = re.search(r'TTL=(\d+)', r, re.I)
            if m:
                return _guess_os(int(m.group(1)))
        except Exception:
            pass
        return ""

    def _check_admin_share(self, ip: str) -> bool:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Test-Path '\\\\{ip}\\C$' -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=3
            ).stdout.strip()
            return "True" in r
        except Exception:
            return False

    def _available_actions(self, ports: list) -> list[str]:
        actions = []
        port_nums = {p["port"] if isinstance(p, dict) else p for p in ports}
        if any(p in port_nums for p in (139, 445)):
            actions.append("smb_enumerate")
        if 3389 in port_nums:
            actions.append("rdp_connect")
        if any(p in port_nums for p in (80, 443, 8080, 8443)):
            actions.append("web_audit")
        if any(p in port_nums for p in (5985, 5986)):
            actions.append("winrm")
        if 22 in port_nums:
            actions.append("ssh")
        if any(p in port_nums for p in (21,)):
            actions.append("ftp_check")
        return actions

    def _enrich_device(self, ip: str, fast: bool = False) -> Optional[dict]:
        """Gather all intel on a single IP and store in DB.
        
        When fast=True, skips Tailscale, uses shorter port timeout (300ms),
        and only checks the most common ports.
        """
        mac = ""
        vendor = ""
        hostname = ""
        ports = []
        os_guess = ""
        ts_ip = ""

        try:
            arp = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"arp -a | Select-String '{ip}'"],
                capture_output=True, text=True, timeout=3
            ).stdout.strip()
            for line in arp.split("\n"):
                if ip in line:
                    cols = line.split()
                    if len(cols) >= 2:
                        mac = cols[1].strip()
                        vendor = _oui_vendor(mac)
                        break
        except Exception:
            pass

        try:
            nb = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"nbtstat -A {ip} 2>$null | Select-String '<00>'"],
                capture_output=True, text=True, timeout=3
            ).stdout.strip()
            for line in nb.split("\n"):
                if "<00>" in line and "UNIQUE" in line:
                    name = line.strip().split()[0]
                    if name and name != ip:
                        hostname = name
                        break
        except Exception:
            pass

        try:
            dns = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Resolve-DnsName -Name {ip} -Type PTR -ErrorAction SilentlyContinue | Select -ExpandProperty NameHost"],
                capture_output=True, text=True, timeout=3
            ).stdout.strip()
            if dns and "." in dns and not hostname:
                hostname = dns
        except Exception:
            pass

        port_timeout = "300" if fast else "1500"
        common_ports = [(445, "SMB"), (139, "NetBIOS"), (80, "HTTP"), (443, "HTTPS"),
                        (3389, "RDP"), (22, "SSH"), (21, "FTP"), (23, "Telnet"),
                        (8080, "HTTP-Alt"), (8443, "HTTPS-Alt"),
                        (5985, "WinRM"), (5900, "VNC"), (554, "RTSP")]
        scan_ports = common_ports if fast else common_ports + [
            (25, "SMTP"), (53, "DNS"), (110, "POP3"), (143, "IMAP"),
            (993, "IMAPS"), (995, "POP3S"), (587, "SMTPS"),
            (3306, "MySQL"), (5432, "PostgreSQL"), (6379, "Redis"),
            (27017, "MongoDB"), (5986, "WinRM-HTTPS"), (8554, "RTSP-Alt")]
        for port, svc in scan_ports:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Test-NetConnection -ComputerName {ip} -Port {port} -WarningAction SilentlyClose -InformationLevel Quiet | Select -First 1"],
                    capture_output=True, text=True, timeout=int(port_timeout)//1000+1
                ).stdout.strip()
                if "True" in r:
                    ports.append({"port": port, "service": svc, "state": "open"})
            except Exception:
                pass

        os_guess = self._fingerprint_os(ip)

        if not fast:
            try:
                ts = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "tailscale status 2>$null | Select-String '100\\.'"],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip()
                for line in ts.split("\n"):
                    if ip in line or hostname.split(".")[0] in line:
                        parts = line.split()
                        for p in parts:
                            if p.startswith("100."):
                                ts_ip = p
                                break
            except Exception:
                pass

        device = {
            "ip": ip, "mac": mac, "vendor": vendor, "hostname": hostname,
            "ports": ports, "os_guess": os_guess, "tailscale_ip": ts_ip,
            "smb_access": int(any(p["port"] in (139, 445) for p in ports)),
            "rdp_open": int(any(p["port"] == 3389 for p in ports)),
        }

        self.db.upsert_device(ip, **device)
        return device

    # ── Urban Scanner — background surveillance ─────────────────────────────────

    def start_urban_scanner(self):
        if self._urban_running:
            return
        self._urban_running = True
        t = threading.Thread(target=self._urban_loop, daemon=True)
        t.start()

    def _urban_loop(self):
        last_wifi_check = 0
        last_camera_check = 0

        while self._urban_running:
            now = time.time()
            try:
                # WiFi sweep every 60s
                if now - last_wifi_check > 60:
                    self._scan_wifi()
                    last_wifi_check = now

                # Camera scan every 120s
                if now - last_camera_check > 120:
                    self._scan_cameras()
                    last_camera_check = now

                # Proximity check every 30s
                self._check_proximity()
            except Exception:
                pass
            time.sleep(15)

    def _scan_wifi(self):
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "netsh wlan show networks mode=Bssid 2>$null | Out-String"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if not r:
                return
            lines = r.split("\n")
            current_ssid = ""
            ap_count = 0
            for line in lines:
                line = line.strip()
                if line.startswith("SSID"):
                    m = re.search(r'SSID\s*:\s*(.+)', line)
                    if m:
                        current_ssid = m.group(1).strip()
                        ap_count += 1
                if "Signal" in line and current_ssid:
                    sig = re.search(r'(\d+)%', line)
                    pct = int(sig.group(1)) if sig else 0
                    self.db.add_urban_event(
                        "wifi_ap", f"WiFi: {current_ssid} ({pct}%)",
                        {"ssid": current_ssid, "signal": pct}, "wifi_scanner"
                    )
                    current_ssid = ""
            self.db.journal_entry("wifi_scan", {"aps_found": ap_count}, "urban_scanner", 1)
        except Exception:
            pass

    def _scan_cameras(self):
        """Scan for RTSP/HTTP cameras on the LAN."""
        try:
            arp = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "arp -a | Select-String 'dynamic' | ForEach-Object { ($_.Trim() -split '\\s+')[0] }"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            ips = [l.strip() for l in arp.split() if l.strip().count(".") == 3]
            for ip in ips[:30]:
                for port, name in [(554, "RTSP"), (80, "HTTP"), (8080, "HTTP-Alt"), (8554, "RTSP-Alt")]:
                    try:
                        r = subprocess.run(
                            ["powershell", "-NoProfile", "-Command",
                             f"Test-NetConnection -ComputerName {ip} -Port {port} -WarningAction SilentlyClose | Select -ExpandProperty TcpTestSucceeded"],
                            capture_output=True, text=True, timeout=2
                        ).stdout.strip()
                        if "True" in r:
                            vendor = ""
                            try:
                                arp2 = subprocess.run(
                                    ["powershell", "-NoProfile", "-Command", f"arp -a | Select-String '{ip}'"],
                                    capture_output=True, text=True, timeout=2
                                ).stdout.strip()
                                for line in arp2.split("\n"):
                                    if ip in line:
                                        cols = line.split()
                                        if len(cols) >= 2:
                                            vendor = _oui_vendor(cols[1].strip())
                                            break
                            except Exception:
                                pass
                            self.db.add_urban_event(
                                "camera", f"Camera: {ip}:{port} ({name}) [{vendor}]",
                                {"ip": ip, "port": port, "service": name, "vendor": vendor}, "camera_scanner"
                            )
                            self.db.upsert_device(ip, ports=[{"port": port, "service": name, "state": "open"}])
                    except Exception:
                        pass
        except Exception:
            pass

    def _check_proximity(self):
        """Detect known devices appearing/disappearing from ARP."""
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "arp -a | Select-String 'dynamic' | ForEach-Object { ($_.Trim() -split '\\s+')[0,1] -join '|' }"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            current: dict[str, str] = {}
            for line in out.split():
                parts = line.split("|")
                if len(parts) >= 2:
                    ip = parts[0].strip()
                    mac = parts[1].strip()
                    if ip.count(".") == 3 and mac.count("-") == 5:
                        current[mac] = ip

            for mac, ip in current.items():
                if mac not in self._known_macs:
                    vendor = _oui_vendor(mac)
                    dtype = _device_type(vendor, "", [])
                    self.db.add_urban_event(
                        "proximity", f"New device: {ip} ({vendor}) — {dtype}",
                        {"ip": ip, "mac": mac, "vendor": vendor, "type": dtype}, "proximity_watch"
                    )
                    self.db.upsert_device(ip, mac=mac, vendor=vendor)

            for mac in list(self._known_macs.keys()):
                if mac not in current:
                    ip = self._known_macs[mac]
                    self.db.add_urban_event(
                        "proximity", f"Device left: {ip}",
                        {"ip": ip, "mac": mac}, "proximity_watch"
                    )

            self._known_macs = current
        except Exception:
            pass

    def stop_urban_scanner(self):
        self._urban_running = False


def _run_bg_scan(engine):
    try:
        devices = engine._quick_scan()
        engine._scan_count = len(devices)
        if not devices and engine.db:
            engine._scan_count = len(engine.db.all_devices())
    except Exception:
        engine._scan_count = len(engine.db.all_devices()) if engine.db else 0
    finally:
        engine._scan_in_progress = False
        engine._scan_done = True
