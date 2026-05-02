"""Cross-device sync for Kai (Git-backed command bus).

This is a minimal, safe utility to share commands/results between two machines
(Mac and Windows). It relies on a Git repo as a central bus. Both machines pull
commands from the remote, execute them via Kai, and push results back.

WARNING: This is a simple prototype intended for local, authorized usage. Do not
expose this over untrusted networks without proper authentication.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional


class CrossDeviceBus:
    def __init__(self, repo_url: str, local_dir: str):
        self.repo_url = repo_url
        self.local_dir = Path(local_dir).resolve()
        self._ensure_repo()

    def _ensure_repo(self) -> None:
        if not self.local_dir.exists():
            self.local_dir.mkdir(parents=True, exist_ok=True)
        if not (self.local_dir / ".git").exists():
            subprocess.run(["git", "init"], cwd=str(self.local_dir), check=False)
            subprocess.run(["git", "remote", "add", "origin", self.repo_url], cwd=str(self.local_dir), check=False)

    def pull(self) -> None:
        subprocess.run(["git", "pull", "origin", "main"], cwd=str(self.local_dir), check=False)

    def push(self) -> None:
        subprocess.run(["git", "add", "-A"], cwd=str(self.local_dir), check=False)
        subprocess.run(["git", "commit", "-m", "chore: sync cross-device bus"], cwd=str(self.local_dir), check=False)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(self.local_dir), check=False)

    def get_command(self) -> Optional[dict]:
        self.pull()
        cmd_file = self.local_dir / "shared" / "commands.json"
        if not cmd_file.exists():
            return None
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Expect a simple object with {"id": ..., "cmd": ...}
            return data
        except Exception:
            return None

    def mark_done(self, cmd_id: str, result: dict) -> None:
        cmd_file = self.local_dir / "shared" / "commands.json"
        if not cmd_file.exists():
            return
        # Load, update, and write a minimal history entry
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"id": cmd_id, "result": result}
        data = data if isinstance(data, dict) else {"id": cmd_id, "result": result}
        # Persist result to a simple results.json for visibility
        results_file = self.local_dir / "shared" / "results.json"
        if results_file.exists():
            try:
                with open(results_file, "r", encoding="utf-8") as rf:
                    existing = json.load(rf)
            except Exception:
                existing = []
        else:
            existing = []
        existing.append({"id": cmd_id, "result": result})
        with open(results_file, "w", encoding="utf-8") as rf:
            json.dump(existing, rf, indent=2)
        self.pull()
        self.push()
