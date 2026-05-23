from __future__ import annotations

import json
import os
import platform
import re
import shlex
import subprocess
import threading
import time
import uuid
from queue import Empty, Queue
from pathlib import Path
import pyautogui

from kai_agent.browser_tools import BrowserTools
from kai_agent.document_handler import DocumentHandler
from kai_agent.tavily_client import TavilyClient
from kai_agent.tool_policy import ToolPolicy
from kai_agent.anonymity_stack import AnonymityStack



def _load_config_key(key: str) -> str:
    config_path = Path("kai_config.json")
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            value = str(cfg.get(key, "")).strip()
            if value:
                return value
        except Exception:
            pass
    return ""

# Cross-platform Tesseract path
tesseract_path_from_config = _load_config_key("tesseract_path")
if tesseract_path_from_config:
    TESSERACT_PATH = Path(tesseract_path_from_config)
elif platform.system() == "Windows":
    TESSERACT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
else:
    # Linux/WSL paths
    TESSERACT_PATH = Path("/usr/bin/tesseract")
    if not TESSERACT_PATH.exists():
        TESSERACT_PATH = Path("/usr/local/bin/tesseract")

SUBPROCESS_TEXT_KWARGS = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}


class DesktopTools:
    def __init__(self, workspace: Path, chimera=None) -> None:
        self.workspace = workspace
        self.tmp_dir = workspace / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.kali_process: subprocess.Popen[bytes] | None = None
        self.kali_queue: Queue[str] = Queue()
        self.kali_reader_thread: threading.Thread | None = None
        self.kali_lock = threading.Lock()
        self.chimera = chimera
        
        # OS detection
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.shell_cmd = "powershell" if self.is_windows else "bash"
        self.shell_flag = "-Command" if self.is_windows else "-c"

        self.kali_session_cwd = self._to_wsl_path(self.workspace)
        self.tavily = TavilyClient()
        self.anonymity = AnonymityStack(workspace)
        self.browser = BrowserTools(workspace, chimera=chimera, anonymity=self.anonymity)
        self.documents = DocumentHandler(workspace)
        self.policy = ToolPolicy(workspace)

    def _policy_block(self, action: str, **payload) -> str:
        decision = self.policy.evaluate(action, payload)
        self.policy.record(action, payload, decision)
        if decision.get("allowed", False):
            return ""
        return json.dumps(
            {
                "action": action,
                "ok": False,
                "blocked": True,
                **decision,
                **{key: str(value) if isinstance(value, Path) else value for key, value in payload.items()},
            },
            indent=2,
        )

    def policy_status(self) -> str:
        return json.dumps(self.policy.status(), indent=2)

    def set_policy_mode(self, mode: str) -> str:
        return json.dumps(self.policy.set_mode(mode), indent=2)

    def list_capabilities(self) -> str:
        return json.dumps(self.policy.capabilities(), indent=2)

    def build_tool_context(self) -> str:
        return self.policy.build_context()

    def classify_command(self, command: str, shell: str = "powershell") -> dict:
        lowered = command.strip().lower()
        tags: list[str] = []
        level = 3

        safe_prefixes = [
            "pwd",
            "ls",
            "dir",
            "whoami",
            "echo ",
            "cat ",
            "type ",
            "ss ",
            "ip ",
            "ifconfig",
            "journalctl",
            "systemctl status",
            "Get-ChildItem".lower(),
            "Get-Content".lower(),
        ]
        caution_terms = [
            "apt install",
            "pip install",
            "npm install",
            "winget install",
            "git clone",
            "curl ",
            "wget ",
            "Invoke-WebRequest".lower(),
            "Start-Process".lower(),
        ]
        destructive_terms = [
            "rm ",
            "del ",
            "rmdir ",
            "format ",
            "mkfs",
            "shutdown",
            "reboot",
            "poweroff",
            "sc delete",
            "reg delete",
            "Remove-Item".lower(),
        ]

        if any(term in lowered for term in destructive_terms):
            tags.extend(["destructive", "system-changing"])
            level = 5
        elif any(term in lowered for term in caution_terms):
            tags.append("caution")
            level = 4
        elif any(lowered == prefix or lowered.startswith(prefix) for prefix in safe_prefixes):
            tags.append("safe")
            level = 2
        else:
            tags.append("caution")
            level = 3

        if any(term in lowered for term in ["curl ", "wget ", "invoke-webrequest", "nmap", "ffuf", "ping ", "nslookup", "dig "]):
            tags.append("network-active")
        if any(term in lowered for term in ["apt ", "dpkg ", "pip ", "npm ", "winget ", "choco ", "systemctl ", "service "]):
            tags.append("system-changing")
        if not tags:
            tags.append("safe")

        return {
            "command": command,
            "shell": shell,
            "confidence": tags[0],
            "tags": tags,
            "action_level": level,
            "requires_confirmation": level >= 4 or "destructive" in tags,
        }

    def preview_command(self, command: str, shell: str = "powershell") -> str:
        payload = {
            "action": "command_preview",
            "ok": True,
            **self.classify_command(command, shell=shell),
        }
        return json.dumps(payload, indent=2)

    def run_shell(self, command: str, timeout: int = 30) -> str:
        meta = self.classify_command(command, shell=self.shell_cmd)
        blocked = self._policy_block("run_shell", timeout=timeout, **meta)
        if blocked:
            return blocked
        
        # Cross-platform shell execution
        if self.is_windows:
            shell_args = ["powershell", "-NoProfile", "-Command", command]
        else:
            shell_args = ["bash", "-c", command]
            
        try:
            completed = subprocess.run(
                shell_args,
                cwd=str(self.workspace),
                capture_output=True,
                timeout=timeout,
                **SUBPROCESS_TEXT_KWARGS,
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            payload = {
                "action": "run_shell",
                "command": command,
                "returncode": completed.returncode,
                "stdout": stdout[:8000],
                "stderr": stderr[:4000],
                **meta,
            }
        except subprocess.TimeoutExpired:
            payload = {
                "action": "run_shell",
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                **meta,
            }
        except Exception as exc:
            payload = {
                "action": "run_shell",
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command failed: {exc}",
                **meta,
            }
        self.policy.record("run_shell", payload, {"allowed": bool(payload.get("returncode", -1) != -999), "policy_mode": self.policy.status()["mode"], "policy_reason": "Executed through policy-approved shell path."})
        return json.dumps(payload, indent=2)

    def run_wsl(self, command: str, timeout: int = 60, distro: str = "kali-linux") -> str:
        meta = self.classify_command(command, shell="bash")
        blocked = self._policy_block("run_wsl", timeout=timeout, distro=distro, **meta)
        if blocked:
            return blocked
        
        # In WSL, just run bash directly instead of nested wsl.exe
        if self.is_linux:
            try:
                completed = subprocess.run(
                    ["bash", "-lc", command],
                    cwd=str(self.workspace),
                    capture_output=True,
                    timeout=timeout,
                    **SUBPROCESS_TEXT_KWARGS,
                )
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout.strip()[:8000],
                    "stderr": completed.stderr.strip()[:4000],
                    **meta,
                }
            except subprocess.TimeoutExpired:
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"WSL command timed out after {timeout}s",
                    **meta,
                }
            except Exception as exc:
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"WSL command failed: {exc}",
                    **meta,
                }
        else:
            # Windows: use wsl.exe
            try:
                completed = subprocess.run(
                    ["wsl.exe", "-d", distro, "--", "bash", "-lc", command],
                    cwd=str(self.workspace),
                    capture_output=True,
                    timeout=timeout,
                    **SUBPROCESS_TEXT_KWARGS,
                )
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout.strip()[:8000],
                    "stderr": completed.stderr.strip()[:4000],
                    **meta,
                }
            except subprocess.TimeoutExpired:
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"WSL command timed out after {timeout}s",
                    **meta,
                }
            except Exception as exc:
                payload = {
                    "action": "run_wsl",
                    "command": command,
                    "distro": distro,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"WSL command failed: {exc}",
                    **meta,
                }
        self.policy.record("run_wsl", payload, {"allowed": True, "policy_mode": self.policy.status()["mode"], "policy_reason": "Executed through policy-approved WSL path."})
        return json.dumps(payload, indent=2)

    def _kali_reader(self) -> None:
        if not self.kali_process or not self.kali_process.stdout:
            return
        for raw_line in self.kali_process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            self.kali_queue.put(line)

    def ensure_kali_session(self) -> None:
        if self.kali_process and self.kali_process.poll() is None:
            return

        # In WSL, run bash directly
        if self.is_linux:
            self.kali_process = subprocess.Popen(
                ["bash", "--noprofile", "--norc"],
                cwd=str(self.workspace),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
        else:
            self.kali_process = subprocess.Popen(
                ["wsl.exe", "-d", "kali-linux", "--", "bash", "--noprofile", "--norc"],
                cwd=str(self.workspace),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
        self.kali_queue = Queue()
        self.kali_reader_thread = threading.Thread(target=self._kali_reader, daemon=True)
        self.kali_reader_thread.start()

        ready_token = f"__KAI_READY__{uuid.uuid4().hex}"
        init_cmd = (
            "export TERM=dumb\n"
            "unset PROMPT_COMMAND\n"
            "PS1=''\n"
            f"cd {shlex.quote(self.kali_session_cwd)}\n"
            f"echo {ready_token}\n"
        )
        assert self.kali_process.stdin is not None
        self.kali_process.stdin.write(init_cmd.encode("utf-8"))
        self.kali_process.stdin.flush()

        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                line = self.kali_queue.get(timeout=0.5)
                if line == ready_token:
                    return
            except Empty:
                continue
        raise RuntimeError("Timed out starting persistent Kali session.")

    def stop_kali_session(self) -> str:
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

    def start_kali_session(self) -> str:
        with self.kali_lock:
            try:
                self.ensure_kali_session()
                payload = {
                    "action": "kali_session_start",
                    "ok": True,
                    "cwd": self.kali_session_cwd,
                    "message": "Persistent Kali session is ready.",
                }
            except Exception as exc:
                payload = {
                    "action": "kali_session_start",
                    "ok": False,
                    "cwd": self.kali_session_cwd,
                    "error": str(exc),
                }
        return json.dumps(payload, indent=2)

    def get_kali_session_status(self) -> str:
        running = bool(self.kali_process and self.kali_process.poll() is None)
        payload = {
            "action": "kali_session_status",
            "ok": True,
            "running": running,
            "cwd": self.kali_session_cwd,
        }
        return json.dumps(payload, indent=2)

    def complete_kali_input(self, partial: str, limit: int = 12) -> str:
        fragment = partial.strip()
        if not fragment:
            target = ""
            base_prefix = ""
        elif partial.endswith(" "):
            target = ""
            base_prefix = partial
        else:
            if " " in fragment:
                base_prefix, target = fragment.rsplit(" ", 1)
                base_prefix += " "
            else:
                base_prefix = ""
                target = fragment

        quoted_target = shlex.quote(target)
        command = (
            "target="
            + quoted_target
            + "\n"
            + "compgen -cdfa -- \"$target\" | head -n "
            + str(limit)
        )
        result = json.loads(self.run_kali_session_command(command, timeout=30))
        raw_output = result.get("stdout", "")
        suggestions = []
        for item in raw_output.splitlines():
            item = item.strip()
            if not item:
                continue
            suggestions.append(f"{base_prefix}{item}")

        payload = {
            "action": "kali_completion",
            "ok": result.get("ok", False),
            "partial": partial,
            "cwd": result.get("cwd", self.kali_session_cwd),
            "suggestions": suggestions[:limit],
        }
        if result.get("stderr"):
            payload["stderr"] = result["stderr"]
        return json.dumps(payload, indent=2)

    def run_kali_session_command(self, command: str, timeout: int = 180) -> str:
        with self.kali_lock:
            self.ensure_kali_session()
            assert self.kali_process is not None and self.kali_process.stdin is not None
            token = uuid.uuid4().hex
            start = f"__KAI_START__{token}"
            cwd_marker = f"__KAI_CWD__{token}__"
            end = f"__KAI_END__{token}__"
            wrapped = (
                f"echo {start}\n"
                f"{command}\n"
                f"status=$?\n"
                "printf '\\n'\n"
                f"printf '{cwd_marker}%s\\n' \"$(pwd)\"\n"
                f"printf '{end}%s\\n' \"$status\"\n"
            )
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
                    current_cwd = line[len(cwd_marker) :]
                    continue
                if line.startswith(end):
                    try:
                        status = int(line[len(end) :])
                    except ValueError:
                        status = -1
                    break
                lines.append(line)

            if status is None:
                raise RuntimeError("Timed out waiting for Kali session command to finish.")

            self.kali_session_cwd = current_cwd
            payload = {
                "action": "kali_session_command",
                "command": command,
                "cwd": current_cwd,
                "returncode": status,
                "stdout": "\n".join(lines).strip()[:12000],
                "stderr": "",
                "ok": status == 0,
                **self.classify_command(command, shell="bash"),
            }
            return json.dumps(payload, indent=2)

    def ask_kali_helper(self, prompt: str, use_web: bool = False) -> str:
        kai_cmd = "/home/tryagain/.local/bin/kai"
        if self.is_linux:
            args = [kai_cmd]
        else:
            args = ["wsl.exe", "-d", "kali-linux", "--", kai_cmd]
        if use_web:
            args.append("--web")
        args.append(prompt)
        result = self._run_native(args, timeout=240)
        payload = {
            "action": "ask_kali_helper",
            "prompt": prompt,
            "use_web": use_web,
            **result,
        }
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def search_web(self, query: str, max_results: int = 5) -> str:
        return json.dumps(self.tavily.search(query=query, max_results=max_results), indent=2)

    def _run_native(self, args: list[str], timeout: int = 120, cwd: Path | None = None) -> dict:
        try:
            completed = subprocess.run(
                args,
                cwd=str(cwd or self.workspace),
                capture_output=True,
                timeout=timeout,
                **SUBPROCESS_TEXT_KWARGS,
            )
            return {
                "command": args,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip()[:12000],
                "stderr": completed.stderr.strip()[:6000],
            }
        except subprocess.TimeoutExpired:
            return {
                "command": args,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
            }
        except Exception as exc:
            return {
                "command": args,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command failed: {exc}",
            }

    def _ensure_command(self, command: str) -> tuple[bool, str]:
        candidates = {
            "git": ["git", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"] if self.is_linux else ["npm.cmd", "--version"],
            "python": ["python3", "--version"] if self.is_linux else ["python", "--version"],
            "tesseract": [str(TESSERACT_PATH), "--version"],
        }
        if command in candidates:
            check = self._run_native(candidates[command], timeout=20)
            if check["returncode"] == 0:
                return True, f"{command} already available."

        if self.is_linux:
            installers = {
                "git": ["sudo", "apt", "install", "-y", "git"],
                "node": ["sudo", "apt", "install", "-y", "nodejs", "npm"],
                "npm": ["sudo", "apt", "install", "-y", "nodejs", "npm"],
                "python": ["sudo", "apt", "install", "-y", "python3", "python3-pip"],
                "tesseract": ["sudo", "apt", "install", "-y", "tesseract-ocr"],
            }
        else:
            installers = {
                "git": ["winget", "install", "--id", "Git.Git", "--exact", "--accept-package-agreements", "--accept-source-agreements"],
                "node": ["winget", "install", "--id", "OpenJS.NodeJS", "--exact", "--accept-package-agreements", "--accept-source-agreements"],
                "npm": ["winget", "install", "--id", "OpenJS.NodeJS", "--exact", "--accept-package-agreements", "--accept-source-agreements"],
                "python": ["winget", "install", "--id", "Python.Python.3.12", "--exact", "--accept-package-agreements", "--accept-source-agreements"],
                "tesseract": ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "--exact", "--accept-package-agreements", "--accept-source-agreements"],
            }
        install_args = installers.get(command)
        if not install_args:
            return False, f"No automatic installer is configured for {command}."

        result = self._run_native(install_args, timeout=900)
        if result["returncode"] == 0:
            return True, f"Installed {command}."
        return False, result["stderr"] or result["stdout"] or f"Failed to install {command}."

    def _resolve_path(self, raw_path: str) -> Path:
        raw_path = raw_path.strip().strip('"').strip("'")
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        return (self.workspace / candidate).resolve()

    def _to_wsl_path(self, path: Path) -> str:
        path = path.resolve()
        if self.is_linux:
            # Already in Linux, return normal path
            return str(path)
        drive = path.drive.rstrip(":").lower()
        parts = [part for part in path.parts[1:] if part not in (path.drive, "\\", "/")]
        joined = "/".join(parts)
        return f"/mnt/{drive}/{joined}"

    def open_path(self, path: str) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block("open_path", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "open_path", "ok": False, "error": f"Path not found: {target}"}, indent=2)
        try:
            if self.is_windows:
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(target)], check=True, capture_output=True)
            return json.dumps({"action": "open_path", "ok": True, "path": str(target)}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "open_path", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def write_file(self, path: str, content: str) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block("write_file", path=target, chars_written=len(content))
        if blocked:
            return blocked
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return json.dumps(
                {
                    "action": "write_file",
                    "ok": True,
                    "path": str(target),
                    "chars_written": len(content),
                },
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"action": "write_file", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def append_file(self, path: str, content: str) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block("append_file", path=target, chars_appended=len(content))
        if blocked:
            return blocked
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(content)
            return json.dumps(
                {
                    "action": "append_file",
                    "ok": True,
                    "path": str(target),
                    "chars_appended": len(content),
                },
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"action": "append_file", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def replace_in_file(self, path: str, old_text: str, new_text: str) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block("replace_in_file", path=target, replaced_chars=len(old_text), new_chars=len(new_text))
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "replace_in_file", "ok": False, "path": str(target), "error": "File not found."}, indent=2)
        try:
            original = target.read_text(encoding="utf-8", errors="replace")
            if old_text not in original:
                return json.dumps(
                    {
                        "action": "replace_in_file",
                        "ok": False,
                        "path": str(target),
                        "error": "Target text was not found in the file.",
                    },
                    indent=2,
                )
            updated = original.replace(old_text, new_text, 1)
            target.write_text(updated, encoding="utf-8")
            return json.dumps(
                {
                    "action": "replace_in_file",
                    "ok": True,
                    "path": str(target),
                    "replaced_chars": len(old_text),
                    "new_chars": len(new_text),
                },
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"action": "replace_in_file", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def extract_zip(self, archive_path: str, destination: str | None = None) -> str:
        archive = self._resolve_path(archive_path)
        if not archive.exists():
            return json.dumps({"action": "extract_zip", "ok": False, "error": f"Archive not found: {archive}"}, indent=2)
        target_dir = self._resolve_path(destination) if destination else archive.with_suffix("")
        blocked = self._policy_block("extract_zip", archive=archive, destination=target_dir)
        if blocked:
            return blocked
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if self.is_linux:
            result = self._run_native(
                ["unzip", "-o", str(archive), "-d", str(target_dir)],
                timeout=600,
            )
        else:
            result = self._run_native(
                ["powershell", "-NoProfile", "-Command", f"Expand-Archive -LiteralPath '{archive}' -DestinationPath '{target_dir}' -Force"],
                timeout=600,
            )
        payload = {"action": "extract_zip", "archive": str(archive), "destination": str(target_dir), **result}
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def clone_repo(self, repo_url: str, destination: str | None = None) -> str:
        target = self._resolve_path(destination) if destination else (self.workspace / (Path(repo_url.rstrip("/")).stem or "repo"))
        blocked = self._policy_block("clone_repo", repo_url=repo_url, destination=target)
        if blocked:
            return blocked
        ok, ensure_msg = self._ensure_command("git")
        if not ok:
            return json.dumps({"action": "clone_repo", "ok": False, "error": ensure_msg}, indent=2)
        result = self._run_native(["git", "clone", repo_url, str(target)], timeout=1200)
        payload = {"action": "clone_repo", "repo_url": repo_url, "destination": str(target), "setup": ensure_msg, **result}
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def install_project(self, target_path: str) -> str:
        target = self._resolve_path(target_path)
        blocked = self._policy_block("install_project", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "install_project", "ok": False, "error": f"Project path not found: {target}"}, indent=2)

        steps: list[dict] = []
        if (target / "package.json").exists():
            ok, msg = self._ensure_command("npm")
            steps.append({"tool": "npm", "setup": msg})
            if ok:
                steps.append(self._run_native(["npm", "install"], cwd=target, timeout=1800))
        if (target / "requirements.txt").exists():
            ok, msg = self._ensure_command("python")
            steps.append({"tool": "python", "setup": msg})
            if ok:
                steps.append(self._run_native(["python3", "-m", "pip", "install", "-r", "requirements.txt"], cwd=target, timeout=1800))
        if (target / "pyproject.toml").exists() and not (target / "requirements.txt").exists():
            ok, msg = self._ensure_command("python")
            steps.append({"tool": "python", "setup": msg})
            if ok:
                steps.append(self._run_native(["python3", "-m", "pip", "install", "-e", "."], cwd=target, timeout=1800))

        if not steps:
            return json.dumps(
                {
                    "action": "install_project",
                    "ok": False,
                    "path": str(target),
                    "error": "No supported project manifest found. I looked for package.json, requirements.txt, and pyproject.toml.",
                },
                indent=2,
            )

        ok = any(isinstance(step, dict) and step.get("returncode") == 0 for step in steps)
        return json.dumps({"action": "install_project", "path": str(target), "ok": ok, "steps": steps}, indent=2)

    def run_project(self, target_path: str) -> str:
        target = self._resolve_path(target_path)
        blocked = self._policy_block("run_project", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "run_project", "ok": False, "error": f"Project path not found: {target}"}, indent=2)

        latest_launcher = target / "tools" / "launch_kai_latest.ps1"
        widget_launcher = target / "tools" / "launch_kai_widget.ps1"
        panel_launcher = target / "tools" / "launch_kai_panel.ps1"
        stack_launcher = target / "tools" / "launch_kai_stack.ps1"
        if latest_launcher.exists() or widget_launcher.exists() or panel_launcher.exists() or stack_launcher.exists():
            launcher = next(
                candidate
                for candidate in (latest_launcher, widget_launcher, panel_launcher, stack_launcher)
                if candidate.exists()
            )
            if self.is_linux:
                result = self._run_native(
                    ["bash", str(launcher)],
                    timeout=60,
                )
            else:
                # Use a more robust method for launching a new terminal process
                # This avoids complex string escaping and is more secure.
                # The command to be executed in the new terminal
                inner_command = f"cd '{target}'; python '{file_path}'"
                
                # Arguments for Start-Process
                start_process_args = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Start-Process",
                    "powershell",
                    "-ArgumentList",
                    f"-NoExit, -Command, \"{inner_command}\""
                ]
                
                result = self._run_native(
                    start_process_args,
                    timeout=60,
                )
            payload = {"action": "run_project", "path": str(target), "runner": f"python {file_path}", **result}
            payload["ok"] = result["returncode"] == 0
            return json.dumps(payload, indent=2)

        return json.dumps(
            {"action": "run_project", "ok": False, "path": str(target), "error": "No supported project entrypoint found."},
            indent=2,
        )

    def run_tests(self, target_path: str) -> str:
        target = self._resolve_path(target_path)
        blocked = self._policy_block("run_tests", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "run_tests", "ok": False, "error": f"Path not found: {target}"}, indent=2)

        if (target / "package.json").exists():
            ok, msg = self._ensure_command("npm")
            if not ok:
                return json.dumps({"action": "run_tests", "ok": False, "error": msg}, indent=2)
            result = self._run_native(["npm", "test"], cwd=target, timeout=600)
            payload = {"action": "run_tests", "path": str(target), "runner": "npm test", **result}
            payload["ok"] = result["returncode"] == 0
            return json.dumps(payload, indent=2)

        for candidate in ("pytest", "python -m pytest", "python3 -m pytest"):
            if self.is_linux:
                check = self._run_native(["bash", "-c", f"command -v {candidate.split()[0]}"], timeout=10)
            else:
                check = self._run_native(["powershell", "-Command", f"Get-Command {candidate.split()[0]}"], timeout=10)
            if check["returncode"] == 0:
                if self.is_linux:
                    result = self._run_native(["bash", "-c", f"cd {target} && {candidate}"], timeout=600)
                else:
                    result = self._run_native(["powershell", "-Command", f"cd {target}; {candidate}"], timeout=600)
                payload = {"action": "run_tests", "path": str(target), "runner": candidate, **result}
                payload["ok"] = result["returncode"] == 0
                return json.dumps(payload, indent=2)

        return json.dumps(
            {"action": "run_tests", "ok": False, "path": str(target), "error": "No supported test runner found."},
            indent=2,
        )

    def setup_github_project(self, repo_url: str) -> str:
        blocked = self._policy_block("setup_github_project", repo_url=repo_url)
        if blocked:
            return blocked
        clone_result = json.loads(self.clone_repo(repo_url))
        if not clone_result.get("ok"):
            return json.dumps({"action": "setup_github_project", "ok": False, "error": clone_result.get("error", "Clone failed.")}, indent=2)
        target = Path(clone_result["destination"])
        install_result = json.loads(self.install_project(str(target)))
        payload = {
            "action": "setup_github_project",
            "ok": install_result.get("ok", False),
            "repo_url": repo_url,
            "destination": str(target),
            "clone": clone_result,
            "install": install_result,
        }
        return json.dumps(payload, indent=2)

    def codex_edit(self, instruction: str) -> str:
        blocked = self._policy_block("codex_edit", instruction=instruction)
        if blocked:
            return blocked
        ok, msg = self._ensure_command("python")
        if not ok:
            return json.dumps({"action": "codex_edit", "ok": False, "error": msg}, indent=2)
        if self.is_linux:
            result = self._run_native(["python3", "-m", "codex", "edit", instruction], timeout=300)
        else:
            result = self._run_native(["powershell", "-Command", f"codex edit '{instruction}'"], timeout=300)
        payload = {"action": "codex_edit", "instruction": instruction, **result}
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def codex_edit_and_test(self, instruction: str) -> str:
        blocked = self._policy_block("codex_edit_and_test", instruction=instruction)
        if blocked:
            return blocked
        edit_result = json.loads(self.codex_edit(instruction))
        if not edit_result.get("ok"):
            return json.dumps({"action": "codex_edit_and_test", "ok": False, "edit": edit_result}, indent=2)
        test_result = json.loads(self.run_tests(str(self.workspace)))
        payload = {"action": "codex_edit_and_test", "ok": test_result.get("ok", False), "edit": edit_result, "test": test_result}
        return json.dumps(payload, indent=2)

    def read_file(self, path: str, max_chars: int = 8000) -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"[Error: File not found: {target}]"
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_chars:
                content = content[:max_chars] + "\n[...truncated...]"
            return content
        except Exception as exc:
            return f"[Error reading {target}: {exc}]"

    def list_files(self, path: str) -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"[Error: Path not found: {target}]"
        try:
            items = []
            for item in target.iterdir():
                item_type = "dir" if item.is_dir() else "file"
                items.append(f"{item_type}: {item.name}")
            return "\n".join(items)
        except Exception as exc:
            return f"[Error listing {target}: {exc}]"

    # Browser automation - delegated to BrowserTools
    def browse(self, url: str) -> str:
        return self.browser.browse(url)

    def search_browser(self, query: str) -> str:
        return self.browser.search(query)

    def get_page_content(self) -> str:
        return self.browser.get_page_content()

    def get_page_links(self) -> str:
        return self.browser.get_page_links()

    def click_link(self, text: str) -> str:
        return self.browser.click_link(text)

    def find_forms(self) -> str:
        return self.browser.find_forms()

    def fill_form(self, data: dict) -> str:
        return self.browser.fill_form(data)

    def screenshot(self) -> str:
        return self.browser.screenshot()

    def download_file(self, url: str | None = None, filename: str | None = None) -> str:
        return self.browser.download_file(url, filename)

    # Document management - delegated to DocumentHandler
    def list_documents(self) -> str:
        return self.documents.list_documents()

    def find_document(self, name: str) -> str:
        return self.documents.find_document(name)

    def read_document(self, path: str) -> str:
        return self.documents.read_document(path)

    def organize_downloads(self) -> str:
        return self.documents.organize_downloads()

    def document_stats(self) -> str:
        return self.documents.document_stats()

    # OCR and screen capture
    def _ocr_image(self, image_path: Path) -> str:
        if not TESSERACT_PATH.exists():
            return f"[Error: Tesseract not found at {TESSERACT_PATH}]"
        try:
            result = subprocess.run(
                [str(TESSERACT_PATH), str(image_path), "stdout", "-l", "eng"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip()
        except Exception as exc:
            return f"[OCR Error: {exc}]"

    def capture_screen_ocr(self) -> str:
        if self.is_linux:
            # Try Linux screenshot tools
            screenshot_path = self.tmp_dir / "screenshot.png"
            try:
                # Try gnome-screenshot first
                result = subprocess.run(
                    ["gnome-screenshot", "-f", str(screenshot_path)],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0 and screenshot_path.exists():
                    return self._ocr_image(screenshot_path)
            except FileNotFoundError:
                pass
            
            # Try scrot
            try:
                result = subprocess.run(
                    ["scrot", str(screenshot_path)],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0 and screenshot_path.exists():
                    return self._ocr_image(screenshot_path)
            except FileNotFoundError:
                pass
            
            # Try import (ImageMagick)
            try:
                result = subprocess.run(
                    ["import", "-window", "root", str(screenshot_path)],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0 and screenshot_path.exists():
                    return self._ocr_image(screenshot_path)
            except FileNotFoundError:
                pass
            
            return json.dumps({
                "action": "capture_screen_ocr",
                "ok": False,
                "error": "No Linux screenshot tool found. Install gnome-screenshot, scrot, or ImageMagick."
            }, indent=2)
        else:
            # Windows screenshot using PowerShell
            screenshot_path = self.tmp_dir / "screenshot.png"
            ps_script = f"""


Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('{screenshot_path}')
$graphics.Dispose()
$bitmap.Dispose()
"""
            result = self._run_native(
                ["powershell", "-NoProfile", "-Command", ps_script],
                timeout=30,
            )
            if result["returncode"] == 0 and screenshot_path.exists():
                return self._ocr_image(screenshot_path)
            return json.dumps({
                "action": "capture_screen_ocr",
                "ok": False,
                "error": result.get("stderr", "Screenshot failed")
            }, indent=2)

    def click(self, x: int, y: int) -> str:
        try:
            pyautogui.click(x, y)
            return json.dumps({"action": "click", "ok": True, "x": x, "y": y}, indent=2)
        except Exception as e:
            return json.dumps({"action": "click", "ok": False, "error": str(e)}, indent=2)

    def type_text(self, text: str) -> str:
        try:
            pyautogui.typewrite(text)
            return json.dumps({"action": "type_text", "ok": True, "text": text}, indent=2)
        except Exception as e:
            return json.dumps({"action": "type_text", "ok": False, "error": str(e)}, indent=2)

    def capture_active_window_ocr(self) -> str:
        if self.is_linux:
            return json.dumps({
                "action": "capture_active_window_ocr",
                "ok": False,
                "error": "Active window capture not implemented for Linux. Use capture_screen_ocr instead."
            }, indent=2)
        else:
            # Windows active window capture
            screenshot_path = self.tmp_dir / "active_window.png"
            script_path = Path(__file__).parent / "get_active_window.ps1"
            
            result = self._run_native(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path), "-ScreenshotPath", str(screenshot_path)],
                timeout=15
            )

            if result["returncode"] != 0:
                return json.dumps({
                    "action": "capture_active_window_ocr",
                    "ok": False,
                    "error": f"PowerShell script failed: {result['stderr']}"
                }, indent=2)
            if result["returncode"] == 0 and screenshot_path.exists():
                return self._ocr_image(screenshot_path)
            return json.dumps({
                "action": "capture_active_window_ocr",
                "ok": False,
                "error": result.get("stderr", "Active window capture failed")
            }, indent=2)

    # === ANONYMITY & STEALTH ===

    def stealth_status(self) -> str:
        return json.dumps({
            "chimera": self.chimera.status() if self.chimera else {"ok": False, "message": "Chimera not initialized"},
            "anonymity": self.anonymity.status(),
        }, indent=2)

    def stealth_on(self, tor: bool = False) -> str:
        if tor:
            result = self.anonymity.set_tor(True)
        else:
            result = self.anonymity.rotate_proxy()
        if self.chimera:
            self.chimera.mutate(intensity="high")
        return json.dumps({"action": "stealth_on", **result}, indent=2)

    def stealth_off(self) -> str:
        self.anonymity.set_tor(False)
        return json.dumps({"action": "stealth_off", "ok": True, "message": "Stealth disabled. Going direct."}, indent=2)

    def rotate_identity(self) -> str:
        if self.chimera:
            chimera_result = self.chimera.mutate(intensity="high")
        else:
            chimera_result = {"ok": False, "message": "Chimera not initialized"}

        proxy_result = self.anonymity.rotate_proxy()
        fingerprint = self.anonymity.generate_fingerprint()

        return json.dumps({
            "action": "rotate_identity",
            "ok": True,
            "chimera": chimera_result,
            "proxy": proxy_result,
            "new_fingerprint": fingerprint,
            "message": "New identity generated. Fingerprint rotated, proxy cycled.",
        }, indent=2)

    def check_ip_leaks(self) -> str:
        return json.dumps({
            "action": "check_ip_leaks",
            **self.anonymity.check_ip(),
        }, indent=2)

    # ── Forex Data ────────────────────────────────────────────────────────────

    def get_forex_data(self, pairs: str = "all") -> str:
        """Fetch live forex exchange rates from free API."""
        try:
            import urllib.request
            if pairs.lower() == "all":
                url = "https://open.er-api.com/v6/latest/USD"
            else:
                base = pairs.split("/")[0].strip().upper() if "/" in pairs else "USD"
                url = f"https://open.er-api.com/v6/latest/{base}"
            req = urllib.request.Request(url, headers={"User-Agent": "KaiAI/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if data.get("result") != "success":
                return json.dumps({"ok": False, "error": data.get("error-type", "API error")}, indent=2)
            rates = data.get("rates", {})
            timestamp = data.get("time_last_update_utc", "unknown")
            if pairs.lower() != "all":
                targets = [p.strip().upper() for p in pairs.split(",")]
                filtered = {}
                for t in targets:
                    if "/" in t:
                        _, quote = t.split("/", 1)
                    else:
                        quote = t
                    if quote in rates:
                        filtered[t] = rates[quote]
                    else:
                        filtered[t] = f"not found (available: USD, EUR, GBP, JPY, AUD, CAD, CHF, CNY, NZD, ...)"
                return json.dumps({
                    "ok": True, "base": data.get("base_code", "USD"),
                    "rates": filtered, "updated": timestamp
                }, indent=2)
            return json.dumps({
                "ok": True, "base": "USD", "rate_count": len(rates),
                "updated": timestamp,
                "rates": {k: rates[k] for k in list(rates.keys())[:50]},
                "note": f"Full data has {len(rates)} currencies. Shown first 50."
            }, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, indent=2)

    # ── SMS Gateway ───────────────────────────────────────────────────────────

    def send_sms(self, number: str, message: str) -> str:
        """Send SMS via email-to-carrier gateway. Tries multiple carriers."""
        # Known carrier email-to-SMS gateways
        gateways = {
            "verizon": "vtext.com",
            "att": "txt.att.net",
            "tmobile": "tmomail.net",
            "sprint": "messaging.sprintpcs.com",
            "cricket": "mms.cricketwireless.net",
            "googlefi": "msg.fi.google.com",
            "boost": "sms.myboostmobile.com",
            "uscellular": "email.uscc.net",
            "straighttalk": "vtext.com",
            "consumercellular": "mailmymobile.com",
            "xfinity": "vtext.com",
            "republic": "text.republicwireless.com",
            "tracfone": "mmst5.tracfone.com",
        }
        cleaned = number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
        results = []
        try:
            import smtplib
            from email.message import EmailMessage
            sender = "kai@localhost"
            for carrier, domain in gateways.items():
                to_addr = f"{cleaned}@{domain}"
                try:
                    msg = EmailMessage()
                    msg.set_content(message)
                    msg["Subject"] = ""
                    msg["From"] = sender
                    msg["To"] = to_addr
                    # Try localhost:25 (common if no SMTP auth needed)
                    with smtplib.SMTP("localhost", 25, timeout=5) as s:
                        s.send_message(msg)
                    results.append(f"Sent via {carrier} ({to_addr})")
                except (ConnectionRefusedError, OSError, smtplib.SMTPException):
                    # Try without SMTP server — write to file as fallback
                    pass
            if results:
                return json.dumps({"ok": True, "method": "email_gateway", "results": results, "note": "Tested all major carriers."}, indent=2)
            # Fallback: save SMS request to file
            sms_file = self.tmp_dir / f"sms_pending_{int(time.time())}.txt"
            with open(sms_file, "w") as f:
                f.write(f"TO: {number}\nMESSAGE: {message}\n")
            return json.dumps({
                "ok": True, "method": "saved",
                "file": str(sms_file),
                "note": "No SMTP server available. SMS request saved. Install a local SMTP (like hMailServer) or use ADB phone control."
            }, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, indent=2)

    # ── Grid Click ────────────────────────────────────────────────────────────

    def grid_click(self, x_pct: float, y_pct: float) -> str:
        """Click at percentage-based position on screen."""
        try:
            w, h = pyautogui.size()
            x = int(w * x_pct / 100)
            y = int(h * y_pct / 100)
            pyautogui.click(x, y)
            return json.dumps({"action": "grid_click", "ok": True, "x": x, "y": y, "x_pct": x_pct, "y_pct": y_pct}, indent=2)
        except Exception as e:
            return json.dumps({"action": "grid_click", "ok": False, "error": str(e)}, indent=2)

    # ── App Install ───────────────────────────────────────────────────────────

    def install_app(self, app_name: str) -> str:
        """Install an app via winget, choco, or direct download."""
        name = app_name.strip().lower()
        # Known app name mappings
        known = {
            "textnow": ("winget", "TextNow.TextNow"),
            "discord": ("winget", "Discord.Discord"),
            "firefox": ("winget", "Mozilla.Firefox"),
            "chrome": ("winget", "Google.Chrome"),
            "notepad++": ("winget", "Notepad++.Notepad++"),
            "7zip": ("winget", "7zip.7zip"),
            "python": ("winget", "Python.Python.3.12"),
            "git": ("winget", "Git.Git"),
            "vscode": ("winget", "Microsoft.VisualStudioCode"),
            "obsidian": ("winget", "Obsidian.Obsidian"),
            "telegram": ("winget", "Telegram.TelegramDesktop"),
            "whatsapp": ("winget", "WhatsApp.WhatsApp"),
            "signal": ("winget", "Signal.Signal"),
            "vlc": ("winget", "VideoLAN.VLC"),
            "spotify": ("winget", "Spotify.Spotify"),
        }
        if name in known:
            mgr, pkg = known[name]
            if mgr == "winget":
                try:
                    r = subprocess.run(
                        ["winget", "install", "--id", pkg, "--silent", "--accept-package-agreements"],
                        capture_output=True, text=True, timeout=120
                    )
                    if r.returncode == 0 or "success" in r.stdout.lower():
                        return json.dumps({"ok": True, "app": name, "method": "winget", "output": r.stdout[:500]}, indent=2)
                    return json.dumps({"ok": False, "app": name, "method": "winget", "error": r.stderr[:300]}, indent=2)
                except FileNotFoundError:
                    pass
                except subprocess.TimeoutExpired:
                    return json.dumps({"ok": False, "app": name, "method": "winget", "error": "winget timed out"})
            # Fallback to choco
            try:
                r = subprocess.run(
                    ["choco", "install", name, "-y"],
                    capture_output=True, text=True, timeout=120
                )
                if r.returncode == 0:
                    return json.dumps({"ok": True, "app": name, "method": "choco", "output": r.stdout[:500]}, indent=2)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        # Generic web search + download attempt
        try:
            import urllib.request
            search_url = f"https://api.duckduckgo.com/?q={name}+download+windows&format=json"
            req = urllib.request.Request(search_url, headers={"User-Agent": "KaiAI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass  # We'll just tell the user to download manually
        except Exception:
            pass
        return json.dumps({
            "ok": False, "app": name,
            "note": f"Could not auto-install '{name}'. Try: web_search for download page, then browser_open the URL."
        }, indent=2)
