"""Conversation Ghosting — pre-fetches intelligence from user messages."""
from __future__ import annotations

import ipaddress
import re
import subprocess
import time


class GhostContext:
    """Scans user messages for IPs, domains, ports, files and pre-fetches context."""

    def __init__(self, db):
        self.db = db
        self._cache = {}

    def analyze_message(self, text: str) -> dict:
        """Scan message and return pre-fetched intelligence block."""
        findings = []

        ips = re.findall(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', text)
        for ip in ips[:3]:
            if ip in ("127.0.0.1", "0.0.0.0"):
                continue
            info = self._check_ip(ip)
            if info:
                findings.append(info)

        domains = re.findall(r'\b([a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', text)
        for domain in domains[:3]:
            domain = domain.lower()
            if domain in ("localhost",):
                continue
            info = self._check_domain(domain)
            if info:
                findings.append(info)

        ports = re.findall(r'port\s+(\d{2,5})|:(\d{2,5})\b', text)
        for match in ports[:5]:
            port = match[0] or match[1]
            info = self._check_port(int(port))
            if info:
                findings.append(info)

        files = re.findall(r'([\w.-]+\.(py|js|ts|exe|dll|conf|json|txt|bat|ps1|sh|cfg|log))', text, re.I)
        for fname, _ in files[:3]:
            info = self._check_file(fname)
            if info:
                findings.append(info)

        if findings:
            lines = ["[Pre-fetched Intelligence]"]
            for f in findings:
                lines.append(f)
            return {"context": "\n".join(lines), "findings": findings}
        return {"context": "", "findings": []}

    def _check_ip(self, ip: str) -> str:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return ""
        now = time.time()
        if ip in self._cache and now - self._cache[ip]["time"] < 60:
            return self._cache[ip]["text"]
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                f"Test-Connection -Count 1 -ComputerName {ip} -Quiet"],
                               capture_output=True, text=True, timeout=3)
            alive = "alive" if r.stdout.strip() == "True" else "no response"
            result = f"  IP {ip}: {alive}"
            self._cache[ip] = {"text": result, "time": now}
            return result
        except Exception:
            return ""

    def _check_domain(self, domain: str) -> str:
        now = time.time()
        if domain in self._cache and now - self._cache[domain]["time"] < 120:
            return self._cache[domain]["text"]
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                f"Resolve-DnsName {domain} -Type A -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty IPAddress"],
                               capture_output=True, text=True, timeout=5)
            ip = r.stdout.strip()
            result = f"  Domain {domain}: resolves to {ip}" if ip else f"  Domain {domain}: no A record"
            self._cache[domain] = {"text": result, "time": now}
            return result
        except Exception:
            return ""

    def _check_port(self, port: int) -> str:
        try:
            common = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
                      80: "HTTP", 443: "HTTPS", 445: "SMB", 3389: "RDP", 8080: "HTTP-alt",
                      3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis"}
            svc = common.get(port, "unknown")
            return f"  Port {port}: {svc}"
        except Exception:
            return ""

    def _check_file(self, filename: str) -> str:
        from pathlib import Path
        p = Path(filename)
        if p.exists():
            sz = p.stat().st_size
            return f"  File {filename}: exists ({sz:,} bytes)"
        return ""
