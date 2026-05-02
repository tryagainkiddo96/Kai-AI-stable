#!/usr/bin/env python3
"""
Lightweight Kai Agent Node — deploy to any device on your network.
Acts as a remote execution endpoint controlled by the main Kai instance.

Usage:
  python kai_agent_node.py              # Show info
  python kai_agent_node.py --daemon     # Run as persistent server
  python kai_agent_node.py --port 9999  # Custom port
"""
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone

PORT = int(os.environ.get("KAI_NODE_PORT", "8765"))
WORKSPACE = Path.home() / ".kai_node"
WORKSPACE.mkdir(parents=True, exist_ok=True)

LOG_FILE = WORKSPACE / "agent.log"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line.strip())


class KaiAgentHandler(BaseHTTPRequestHandler):
    """HTTP handler for Kai agent node commands."""

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "name": socket.gethostname(),
                "os": f"{platform.system()} {platform.release()}",
                "platform": sys.platform,
                "python": platform.python_version(),
                "status": "running",
                "port": PORT,
                "uptime": time.time() - START_TIME,
                "workspace": str(WORKSPACE),
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        elif self.path == "/log":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            try:
                lines = LOG_FILE.read_text(encoding="utf-8")[-4000:]
            except Exception:
                lines = "No log available."
            self.wfile.write(lines.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/execute":
            self._handle_execute()
        elif self.path == "/upload":
            self._handle_upload()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_execute(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json_response(400, {"ok": False, "error": "Invalid JSON"})
            return

        command = data.get("command", "")
        timeout = data.get("timeout", 30)
        cwd = data.get("cwd", str(WORKSPACE))

        if not command:
            self._json_response(400, {"ok": False, "error": "No command provided"})
            return

        log(f"EXEC: {command[:200]}")

        try:
            if platform.system() == "Windows":
                shell_args = ["powershell", "-NoProfile", "-Command", command]
            else:
                shell_args = ["bash", "-c", command]

            result = subprocess.run(
                shell_args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            response = {
                "ok": result.returncode == 0,
                "stdout": result.stdout[:8000],
                "stderr": result.stderr[:4000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            response = {"ok": False, "error": f"Command timed out after {timeout}s"}
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}

        log(f"RESULT: ok={response.get('ok')}, len={len(response.get('stdout', '') or '')}")
        self._json_response(200, response)

    def _handle_upload(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        filename = self.headers.get("X-Filename", "uploaded_file")
        dest = WORKSPACE / filename

        try:
            dest.write_bytes(body)
            self._json_response(200, {"ok": True, "path": str(dest), "size": len(body)})
        except Exception as exc:
            self._json_response(500, {"ok": False, "error": str(exc)})

    def _json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # Suppress default HTTP server logs


START_TIME = time.time()


def run_daemon(port: int = PORT):
    """Run the Kai agent node as a persistent server."""
    server = HTTPServer(("0.0.0.0", port), KaiAgentHandler)
    log(f"Kai agent node v1.0 starting on port {port}")
    log(f"Hostname: {socket.gethostname()}")
    log(f"OS: {platform.system()} {platform.release()}")
    log(f"Workspace: {WORKSPACE}")
    log(f"Health: http://<this-ip>:{port}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down Kai agent node.")
        server.shutdown()


def run_info():
    """Show agent info without starting the server."""
    ip = "unknown"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print(f"Kai Agent Node v1.0")
    print(f"  Hostname: {socket.gethostname()}")
    print(f"  Local IP: {ip}")
    print(f"  Port: {PORT}")
    print(f"  Workspace: {WORKSPACE}")
    print(f"  Health URL: http://{ip}:{PORT}/health")
    print()
    print("Commands:")
    print("  --daemon          Start the agent server")
    print("  --port <number>   Use a custom port")
    print()
    print("Deploy from main Kai instance:")
    print("  mesh deploy <this-device-ip>")


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        # Parse custom port
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                PORT = int(sys.argv[i + 1])
                break
        run_daemon(PORT)
    else:
        run_info()
