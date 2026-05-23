"""OWASP ZAP REST API Client — headless web security scanning."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
from pathlib import Path

import requests


ZAP_HOST = "127.0.0.1"
ZAP_PORT = 8080
ZAP_API_KEY = "kaizap2024"
WSL_DISTRO = "kali-linux"


class ZapClient:
    """REST API client for OWASP ZAP daemon."""

    def __init__(self) -> None:
        self._base = f"http://{ZAP_HOST}:{ZAP_PORT}"
        self._api_key = ZAP_API_KEY
        self._session: requests.Session | None = None
        self._daemon_pid: int | None = None

    # ── Daemon Lifecycle ──────────────────────────────────────────────────

    def start_daemon(self, port: int = ZAP_PORT, api_key: str = ZAP_API_KEY) -> str:
        """Launch ZAP in headless daemon mode via WSL Kali."""
        self._api_key = api_key
        cmd = (
            f"zap.sh -daemon -host 127.0.0.1 -port {port} "
            f"-config api.key={api_key} "
            f"-config api.addrs.addr.name=127.0.0.1 "
            f"-config api.addrs.addr.regex=true "
            f"2>/dev/null & echo PID=$!"
        )
        r = subprocess.run(
            ["wsl.exe", "-d", WSL_DISTRO, "--", "bash", "-lc", cmd],
            capture_output=True, text=True, timeout=15
        )
        out = (r.stdout + r.stderr).strip()
        for line in out.split("\n"):
            if line.startswith("PID="):
                try:
                    self._daemon_pid = int(line.split("=", 1)[1])
                except ValueError:
                    pass
        self._base = f"http://127.0.0.1:{port}"
        self._session = requests.Session()
        for _ in range(30):
            if self._ping():
                return f"ZAP daemon started (PID {self._daemon_pid})"
            time.sleep(2)
        return f"ZAP started but not responding yet:\n{out[:300]}"

    def stop_daemon(self) -> str:
        """Shut down the ZAP daemon."""
        try:
            self._get("JSON/core/action/shutdown/")
        except Exception:
            pass
        if self._daemon_pid:
            subprocess.run(
                ["wsl.exe", "-d", WSL_DISTRO, "--", "bash", "-lc",
                 f"kill {self._daemon_pid} 2>/dev/null; pkill -f zap"],
                capture_output=True, timeout=10
            )
        self._daemon_pid = None
        self._session = None
        return "ZAP daemon stopped"

    def is_daemon_running(self) -> bool:
        """Check if ZAP process is alive in WSL."""
        r = subprocess.run(
            ["wsl.exe", "-d", WSL_DISTRO, "--", "bash", "-lc",
             "pgrep -f 'zap' 2>/dev/null | head -3"],
            capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0 and r.stdout.strip() != ""

    def ensure_daemon(self) -> str:
        """Start daemon if not running."""
        if self._ping():
            return "ZAP daemon already running"
        if self.is_daemon_running():
            for _ in range(15):
                if self._ping():
                    return "ZAP daemon reconnected"
                time.sleep(2)
        return self.start_daemon()

    # ── Internal ──────────────────────────────────────────────────────────

    def _ping(self) -> bool:
        """Check if ZAP API is reachable."""
        try:
            r = self._get("JSON/core/view/version/", timeout=5)
            return r.ok
        except Exception:
            return False

    def _get(self, path: str, params: dict | None = None,
             timeout: int = 30) -> requests.Response:
        """GET request with API key."""
        p = dict(params or {})
        if "apikey" not in p:
            p["apikey"] = self._api_key
        sess = self._session or requests.Session()
        url = f"{self._base}/{path}"
        return sess.get(url, params=p, timeout=timeout)

    def _post(self, path: str, params: dict | None = None,
              timeout: int = 60) -> requests.Response:
        """POST request with API key."""
        p = dict(params or {})
        if "apikey" not in p:
            p["apikey"] = self._api_key
        sess = self._session or requests.Session()
        url = f"{self._base}/{path}"
        return sess.post(url, data=p, timeout=timeout)

    def _result(self, resp: requests.Response) -> dict:
        """Parse JSON response."""
        try:
            return resp.json() if resp.text else {}
        except Exception:
            return {"raw": resp.text[:1000]}

    # ── Core ──────────────────────────────────────────────────────────────

    def version(self) -> dict:
        """Get ZAP version."""
        return self._result(self._get("JSON/core/view/version/"))

    def mode(self) -> dict:
        """Get current mode (attack/protect/standard/safe)."""
        return self._result(self._get("JSON/core/view/mode/"))

    def set_mode(self, mode: str = "attack") -> dict:
        """Set ZAP mode: attack, protect, standard, safe."""
        return self._result(self._post("JSON/core/action/setMode/",
                                       {"mode": mode}))

    def exclude_from_proxy(self, regex: str) -> dict:
        """Exclude URLs matching regex from proxying."""
        return self._result(self._post("JSON/core/action/excludeFromProxy/",
                                       {"regex": regex}))

    # ── Spider (Crawler) ──────────────────────────────────────────────────

    def start_spider(self, url: str, max_children: int = 10,
                     recurse: bool = True, subtree_only: bool = False) -> dict:
        """Start spider scan of a URL. Returns scan ID."""
        params = {
            "url": url,
            "maxChildren": str(max_children),
            "recurse": str(recurse).lower(),
            "subtreeOnly": str(subtree_only).lower(),
        }
        resp = self._post("JSON/spider/action/scan/", params, timeout=10)
        data = self._result(resp)
        return data

    def spider_status(self, scan_id: str) -> dict:
        """Check spider scan progress (0-100)."""
        return self._result(
            self._get("JSON/spider/view/status/", {"scanId": scan_id}))

    def spider_results(self, scan_id: str) -> dict:
        """Get URLs found by spider."""
        return self._result(
            self._get("JSON/spider/view/results/", {"scanId": scan_id}))

    def spider_full_results(self, scan_id: str) -> dict:
        """Get full results including URLs not yet visited."""
        return self._result(
            self._get("JSON/spider/view/fullResults/", {"scanId": scan_id}))

    def spider_scan_ids(self) -> dict:
        """List all spider scan IDs."""
        return self._result(self._get("JSON/spider/view/scans/"))

    def stop_spider(self, scan_id: str) -> dict:
        """Stop a spider scan."""
        return self._result(
            self._post("JSON/spider/action/stop/", {"scanId": scan_id}))

    def remove_spider_scan(self, scan_id: str) -> dict:
        """Remove spider scan data."""
        return self._result(
            self._post("JSON/spider/action/removeScan/", {"scanId": scan_id}))

    # ── Active Scanner ────────────────────────────────────────────────────

    def start_active_scan(self, url: str, recurse: bool = True,
                          in_scope_only: bool = False,
                          scan_policy_name: str = "") -> dict:
        """Start active scan against a URL. Returns scan ID."""
        params = {
            "url": url,
            "recurse": str(recurse).lower(),
            "inScopeOnly": str(in_scope_only).lower(),
        }
        if scan_policy_name:
            params["scanPolicyName"] = scan_policy_name
        resp = self._post("JSON/ascanner/action/scan/", params, timeout=10)
        return self._result(resp)

    def active_scan_status(self, scan_id: str) -> dict:
        """Check active scan progress (0-100)."""
        return self._result(
            self._get("JSON/ascanner/view/status/", {"scanId": scan_id}))

    def active_scan_scan_ids(self) -> dict:
        """List all active scan IDs."""
        return self._result(self._get("JSON/ascanner/view/scans/"))

    def stop_active_scan(self, scan_id: str) -> dict:
        """Stop an active scan."""
        return self._result(
            self._post("JSON/ascanner/action/stop/", {"scanId": scan_id}))

    def remove_active_scan(self, scan_id: str) -> dict:
        """Remove active scan data."""
        return self._result(
            self._post("JSON/ascanner/action/removeScan/", {"scanId": scan_id}))

    def pause_active_scan(self, scan_id: str) -> dict:
        """Pause an active scan."""
        return self._result(
            self._post("JSON/ascanner/action/pause/", {"scanId": scan_id}))

    def resume_active_scan(self, scan_id: str) -> dict:
        """Resume a paused active scan."""
        return self._result(
            self._post("JSON/ascanner/action/resume/", {"scanId": scan_id}))

    # ── Alerts ────────────────────────────────────────────────────────────

    def alerts(self, base_url: str = "", risk: str = "",
               min_risk: str = "") -> dict:
        """Get alerts, optionally filtered by risk level.
        risk: 0=informational, 1=low, 2=medium, 3=high
        """
        params = {}
        if base_url:
            params["baseurl"] = base_url
        if risk:
            params["riskId"] = risk
        if min_risk:
            params["minRisk"] = min_risk
        return self._result(self._get("JSON/core/view/alerts/", params))

    def alert_summary(self, base_url: str = "") -> dict:
        """Get summary of alerts by risk level."""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        return self._result(
            self._get("JSON/core/view/alertSummary/", params))

    def number_of_alerts(self, base_url: str = "",
                         risk: str = "") -> dict:
        """Get count of alerts."""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        if risk:
            params["riskId"] = risk
        return self._result(
            self._get("JSON/core/view/numberOfAlerts/", params))

    # ── Sites / Context ──────────────────────────────────────────────────

    def sites(self) -> dict:
        """List sites in the ZAP session."""
        return self._result(self._get("JSON/core/view/sites/"))

    def urls(self) -> dict:
        """List all known URLs."""
        return self._result(self._get("JSON/core/view/urls/"))

    def exclude_from_scan(self, regex: str) -> dict:
        """Exclude URLs matching regex from all scans."""
        return self._result(
            self._post("JSON/core/action/excludeFromScan/",
                       {"regex": regex}))

    # ── Scan Policy ──────────────────────────────────────────────────────

    def scan_policies(self) -> dict:
        """List available scan policies."""
        return self._result(
            self._get("JSON/ascanner/view/scanPolicyNames/"))

    def scan_policy_default(self) -> dict:
        """Get default scan policy."""
        return self._result(
            self._get("JSON/ascanner/view/scanPolicyDefault/"))

    # ── Automated Scan (Spider + Active Scan) ────────────────────────────

    def run_full_scan(self, url: str, max_children: int = 10,
                      recurse: bool = True) -> dict:
        """Run spider + active scan and wait for completion. Returns alerts."""
        mode_resp = self.set_mode("attack")
        spider = self.start_spider(url, max_children=max_children,
                                   recurse=recurse)
        spider_id = spider.get("scan")
        if not spider_id:
            return {"error": "Failed to start spider", "response": spider}
        while True:
            st = self.spider_status(spider_id)
            prog = st.get("status", "0")
            if prog == "100":
                break
            time.sleep(3)
        ascanner = self.start_active_scan(url, recurse=recurse)
        ascanner_id = ascanner.get("scan")
        if not ascanner_id:
            return {"error": "Failed to start active scan",
                    "response": ascanner, "spider_complete": True}
        while True:
            st = self.active_scan_status(ascanner_id)
            prog = st.get("status", "0")
            if prog == "100":
                break
            time.sleep(5)
        return self.alerts(base_url=url)

    # ── Reporting ─────────────────────────────────────────────────────────

    def generate_html_report(self) -> str:
        """Generate an HTML report (returns raw HTML string)."""
        resp = self._get("OTHER/core/other/htmlreport/")
        return resp.text if resp.ok else f"Report failed: {resp.status_code}"

    def generate_xml_report(self) -> str:
        """Generate an XML report."""
        resp = self._get("OTHER/core/other/xmlreport/")
        return resp.text if resp.ok else f"Report failed: {resp.status_code}"

    def generate_markdown_report(self) -> str:
        """Generate a Markdown report."""
        resp = self._get("OTHER/core/other/mdreport/")
        return resp.text if resp.ok else f"Report failed: {resp.status_code}"

    # ── Session ──────────────────────────────────────────────────────────

    def new_session(self, name: str = "kai_session", overwrite: bool = True) -> dict:
        """Create a new ZAP session."""
        return self._result(
            self._post("JSON/core/action/newSession/",
                       {"name": name, "overwrite": str(overwrite).lower()}))

    def load_session(self, name: str) -> dict:
        """Load an existing session."""
        return self._result(
            self._post("JSON/core/action/loadSession/", {"name": name}))

    def save_session(self, name: str) -> dict:
        """Save current session."""
        return self._result(
            self._post("JSON/core/action/saveSession/", {"name": name}))

    # ── Context / Scope ──────────────────────────────────────────────────

    def new_context(self, name: str) -> dict:
        """Create a new context."""
        return self._result(
            self._post("JSON/context/action/newContext/", {"contextName": name}))

    def include_in_context(self, context_name: str, regex: str) -> dict:
        """Include URLs matching regex in context."""
        return self._result(
            self._post("JSON/context/action/includeInContext/",
                       {"contextName": context_name, "regex": regex}))

    def exclude_from_context(self, context_name: str, regex: str) -> dict:
        """Exclude URLs matching regex from context."""
        return self._result(
            self._post("JSON/context/action/excludeFromContext/",
                       {"contextName": context_name, "regex": regex}))

    def set_context_in_scope(self, context_name: str,
                             boolean_value: bool = True) -> dict:
        """Set whether a context is in scope."""
        return self._result(
            self._post("JSON/context/action/setContextInScope/",
                       {"contextName": context_name,
                        "booleanInScope": str(boolean_value).lower()}))

    # ── Params ───────────────────────────────────────────────────────────

    def params(self, site: str = "") -> dict:
        """List parameters for a site."""
        params = {}
        if site:
            params["site"] = site
        return self._result(self._get("JSON/params/view/params/", params))
