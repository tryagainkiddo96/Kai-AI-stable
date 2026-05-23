"""Shell Tools — command classification and execution."""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

SUBPROCESS_TEXT_KWARGS = {"text": True, "encoding": "utf-8", "errors": "replace"}


class ShellTools:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"

    def classify_command(self, command: str) -> dict:
        lowered = command.strip().lower()
        tags: list[str] = []
        level = 3
        safe_prefixes = ["pwd", "ls", "dir", "whoami", "echo ", "cat ", "type ", "get-childitem", "get-content"]
        caution_terms = ["apt install", "pip install", "npm install", "winget install", "git clone", "curl ", "wget "]
        destructive_terms = ["rm ", "del ", "rmdir ", "format ", "shutdown", "reboot", "remove-item"]
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
        if any(term in lowered for term in ["curl ", "wget ", "nmap", "ping "]):
            tags.append("network-active")
        if not tags:
            tags.append("safe")
        return {"command": command, "tags": tags, "action_level": level, "confidence": tags[0], "requires_confirmation": level >= 4 or "destructive" in tags}

    def run_shell(self, command: str, timeout: int = 30) -> str:
        meta = self.classify_command(command)
        shell_args = ["powershell", "-NoProfile", "-Command", command] if self.is_windows else ["bash", "-c", command]
        try:
            completed = subprocess.run(shell_args, cwd=str(self.workspace), capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
            return json.dumps({
                "action": "run_shell", "command": command, "returncode": completed.returncode,
                "stdout": completed.stdout.strip()[:8000], "stderr": completed.stderr.strip()[:4000], **meta,
            }, indent=2)
        except subprocess.TimeoutExpired:
            return json.dumps({"action": "run_shell", "command": command, "returncode": -1, "stdout": "", "stderr": f"Command timed out after {timeout}s", **meta}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "run_shell", "command": command, "returncode": -1, "stdout": "", "stderr": f"Command failed: {exc}", **meta}, indent=2)

    @staticmethod
    def _clean_wsl_output(text: str) -> str:
        return text.replace("\x00", "").strip()[:8000]

    def run_wsl(self, command: str, timeout: int = 60, distro: str = "kali-linux") -> str:
        meta = self.classify_command(command)
        try:
            if self.is_linux:
                completed = subprocess.run(["bash", "-lc", command], cwd=str(self.workspace), capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
            else:
                completed = subprocess.run(["wsl.exe", "-d", distro, "--", "bash", "-lc", command], cwd=str(self.workspace), capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
            return json.dumps({
                "action": "run_wsl", "command": command, "distro": distro,
                "returncode": completed.returncode,
                "stdout": self._clean_wsl_output(completed.stdout),
                "stderr": self._clean_wsl_output(completed.stderr)[:4000], **meta,
            }, indent=2)
        except subprocess.TimeoutExpired:
            return json.dumps({"action": "run_wsl", "command": command, "distro": distro, "returncode": -1, "stdout": "", "stderr": f"WSL command timed out after {timeout}s", **meta}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "run_wsl", "command": command, "distro": distro, "returncode": -1, "stdout": "", "stderr": f"WSL command failed: {exc}", **meta}, indent=2)

    def run_native(self, args: list[str], timeout: int = 120, cwd: Path | None = None) -> dict:
        try:
            completed = subprocess.run(args, cwd=str(cwd or self.workspace), capture_output=True, timeout=timeout, **SUBPROCESS_TEXT_KWARGS)
            return {"command": args, "returncode": completed.returncode, "stdout": completed.stdout.strip()[:12000], "stderr": completed.stderr.strip()[:6000]}
        except subprocess.TimeoutExpired:
            return {"command": args, "returncode": -1, "stdout": "", "stderr": f"Command timed out after {timeout}s"}
        except Exception as exc:
            return {"command": args, "returncode": -1, "stdout": "", "stderr": f"Command failed: {exc}"}

    def ensure_command(self, command: str) -> tuple[bool, str]:
        candidates = {
            "git": ["git", "--version"],
            "python": ["python3", "--version"] if self.is_linux else ["python", "--version"],
        }
        if command in candidates:
            check = self.run_native(candidates[command], timeout=20)
            if check["returncode"] == 0:
                return True, f"{command} already available."
        return False, f"{command} not available."
