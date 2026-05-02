"""Kali Tools — persistent WSL Kali session management."""
from __future__ import annotations

import json
import platform
import shlex
import subprocess
import threading
import time
import uuid
from queue import Empty, Queue
from pathlib import Path

from kai_agent.tools.shell_tools import ShellTools


class KaliTools:
    def __init__(self, workspace: Path, shell_tools: ShellTools) -> None:
        self.workspace = workspace
        self.shell = shell_tools
        self.kali_process: subprocess.Popen[bytes] | None = None
        self.kali_queue: Queue[str] = Queue()
        self.kali_reader_thread: threading.Thread | None = None
        self.kali_lock = threading.Lock()
        self.kali_session_cwd = self._to_wsl_path(self.workspace)

    def _to_wsl_path(self, path: Path) -> str:
        path = path.resolve()
        if self.shell.is_linux:
            return str(path)
        drive = path.drive.rstrip(":").lower()
        parts = [part for part in path.parts[1:] if part not in (path.drive, "\\", "/")]
        return f"/mnt/{drive}/" + "/".join(parts)

    def _kali_reader(self) -> None:
        if not self.kali_process or not self.kali_process.stdout:
            return
        for raw_line in self.kali_process.stdout:
            self.kali_queue.put(raw_line.decode("utf-8", errors="replace").rstrip("\r\n"))

    def ensure_session(self) -> None:
        if self.kali_process and self.kali_process.poll() is None:
            return
        if self.shell.is_linux:
            self.kali_process = subprocess.Popen(
                ["bash", "--noprofile", "--norc"],
                cwd=str(self.workspace), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
            )
        else:
            self.kali_process = subprocess.Popen(
                ["wsl.exe", "-d", "kali-linux", "--", "bash", "--noprofile", "--norc"],
                cwd=str(self.workspace), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
            )
        self.kali_queue = Queue()
        self.kali_reader_thread = threading.Thread(target=self._kali_reader, daemon=True)
        self.kali_reader_thread.start()
        ready_token = f"__KAI_READY__{uuid.uuid4().hex}"
        init_cmd = f"export TERM=dumb\nunset PROMPT_COMMAND\nPS1=''\ncd {shlex.quote(self.kali_session_cwd)}\necho {ready_token}\n"
        assert self.kali_process.stdin is not None
        self.kali_process.stdin.write(init_cmd.encode("utf-8"))
        self.kali_process.stdin.flush()
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                if self.kali_queue.get(timeout=0.5) == ready_token:
                    return
            except Empty:
                continue
        raise RuntimeError("Timed out starting persistent Kali session.")

    def start_session(self) -> str:
        with self.kali_lock:
            try:
                self.ensure_session()
                return json.dumps({"action": "kali_session_start", "ok": True, "cwd": self.kali_session_cwd, "message": "Kali session ready."}, indent=2)
            except Exception as exc:
                return json.dumps({"action": "kali_session_start", "ok": False, "cwd": self.kali_session_cwd, "error": str(exc)}, indent=2)

    def stop_session(self) -> str:
        with self.kali_lock:
            if not self.kali_process or self.kali_process.poll() is not None:
                return json.dumps({"action": "kali_session_stop", "ok": True, "message": "Kali session was not running."}, indent=2)
            try:
                if self.kali_process.stdin:
                    self.kali_process.stdin.write(b"exit\n")
                    self.kali_process.stdin.flush()
                self.kali_process.wait(timeout=5)
            except Exception:
                self.kali_process.kill()
            finally:
                self.kali_process = None
            return json.dumps({"action": "kali_session_stop", "ok": True, "message": "Stopped Kali session."}, indent=2)

    def session_status(self) -> str:
        running = bool(self.kali_process and self.kali_process.poll() is None)
        return json.dumps({"action": "kali_session_status", "ok": True, "running": running, "cwd": self.kali_session_cwd}, indent=2)

    def run_command(self, command: str, timeout: int = 180) -> str:
        with self.kali_lock:
            self.ensure_session()
            assert self.kali_process is not None and self.kali_process.stdin is not None
            token = uuid.uuid4().hex
            start = f"__KAI_START__{token}"
            cwd_marker = f"__KAI_CWD__{token}__"
            end = f"__KAI_END__{token}__"
            wrapped = f"echo {start}\n{command}\nstatus=$?\nprintf '\\n'\nprintf '{cwd_marker}%s\\n' \"$(pwd)\"\nprintf '{end}%s\\n' \"$status\"\n"
            self.kali_process.stdin.write(wrapped.encode("utf-8"))
            self.kali_process.stdin.flush()
            lines: list[str] = []
            current_cwd = self.kali_session_cwd
            status: int | None = None
            started = False
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    line = self.kali_queue.get(timeout=0.5)
                except Empty:
                    continue
                if not started:
                    if line == start:
                        started = True
                    continue
                if line.startswith(cwd_marker):
                    current_cwd = line[len(cwd_marker):]
                    continue
                if line.startswith(end):
                    try:
                        status = int(line[len(end):])
                    except ValueError:
                        status = -1
                    break
                lines.append(line)
            if status is None:
                raise RuntimeError("Timed out waiting for Kali session command.")
            self.kali_session_cwd = current_cwd
            payload = {
                "action": "kali_session_command", "command": command, "cwd": current_cwd,
                "returncode": status, "stdout": "\n".join(lines).strip()[:12000],
                "stderr": "", "ok": status == 0, **self.shell.classify_command(command),
            }
            return json.dumps(payload, indent=2)
