"""Traffic Eye — passive network monitor + optional HTTP proxy.

Passive mode:
  Polls Get-NetTCPConnection every 3s, logs all established connections.
  Zero config, works immediately.

HTTP Proxy mode:
  Pure stdlib HTTP proxy on port 8080. Set browser to localhost:8080.
  Logs all HTTP requests. HTTPS shown as tunnels (content encrypted).
"""
from __future__ import annotations

import json
import re
import socket
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


class TrafficEye:
    """Monitors all network connections on this machine."""

    def __init__(self, db):
        self.db = db
        self._poll_thread: threading.Thread | None = None
        self._proxy_server: HTTPServer | None = None
        self._proxy_thread: threading.Thread | None = None
        self._enabled = False
        self._proxy_enabled = False
        self._known_connections: set[tuple] = set()
        self._live_buffer: list[dict] = []
        self._buffer_lock = threading.Lock()
        self._max_buffer = 200

    # ── Passive Connection Monitor ───────────────────────────────────────────

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        self._enabled = False

    def _poll_loop(self):
        while self._enabled:
            try:
                self._poll_connections()
            except Exception:
                pass
            time.sleep(3)

    def _poll_connections(self):
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object State -eq 'Established' | "
             "Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, OwningProcess | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=5,
        )
        if not r.stdout.strip():
            return
        try:
            data = json.loads(r.stdout.strip())
        except json.JSONDecodeError:
            return
        if isinstance(data, dict):
            data = [data]

        current: set[tuple] = set()
        for item in data:
            local = f"{item.get('LocalAddress','')}:{item.get('LocalPort','')}"
            remote = f"{item.get('RemoteAddress','')}:{item.get('RemotePort','')}"
            pid = item.get("OwningProcess", "")
            proc_name = self._get_process_name(pid)
            key = (local, remote)
            current.add(key)

            if key not in self._known_connections:
                self._known_connections.add(key)
                entry = {
                    "local": local, "remote": remote,
                    "process": proc_name, "time": time.time(),
                }
                self.db.log_traffic(
                    item.get("LocalAddress", ""), int(item.get("LocalPort", 0)),
                    item.get("RemoteAddress", ""), int(item.get("RemotePort", 0)),
                    process_name=proc_name, state="Established",
                )
                with self._buffer_lock:
                    self._live_buffer.append(entry)
                    if len(self._live_buffer) > self._max_buffer:
                        self._live_buffer = self._live_buffer[-self._max_buffer:]

    def _get_process_name(self, pid: str) -> str:
        if not pid:
            return ""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"],
                capture_output=True, text=True, timeout=2,
            )
            return r.stdout.strip()
        except Exception:
            return ""

    def get_live(self) -> list[dict]:
        with self._buffer_lock:
            return list(self._live_buffer)

    def get_history(self, limit: int = 100) -> list[dict]:
        return self.db.query_traffic(limit=limit)

    # ── HTTP Proxy Mode ──────────────────────────────────────────────────────

    def start_proxy(self, port: int = 8080):
        if self._proxy_enabled:
            return
        try:
            self._proxy_server = HTTPServer(("127.0.0.1", port), lambda *a: _ProxyHandler(self.db, *a))
            self._proxy_enabled = True
            self._proxy_thread = threading.Thread(target=self._proxy_server.serve_forever, daemon=True)
            self._proxy_thread.start()
        except Exception:
            pass

    def stop_proxy(self):
        self._proxy_enabled = False
        if self._proxy_server:
            self._proxy_server.shutdown()
            self._proxy_server = None


class _ProxyHandler(BaseHTTPRequestHandler):
    """HTTP proxy request handler. Logs each request to CTOS DB."""

    def __init__(self, db, *args):
        self._traffic_db = db
        super().__init__(*args)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_PUT(self):
        self._proxy_request("PUT")

    def do_DELETE(self):
        self._proxy_request("DELETE")

    def do_PATCH(self):
        self._proxy_request("PATCH")

    def do_HEAD(self):
        self._proxy_request("HEAD")

    def do_OPTIONS(self):
        self._proxy_request("OPTIONS")

    def do_CONNECT(self):
        """HTTPS CONNECT tunnel — log but can't intercept content."""
        try:
            host, port_str = self.path.split(":", 1)
            port = int(port_str)
        except (ValueError, IndexError):
            self.send_error(400)
            return

        self._traffic_db.log_traffic(
            self.client_address[0], 0, host, port,
            protocol="HTTPS", process_name="proxy", state="Tunnel",
        )

        try:
            remote = socket.create_connection((host, port), timeout=10)
            self.send_response(200, "Connection Established")
            self.end_headers()

            self.wfile.flush()
            self.connection.setblocking(True)

            threads = []
            for src, dst in [(self.connection, remote), (remote, self.connection)]:
                t = threading.Thread(target=self._relay, args=(src, dst), daemon=True)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        except Exception:
            self.send_error(502)

    def _relay(self, src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass

    def _proxy_request(self, method: str):
        url = self.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        self._traffic_db.log_traffic(
            self.client_address[0], 0, url, 80,
            protocol=f"HTTP {method}", process_name="proxy", state="Request",
        )

        try:
            req = Request(url, data=body if body else None,
                          headers=dict(self.headers), method=method)
            resp = urlopen(req, timeout=15)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                    self.send_header(k, v)
            resp_body = resp.read()
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except URLError as e:
            self.send_error(502, str(e.reason))
        except Exception as e:
            self.send_error(500, str(e))


