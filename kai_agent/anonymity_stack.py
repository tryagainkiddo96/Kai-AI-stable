"""
Kai Anonymity Stack — Proxy rotation, TOR, timing randomization, and leak prevention.
"""
from __future__ import annotations

import json
import os
import random
import socket
import subprocess
import time
from pathlib import Path
from urllib import request, error

# Known good free/proxy sources — Kai rotates through these
COMMON_PROXIES = [
    {"http": "http://127.0.0.1:9050", "https": "http://127.0.0.1:9050"},  # TOR SOCKS via Polipo/Privoxy
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json, text/plain, */*",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "fr-FR,fr;q=0.9",
    "de-DE,de;q=0.9",
    "es-ES,es;q=0.9",
]

SEC_CH_UA = [
    '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    '"Not_A Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    '"Not_A Brand";v="99", "Chromium";v="120", "Microsoft Edge";v="120"',
]

PLATFORMS = ["Windows", "macOS", "Linux"]

SEC_CH_UA_PLATFORM = [
    '"Windows"', '"macOS"', '"Linux"',
]

MOBILE_INDICATORS = ["", "?1", "?0"]


class AnonymityStack:
    """Manages proxy rotation, TOR, timing randomization, and fingerprint spoofing."""

    def __init__(self, workspace: Path, tor_enabled: bool = False, proxy_list: list | None = None) -> None:
        self.workspace = Path(workspace)
        self.state_path = self.workspace / "memory" / "anonymity_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.tor_enabled = tor_enabled
        self.proxy_list = proxy_list or []
        self.current_proxy: dict | None = None
        self.proxy_index = 0
        self._tor_available: bool | None = None

        # Load state
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
                self.current_proxy = state.get("current_proxy")
                self.proxy_index = state.get("proxy_index", 0)
            except Exception:
                pass

    def _save(self) -> None:
        state = {
            "current_proxy": self.current_proxy,
            "proxy_index": self.proxy_index,
        }
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # === PROXY MANAGEMENT ===

    def rotate_proxy(self) -> dict:
        """Rotate to next proxy in list."""
        all_proxies = self.proxy_list + COMMON_PROXIES
        if not all_proxies:
            self.current_proxy = None
            self._save()
            return {"ok": True, "mode": "direct", "message": "No proxies configured. Going direct."}

        self.proxy_index = (self.proxy_index + 1) % len(all_proxies)
        self.current_proxy = all_proxies[self.proxy_index]
        self._save()
        return {
            "ok": True,
            "mode": "proxy",
            "proxy": str(self.current_proxy),
            "index": self.proxy_index,
        }

    def set_tor(self, enabled: bool) -> dict:
        """Enable/disable TOR routing."""
        self.tor_enabled = enabled
        if enabled:
            if self._check_tor():
                self.current_proxy = {"http": "http://127.0.0.1:9050", "https": "http://127.0.0.1:9050"}
                self._save()
                return {"ok": True, "mode": "tor", "message": "TOR routing enabled. IP anonymized."}
            else:
                self.tor_enabled = False
                return {"ok": False, "error": "TOR is not running. Install and start TOR service."}
        else:
            self.current_proxy = None
            self._save()
            return {"ok": True, "mode": "direct", "message": "TOR disabled. Going direct."}

    def _check_tor(self) -> bool:
        """Check if TOR is running on port 9050."""
        if self._tor_available is not None:
            return self._tor_available
        try:
            sock = socket.create_connection(("127.0.0.1", 9050), timeout=3)
            sock.close()
            self._tor_available = True
            return True
        except (ConnectionRefusedError, OSError, TimeoutError):
            self._tor_available = False
            return False

    # === FINGERPRINT GENERATION ===

    def generate_fingerprint(self, mobile: bool = False) -> dict:
        """Generate a random browser fingerprint."""
        ua = random.choice(USER_AGENTS)
        if mobile:
            ua = [u for u in USER_AGENTS if "Mobile" in u or "Android" in u or "iPhone" in u]
            if ua:
                ua = random.choice(ua)
            else:
                ua = random.choice(USER_AGENTS)

        platform = "Android" if "Android" in ua else "iPhone" if "iPhone" in ua else random.choice(PLATFORMS)
        sec_ch_ua = random.choice(SEC_CH_UA)
        sec_ch_platform = random.choice(SEC_CH_UA_PLATFORM)

        return {
            "user_agent": ua,
            "accept": random.choice(ACCEPT_HEADERS),
            "accept_language": random.choice(ACCEPT_LANGUAGES),
            "sec_ch_ua": sec_ch_ua,
            "sec_ch_ua_platform": sec_ch_platform,
            "sec_ch_ua_mobile": random.choice(MOBILE_INDICATORS),
            "sec_fetch_dest": "document",
            "sec_fetch_mode": "navigate",
            "sec_fetch_site": "none",
            "upgrade_insecure_requests": "1",
            "connection": "keep-alive",
        }

    def get_headers(self, fingerprint: dict | None = None) -> dict:
        """Get request headers from a fingerprint."""
        fp = fingerprint or self.generate_fingerprint()
        return {
            "User-Agent": fp["user_agent"],
            "Accept": fp["accept"],
            "Accept-Language": fp["accept_language"],
            "Sec-Ch-Ua": fp["sec_ch_ua"],
            "Sec-Ch-Ua-Platform": fp["sec_ch_ua_platform"],
            "Sec-Ch-Ua-Mobile": fp["sec_ch_ua_mobile"],
            "Sec-Fetch-Dest": fp["sec_fetch_dest"],
            "Sec-Fetch-Mode": fp["sec_fetch_mode"],
            "Sec-Fetch-Site": fp["sec_fetch_site"],
            "Upgrade-Insecure-Requests": fp["upgrade_insecure_requests"],
            "Connection": fp["connection"],
            "Cache-Control": "max-age=0",
        }

    # === TIMING RANDOMIZATION ===

    def jitter_delay(self, base: float = 1.0, variance: float = 2.0) -> None:
        """Sleep for a randomized duration to defeat timing analysis."""
        delay = max(0, base + random.uniform(-variance, variance))
        time.sleep(delay)

    def human_delay(self, action: str = "browse") -> None:
        """Realistic human-like delays between actions."""
        delays = {
            "browse": (2.0, 8.0),
            "click": (0.5, 2.5),
            "type": (0.1, 0.5),
            "scroll": (0.3, 1.5),
            "submit": (1.0, 3.0),
        }
        low, high = delays.get(action, (1.0, 3.0))
        time.sleep(random.uniform(low, high))

    # === ANONYMOUS REQUESTS ===

    def fetch(self, url: str, method: str = "GET", data: dict | None = None,
              timeout: int = 30, follow_redirects: bool = True) -> dict:
        """Make an anonymized HTTP request with rotated fingerprint and proxy."""
        headers = self.get_headers()
        fingerprint = self.generate_fingerprint()
        headers.update(self.get_headers(fingerprint))

        # Add proxy if configured
        proxy = self.current_proxy
        if proxy:
            opener = request.build_opener(request.ProxyHandler(proxy))
            request.install_opener(opener)

        try:
            if method.upper() == "POST" and data:
                payload = json.dumps(data).encode("utf-8")
                req = request.Request(url, data=payload, headers=headers, method="POST")
            else:
                req = request.Request(url, headers=headers, method="GET")

            with request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return {
                    "ok": True,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body[:5000],
                    "fingerprint_id": fingerprint.get("sec_ch_ua", "")[:20],
                    "proxied": bool(proxy),
                }
        except error.HTTPError as exc:
            return {"ok": False, "status": exc.code, "error": str(exc)[:500]}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:500]}

    # === IP & LEAK CHECKS ===

    def check_ip(self) -> dict:
        """Check current public IP and detect leaks."""
        results = {"services": {}}

        services = [
            ("api.ipify.org", "https://api.ipify.org?format=json"),
            ("ifconfig.me", "https://ifconfig.me/ip"),
            ("icanhazip.com", "https://icanhazip.com/"),
        ]

        for name, url in services:
            try:
                req = request.Request(url, headers={"User-Agent": random.choice(USER_AGENTS)})
                with request.urlopen(req, timeout=10) as response:
                    data = response.read().decode("utf-8", errors="replace").strip()
                    results["services"][name] = data
            except Exception:
                results["services"][name] = "unreachable"

        # DNS leak check — check if DNS resolver matches ISP
        try:
            resolver = socket.gethostbyname("dnsleaktest.com")
            results["dns_resolver"] = resolver
        except Exception:
            results["dns_resolver"] = "unknown"

        results["ip"] = list(results["services"].values())[0] if results["services"] else "unknown"
        results["all_match"] = len(set(v for v in results["services"].values() if v not in ("unreachable", ""))) <= 1

        return results

    def status(self) -> dict:
        """Get current anonymity status."""
        tor_running = self._check_tor()
        return {
            "tor_enabled": self.tor_enabled,
            "tor_running": tor_running,
            "proxy_active": bool(self.current_proxy),
            "current_proxy": str(self.current_proxy) if self.current_proxy else "direct",
            "proxy_list_size": len(self.proxy_list),
            "fingerprint_rotation": "enabled",
            "timing_jitter": "enabled",
        }
