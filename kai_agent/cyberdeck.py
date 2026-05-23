"""Cyberdeck — Quickhack execution engine for Kai."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

WORKSPACE: Path | None = None


_NMAP_PATH: str = ""

def _find_nmap() -> str:
    for p in [r"C:\Program Files (x86)\Nmap\nmap.exe", r"C:\Program Files\Nmap\nmap.exe"]:
        if Path(p).exists():
            return p
    try:
        subprocess.run(["nmap", "--version"], capture_output=True, timeout=5)
        return "nmap"
    except: pass
    return ""

def _cmd(cmd: list[str], timeout: int = 60, **kwargs) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
        out = (r.stdout or "") + (r.stderr or "")
        return out.strip() or f"[exit {r.returncode}]"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except FileNotFoundError:
        return "[TOOL NOT FOUND]"
    except Exception as e:
        return f"[ERROR: {e}]"


def _wsl(cmd: str, timeout: int = 120) -> str:
    try:
        r = subprocess.run(
            ["wsl", "-d", "kali-linux", "--", "bash", "-lc", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return out.strip() or f"[exit {r.returncode}]"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


def _ps(script: str, timeout: int = 60) -> str:
    return _cmd(["powershell", "-NoProfile", "-Command", script], timeout=timeout)


def _wsl_python(script: str, timeout: int = 120) -> str:
    return _wsl(f"python3 -c {shlex.quote(script)}", timeout=timeout)


def _detect_target(text: str) -> tuple[str, str]:
    ip_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")
    domain_re = re.compile(r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")
    email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    url_re = re.compile(r"https?://[^\s]+")

    ips = ip_re.findall(text)
    if ips:
        return "ip", ips[0]
    urls = url_re.findall(text)
    if urls:
        return "url", urls[0]
    emails = email_re.findall(text)
    if emails:
        return "email", emails[0]
    domains = domain_re.findall(text)
    if domains:
        return "domain", domains[0]
    return "raw", text.strip().split()[-1] if text.strip() else ""


# ── Quickhack implementations ────────────────────────────────────────────

def _ping(target: str) -> str:
    kind, val = _detect_target(target)
    nmap = _NMAP_PATH or "nmap"
    if kind == "ip" and "/" in val:
        return _cmd([nmap, "-sn", val], timeout=120)
    return _cmd([nmap, "-sn", val], timeout=60)


def _port_knock(target: str) -> str:
    kind, val = _detect_target(target)
    if kind == "url":
        from urllib.parse import urlparse
        val = urlparse(val).hostname or val
    return _wsl(f"nmap -sV -T4 {shlex.quote(val)} 2>/dev/null", timeout=180)


def _mass_vuln_scan(target: str) -> str:
    kind, val = _detect_target(target)
    if kind == "url":
        val = val.split("//")[-1].split("/")[0]
    return _wsl(f"nuclei -u https://{shlex.quote(val)} -silent -jsonl 2>/dev/null | tail -30", timeout=300)


def _directory_bruteforce(target: str) -> str:
    kind, val = _detect_target(target)
    if kind == "url":
        return _wsl(f"gobuster dir -u {shlex.quote(val)} -w /usr/share/wordlists/dirb/common.txt -q -t 20 -n 2>/dev/null | tail -30", timeout=180)
    return _wsl(f"gobuster dir -u https://{shlex.quote(val)} -w /usr/share/wordlists/dirb/common.txt -q -t 20 -n 2>/dev/null | tail -30", timeout=180)


def _nikto_scan(target: str) -> str:
    kind, val = _detect_target(target)
    if kind == "url":
        return _wsl(f"nikto -h {shlex.quote(val)} -Tuning 123 -output /dev/stdout 2>/dev/null | tail -30", timeout=300)
    return _wsl(f"nikto -h https://{shlex.quote(val)} -Tuning 123 -output /dev/stdout 2>/dev/null | tail -30", timeout=300)


def _sql_injection(target: str) -> str:
    kind, val = _detect_target(target)
    return _cmd(["python", "-m", "sqlmap", "-u", val, "--batch", "--level", "2", "--risk", "2"], timeout=300)


def _camera_check(target: str = "") -> str:
    return _cmd(["python", "-c", """
