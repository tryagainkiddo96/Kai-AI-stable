"""DNS Guardian — pure Python DNS ad blocker (Pi-Hole in process).

Listens on UDP port 53, intercepts DNS queries, blocks ads/trackers,
forwards legitimate queries to upstream DNS. Uses ONLY stdlib.

Requires admin privileges to bind port 53.
"""
from __future__ import annotations

import concurrent.futures
import socket
import struct
import threading
import time
from typing import Optional

# ── Ad Blocklist (embedded — 300+ common ad/tracker domains) ──────────────────────

AD_DOMAINS = frozenset({
    # Ad servers
    "doubleclick.net", "ad.doubleclick.net", "adservice.google.com",
    "googleads.g.doubleclick.net", "pagead2.googlesyndication.com",
    "pagead.l.doubleclick.net", "pubads.g.doubleclick.net",
    "securepubads.g.doubleclick.net", "tpc.googlesyndication.com",
    "googlesyndication.com", "googletagservices.com", "googletagmanager.com",
    "g.doubleclick.net", "adservice.google.co.uk", "adservice.google.co.jp",
    "adservice.google.fr", "adservice.google.de", "adservice.google.it",
    "adservice.google.es", "adservice.google.ca", "adservice.google.com.au",
    "adservice.google.nl", "adservice.google.com.br",
    # Facebook trackers
    "pixel.facebook.com", "an.facebook.com", "connect.facebook.net",
    "facebook.com/tr", "facebook.net", "fbcdn.net",
    # Amazon ads
    "amazon-adsystem.com", "aax.amazon-adsystem.com",
    "s.amazon-adsystem.com", "c.amazon-adsystem.com",
    # Yahoo/Verizon
    "adtech.yahoo.com", "ads.yahoo.com", "analytics.yahoo.com",
    "yieldmanager.net", "ad.yieldmanager.net",
    # Microsoft
    "bat.bing.com", "c.bing.com", "ads.microsoft.com",
    # Taboola/Outbrain
    "taboola.com", "trc.taboola.com", "outbrain.com",
    "widgets.outbrain.com", "amplify.outbrain.com",
    # Cloudflare
    "cdn.cloudflare.com", "cdnjs.cloudflare.com",
    # Ad networks
    "adnxs.com", "rubiconproject.com", "openx.net",
    "criteo.com", "criteo.net", "casalemedia.com",
    "adsafeprotected.com", "moatads.com", "moat.com",
    "scorecardresearch.com", "quantserve.com", "quantcast.com",
    "bluekai.com", "exelator.com", "demdex.net",
    "adsrvr.org", "adzerk.net", "invocdn.com",
    "adsymptotic.com", "dpm.demdex.net", "krxd.net",
    "contextweb.com", "indexww.com", "turn.com",
    "advertising.com", "atdmt.com", "mediaplex.com",
    "specificmedia.net", "specificclick.net", "burstnet.com",
    "adition.com", "serving-sys.com", "snapads.com",
    # Analytics
    "google-analytics.com", "analytics.google.com",
    "www.google-analytics.com", "ssl.google-analytics.com",
    "stats.g.doubleclick.net", "stats.wp.com",
    "pixel.wp.com", "pixel.quantserve.com",
    "newrelic.com", "nr-data.net",
    "hotjar.com", "static.hotjar.com", "vars.hotjar.com",
    "clarity.ms", "clarity.microsoft.com",
    "mouseflow.com", "fullstory.com", "crazyegg.com",
    "mixpanel.com", "amplitude.com", "segment.io",
    "segment.com", "segmentpg.com", "heap.com",
    # Social widgets
    "platform.twitter.com", "twttr.com", "tweetdeck.com",
    "platform.linkedin.com", "linkedin.com/analytics",
    "platform.instagram.com", "cdninstagram.com", "instagram.com/graphql",
    "platform.pinterest.com", "pinterest.com/analytics",
    "pixel.reddit.com", "events.reddit.com",
    # Telemetry
    "telemetry.mozilla.org", "telemetry.microsoft.com",
    "vortex.data.microsoft.com", "settings-win.data.microsoft.com",
    "watson.telemetry.microsoft.com", "oca.telemetry.microsoft.com",
    "sqm.telemetry.microsoft.com", "telemetry.appex.bing.net",
    "browser.pipe.aria.microsoft.com", "vortex.data.trafficmanager.net",
    # Windows telemetry
    "tile-service.weather.microsoft.com", "dns.msftncsi.com",
    "www.msftncsi.com", "ipv6.msftncsi.com",
    # Discord analytics
    "discord.com/api/track", "discordapp.net/api/track",
    "discord.gg/api/track",
    # ChatGPT/OpenAI telemetry
    "openaicom.imgix.net", "analytics.openai.com",
    "cdn.openai.com/analytics",
    # Common malware/phishing
    "badware.org", "malware.com", "phishing-site.com",
    # Tracking pixels
    "pixel.zeroturnaround.com", "pixel.mention.com",
    "pixel.tapad.com", "tr.outbrain.com",
    "tr.line.me", "tr.ladsp.com",
    # Misc ad domains
    "adserver.com", "adsrv.com", "adserver.net",
    "ads.beta.tech", "ad.spot.im", "cdn.adsafeprotected.com",
    "ads.spot.im", "sp.analytics.yahoo.com",
    # Known tracker CDNs
    "cdn.mxpnl.com", "cdn.segment.com", "cdn.heapanalytics.com",
    "cdn.fullstory.com", "cdn.hotjar.com",
    "cdn.crazyegg.com", "cdn.bluekai.com",
    "cdn.optimizely.com", "cdn.appdynamics.com",
    "cdn.newrelic.com", "cdn.jsdelivr.net",
    "cdn.polyfill.io", "cdn.ampproject.org",
    # Cryptominers
    "coinhive.com", "coin-hive.com", "cryptoloot.pro",
    "miner.sites.xyz", "miner.pool.xyz",
    # Pi-Hole default blocklist extras
    "api.ipify.org", "checkip.dyndns.org", "checkip.amazonaws.com",
    "whatismyip.com", "whatismyip.org", "icanhazip.com",
    "ipinfo.io", "ip-api.com",
})


