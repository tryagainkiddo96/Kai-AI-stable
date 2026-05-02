"""File Tools — filesystem operations with policy gating."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from kai_agent.tools.shell_tools import ShellTools


class FileTools:
    def __init__(self, workspace: Path, shell_tools: ShellTools) -> None:
        self.workspace = workspace
        self.shell = shell_tools
        self.is_linux = shell_tools.is_linux

    def _resolve_path(self, raw_path: str) -> Path:
        raw_path = raw_path.strip().strip('"').strip("'")
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate
        return (self.workspace / candidate).resolve()

    def _policy_block(self, policy, action: str, **payload) -> str:
        decision = policy.evaluate(action, payload)
        policy.record(action, payload, decision)
        if decision.get("allowed", False):
            return ""
        return json.dumps({"action": action, "ok": False, "blocked": True, **decision}, indent=2)

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
            items = [f"{'dir' if item.is_dir() else 'file'}: {item.name}" for item in target.iterdir()]
            return "\n".join(items)
        except Exception as exc:
            return f"[Error listing {target}: {exc}]"

    def write_file(self, path: str, content: str, policy) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block(policy, "write_file", path=target, chars_written=len(content))
        if blocked:
            return blocked
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return json.dumps({"action": "write_file", "ok": True, "path": str(target), "chars_written": len(content)}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "write_file", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def append_file(self, path: str, content: str, policy) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block(policy, "append_file", path=target, chars_appended=len(content))
        if blocked:
            return blocked
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(content)
            return json.dumps({"action": "append_file", "ok": True, "path": str(target), "chars_appended": len(content)}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "append_file", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def replace_in_file(self, path: str, old_text: str, new_text: str, policy) -> str:
        target = self._resolve_path(path)
        blocked = self._policy_block(policy, "replace_in_file", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "replace_in_file", "ok": False, "error": "File not found."}, indent=2)
        try:
            original = target.read_text(encoding="utf-8", errors="replace")
            if old_text not in original:
                return json.dumps({"action": "replace_in_file", "ok": False, "error": "Target text not found."}, indent=2)
            target.write_text(original.replace(old_text, new_text, 1), encoding="utf-8")
            return json.dumps({"action": "replace_in_file", "ok": True, "path": str(target)}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "replace_in_file", "ok": False, "error": str(exc)}, indent=2)

    def open_path(self, path: str, policy) -> str:
        import os
        target = self._resolve_path(path)
        blocked = self._policy_block(policy, "open_path", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "open_path", "ok": False, "error": f"Path not found: {target}"}, indent=2)
        try:
            if self.shell.is_windows:
                os.startfile(str(target))
            else:
                subprocess.run(["xdg-open", str(target)], check=True, capture_output=True)
            return json.dumps({"action": "open_path", "ok": True, "path": str(target)}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "open_path", "ok": False, "path": str(target), "error": str(exc)}, indent=2)

    def clone_repo(self, repo_url: str, destination: str | None, policy) -> str:
        target = self._resolve_path(destination) if destination else (self.workspace / (Path(repo_url.rstrip("/")).stem or "repo"))
        blocked = self._policy_block(policy, "clone_repo", repo_url=repo_url, destination=target)
        if blocked:
            return blocked
        ok, msg = self.shell.ensure_command("git")
        if not ok:
            return json.dumps({"action": "clone_repo", "ok": False, "error": msg}, indent=2)
        result = self.shell.run_native(["git", "clone", repo_url, str(target)], timeout=1200)
        payload = {"action": "clone_repo", "repo_url": repo_url, "destination": str(target), "setup": msg, **result}
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def extract_zip(self, archive_path: str, destination: str | None, policy) -> str:
        archive = self._resolve_path(archive_path)
        if not archive.exists():
            return json.dumps({"action": "extract_zip", "ok": False, "error": f"Archive not found: {archive}"}, indent=2)
        target_dir = self._resolve_path(destination) if destination else archive.with_suffix("")
        blocked = self._policy_block(policy, "extract_zip", archive=archive, destination=target_dir)
        if blocked:
            return blocked
        target_dir.mkdir(parents=True, exist_ok=True)
        if self.is_linux:
            result = self.shell.run_native(["unzip", "-o", str(archive), "-d", str(target_dir)], timeout=600)
        else:
            result = self.shell.run_native(["powershell", "-NoProfile", "-Command", f"Expand-Archive -LiteralPath '{archive}' -DestinationPath '{target_dir}' -Force"], timeout=600)
        payload = {"action": "extract_zip", "archive": str(archive), "destination": str(target_dir), **result}
        payload["ok"] = result["returncode"] == 0
        return json.dumps(payload, indent=2)

    def install_project(self, target_path: str, policy) -> str:
        target = self._resolve_path(target_path)
        blocked = self._policy_block(policy, "install_project", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "install_project", "ok": False, "error": f"Project not found: {target}"}, indent=2)
        steps: list[dict] = []
        if (target / "requirements.txt").exists():
            ok, msg = self.shell.ensure_command("python")
            steps.append({"tool": "python", "setup": msg})
            if ok:
                cmd = ["python3", "-m", "pip", "install", "-r", "requirements.txt"] if self.is_linux else ["python", "-m", "pip", "install", "-r", "requirements.txt"]
                steps.append(self.shell.run_native(cmd, cwd=target, timeout=1800))
        if not steps:
            return json.dumps({"action": "install_project", "ok": False, "error": "No requirements.txt found."}, indent=2)
        ok = any(isinstance(s, dict) and s.get("returncode") == 0 for s in steps)
        return json.dumps({"action": "install_project", "path": str(target), "ok": ok, "steps": steps}, indent=2)

    def run_tests(self, target_path: str, policy) -> str:
        target = self._resolve_path(target_path)
        blocked = self._policy_block(policy, "run_tests", path=target)
        if blocked:
            return blocked
        if not target.exists():
            return json.dumps({"action": "run_tests", "ok": False, "error": f"Path not found: {target}"}, indent=2)
        for candidate in (["python", "-m", "pytest"], ["python3", "-m", "pytest"]):
            check = self.shell.run_native(candidate[:1] + ["--version"], timeout=10)
            if check["returncode"] == 0:
                result = self.shell.run_native(candidate, cwd=target, timeout=600)
                payload = {"action": "run_tests", "path": str(target), "runner": " ".join(candidate), **result}
                payload["ok"] = result["returncode"] == 0
                return json.dumps(payload, indent=2)
        return json.dumps({"action": "run_tests", "ok": False, "error": "pytest not found."}, indent=2)