import json, requests
try:
    r = requests.get("https://www.shodan.io/search/facet?query=port:554+has_screenshot:true&facet=ip", timeout=10)
    print("Shodan camera search requires API key. Try: shodan search port:554")
except: print("Shodan search requires API key: pip install shodan && shodan init YOUR_API_KEY")
"""], timeout=15)


def _person_scan(target: str) -> str:
    kind, val = _detect_target(target)
    results = []
    if kind == "email":
        results.append(_ps(f"curl -s \"https://haveibeenpwned.com/unifiedsearch/{val}\" 2>$null | Select-Object -First 1"))
        domain = val.split("@")[-1]
        results.append(f"[theHarvester via WSL] {_wsl('theHarvester -d ' + domain + ' -b all 2>/dev/null', timeout=120)}")
    else:
        results.append(_wsl(f"theHarvester -d {shlex.quote(val)} -b all 2>/dev/null", timeout=120))
    return "\n---\n".join(r for r in results if r)


def _hydra_bruteforce(target: str) -> str:
    kind, val = _detect_target(target)
    return _wsl(f"hydra -l admin -P /usr/share/wordlists/rockyou.txt.gz {shlex.quote(val)} ssh 2>/dev/null | tail -20", timeout=180)


def _responder_poison(iface: str = "eth0") -> str:
    return _wsl(f"timeout 15 sudo responder -I {shlex.quote(iface)} -w -r -d 2>&1 || echo 'Responder needs root. Run manually: sudo responder -I {iface}'", timeout=30)


def _dns_recon(target: str) -> str:
    kind, val = _detect_target(target)
    results = []
    results.append(f"[nslookup] {_cmd(['nslookup', val], timeout=10)}")
    if kind != "ip":
        results.append(_wsl(f"dnsrecon -d {shlex.quote(val)} -t std 2>/dev/null", timeout=120))
    return "\n---\n".join(r for r in results)


def _cloud_bucket_scan(target: str) -> str:
    kind, val = _detect_target(target)
    results = []
    for service in ["s3", "s3-us-east-1", "s3-eu-west-1"]:
        r = _cmd(["python", "-c", f"""
import requests
url='https://{val}.{service}.amazonaws.com'
try:
    r=requests.get(url, timeout=5)
    if r.status_code < 400: print(f'OPEN: {{url}}')
    elif r.status_code==403: print(f'EXISTS (403): {{url}}')
    else: print(f'{{url}}: HTTP {{r.status_code}}')
except: pass
"""], timeout=10)
        if r and "OPEN" in r:
            results.append(r)
    return "\n".join(results) or f"No open S3 buckets found for '{val}'"


def _whois_lookup(target: str) -> str:
    kind, val = _detect_target(target)
    r = _wsl(f"whois {shlex.quote(val)} 2>/dev/null | head -40", timeout=30)
    return r if r and "ERROR" not in r else f"WHOIS lookup returned no data for {val}"


def _ssl_scan(target: str) -> str:
    kind, val = _detect_target(target)
    if kind == "url":
        from urllib.parse import urlparse
        val = urlparse(val).hostname or val
    return _wsl(f"testssl --quiet {shlex.quote(val)} 2>/dev/null | tail -25", timeout=180)


def _wifi_scan(target: str = "") -> str:
    return _ps("Get-NetAdapter -Name '*wi*','*wl*','*802.11*' -ErrorAction SilentlyContinue | Select-Object Name,InterfaceDescription,Status")


def _certificate_transparency(target: str) -> str:
    return _cmd(["python", "-c", f"""
import json, requests
try:
    r = requests.get('https://crt.sh/?q=%25.{target}&output=json', timeout=15)
    data = r.json()
    names = set()
    for e in data[:50]:
        n = e.get('name_value','')
        if n: names.add(n)
    for n in sorted(names)[:30]: print(n)