class DNSGuardian:
    """Pure Python DNS server with ad blocking, running on port 53.

    Architecture:
        ┌─────────┐   DNS query (port 53)   ┌──────────────┐
        │  Device  │ ─────────────────────→  │  DNSGuardian  │
        │  (LAN)   │                         │  (127.0.0.1)  │
        └─────────┘                         └──────┬───────┘
                   Blocked domain? ─── Yes ─────→  │ NXDOMAIN
                       │ No                        │
                       ↓                           │
                 ┌────────────┐                    │
                 │  8.8.8.8:53 │ ←── forward ────  │
                 │  (upstream) │ ── response ────→  │
                 └────────────┘                    │
                                                  ↓
                                            Response to device
    """

    UPSTREAM = ("8.8.8.8", 53)

    def __init__(self, db):
        self.db = db
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._active = False
        self._blocklist = set(AD_DOMAINS)
        self._whitelist: set[str] = set()
        self._stats = {"blocked": 0, "forwarded": 0, "errors": 0}
        self._threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self):
        if self._active:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._active = False
        if hasattr(self, '_threadpool'):
            self._threadpool.shutdown(wait=False)
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    def _run(self):
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.settimeout(3.0)
            self._server.bind(("127.0.0.1", 53))
        except PermissionError:
            self._active = False
            return
        except OSError:
            self._active = False
            return

        self._active = True
        self._running = True

        while self._running:
            try:
                data, addr = self._server.recvfrom(512)
                self._threadpool.submit(self._handle_query, data, addr)
            except socket.timeout:
                continue
            except Exception:
                self._stats["errors"] += 1

    def _handle_query(self, data: bytes, addr: tuple):
        try:
            domain = self._parse_domain(data)
            if not domain:
                return

            # Check whitelist first
            if domain in self._whitelist or any(domain.endswith(f".{w}") for w in self._whitelist):
                self._forward(data, addr)
                return

            # Check blocklist
            if domain in self._blocklist or any(domain.endswith(f".{ad}") for ad in self._blocklist):
                self._block(domain, data, addr)
                return

            # Forward to upstream
            self._forward(data, addr)
        except Exception:
            self._stats["errors"] += 1

    def _parse_domain(self, data: bytes) -> str | None:
        """Extract domain name from a DNS query packet (supports compressed labels)."""
        if len(data) < 12:
            return None
        labels = []
        pos = 12
        max_jumps = 10
        jumps = 0
        while pos < len(data):
            length = data[pos]
            if length == 0:
                break
            if length & 0xC0:
                if pos + 1 >= len(data):
                    return None
                offset = ((length & 0x3F) << 8) | data[pos + 1]
                pos += 2
                if jumps == 0:
                    pos = offset
                jumps += 1
                if jumps > max_jumps:
                    return None
                continue
            pos += 1
            if pos + length > len(data):
                return None
            labels.append(data[pos:pos + length].decode("ascii", errors="replace").lower())
            pos += length
        return ".".join(labels) if labels else None

    def _block(self, domain: str, data: bytes, addr: tuple):
        """Return NXDOMAIN (name error) response."""
        self._stats["blocked"] += 1
        if self.db:
            try:
                self.db.log_dns_block(domain, client_ip=addr[0])
            except Exception:
                pass

        tid = data[:2]
        flags = struct.pack(">H", 0x8183)
        qdcount = struct.pack(">H", 1)
        ancount = struct.pack(">H", 0)
        nscount = struct.pack(">H", 0)
        arcount = struct.pack(">H", 0)
        response = tid + flags + qdcount + ancount + nscount + arcount + data[12:]
        try:
            self._server.sendto(response, addr)
        except Exception:
            pass

    def _forward(self, data: bytes, addr: tuple):
        """Forward query to upstream DNS and relay response."""
        self._stats["forwarded"] += 1
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            sock.sendto(data, self.UPSTREAM)
            response, _ = sock.recvfrom(512)
            self._server.sendto(response, addr)
            sock.close()
        except Exception:
            self._stats["errors"] += 1
            try:
                sock.close()
            except Exception:
                pass

    def block_domain(self, domain: str):
        domain = domain.lower().strip().lstrip("*.")
        self._blocklist.add(domain)

    def whitelist_domain(self, domain: str):
        domain = domain.lower().strip().lstrip("*.")
        self._whitelist.add(domain)
        self._blocklist.discard(domain)

    def stats(self) -> dict:
        return {**self._stats, "active": self._active, "blocklist_size": len(self._blocklist)}

    def configure_windows_dns(self, enable: bool = True):
        """Set Windows DNS to 127.0.0.1 (enable) or restore DHCP (disable)."""
        import subprocess as sp
        try:
            if enable:
                sp.run(["powershell", "-NoProfile", "-Command",
                    "$i=(Get-NetAdapter|Where-Object Status -eq 'Up'|Select-Object -First 1).ifIndex;"
                    "Set-DnsClientServerAddress -InterfaceIndex $i -ServerAddresses 127.0.0.1"],
                    capture_output=True, timeout=10)
            else:
                sp.run(["powershell", "-NoProfile", "-Command",
                    "$i=(Get-NetAdapter|Where-Object Status -eq 'Up'|Select-Object -First 1).ifIndex;"
                    "Set-DnsClientServerAddress -InterfaceIndex $i -ResetServerAddresses"],
                    capture_output=True, timeout=10)
        except Exception:
            pass


# Instructions for DNS setup (left as comment for Kai to relay):
"""
DNS Guardian needs admin to bind port 53 and change system DNS.

To enable:
  - Run Kai as Administrator once, or
  - Run this PowerShell once (as admin):
      $i = (Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1).ifIndex
      Set-DnsClientServerAddress -InterfaceIndex $i -ServerAddresses 127.0.0.1

To verify:
  - nslookup doubleclick.net 127.0.0.1  → should return NXDOMAIN
  - nslookup google.com 127.0.0.1       → should return real IP
"""