except: print('Error fetching crt.sh')
"""], timeout=20)


def _ssh_key_test(target: str) -> str:
    kind, val = _detect_target(target)
    return _cmd(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", val, "echo", "SSH_OK"], timeout=15)


def _web_header_scan(target: str) -> str:
    return _cmd(["python", "-c", f"""
import requests
try:
    r = requests.get('{target}', timeout=10, verify=False)
    for k,v in sorted(r.headers.items()): print(f'{{k}}: {{v}}')
except Exception as e: print(f'Error: {{e}}')
"""], timeout=15)


def _shodan_search(target: str) -> str:
    return _cmd(["python", "-c", f"""
try:
    import shodan
    api = shodan.Shodan('')
    result = api.search('{target}')
    for s in result['matches'][:5]:
        print(f'{{s[\"ip_str\"]}}:{{s[\"port\"]}} - {{s.get(\"org\",\"\")}}')
    if not result['matches']: print('No results - set SHODAN_API_KEY env var')
except ImportError: print('shodan not installed')
except Exception as e: print(f'Shodan: {{e}}')
"""], timeout=15)


# ── Registry ─────────────────────────────────────────────────────────────

class Cyberdeck:
    def __init__(self, workspace: Path | None = None):
        global WORKSPACE, _NMAP_PATH
        WORKSPACE = workspace
        _NMAP_PATH = _find_nmap()
        self.registry: dict[str, Callable] = {
            "ping": (_ping, "Network discovery via nmap ping sweep"),
            "port_knock": (_port_knock, "Port scan + service version detection"),
            "mass_vuln_scan": (_mass_vuln_scan, "Auto vulnerability scan with Nuclei"),
            "directory_bruteforce": (_directory_bruteforce, "Directory/file brute-force with Gobuster"),
            "nikto_scan": (_nikto_scan, "Web server vulnerability scan with Nikto"),
            "sql_injection": (_sql_injection, "Automated SQL injection with sqlmap"),
            "camera_check": (_camera_check, "Find open RTSP cameras via Shodan"),
            "person_scan": (_person_scan, "OSINT profile building via theHarvester + HaveIBeenPwned"),
            "hydra_bruteforce": (_hydra_bruteforce, "Password brute-force with Hydra"),
            "dns_recon": (_dns_recon, "DNS enumeration with nslookup + dnsrecon"),
            "cloud_bucket_scan": (_cloud_bucket_scan, "Scan for open AWS S3 buckets"),
            "whois_lookup": (_whois_lookup, "Domain WHOIS information lookup"),
            "ssl_scan": (_ssl_scan, "SSL/TLS security scan"),
            "wifi_scan": (_wifi_scan, "Scan for WiFi adapters and networks"),
            "certificate_transparency": (_certificate_transparency, "Certificate Transparency log enumeration"),
            "ssh_key_test": (_ssh_key_test, "Test SSH connectivity to target"),
            "web_header_scan": (_web_header_scan, "Grab HTTP response headers"),
            "responder_poison": (_responder_poison, "Poison LLMNR/NBT-NS on network"),
            "shodan_search": (_shodan_search, "Search Shodan for exposed devices"),
        }

    def execute(self, quickhack: str, target: str = "") -> str:
        entry = self.registry.get(quickhack)
        if not entry:
            similar = [k for k in self.registry if k.startswith(quickhack[:3])]
            if similar:
                return f"Unknown quickhack '{quickhack}'. Did you mean: {', '.join(similar[:5])}?"
            return f"Unknown quickhack '{quickhack}'. Available: {', '.join(sorted(self.registry.keys()))}"

        fn, desc = entry
        start = time.time()
        try:
            result = fn(target)
        except Exception as e:
            result = f"[ERROR: {e}]"
        elapsed = time.time() - start
        return f"[{quickhack}] ({elapsed:.1f}s)\n{desc}\n\n{result}"

    def list_quickhacks(self) -> str:
        lines = ["Available quickhacks:"]
        for name in sorted(self.registry):
            _, desc = self.registry[name]
            lines.append(f"  {name}: {desc}")
        return "\n".join(lines)
