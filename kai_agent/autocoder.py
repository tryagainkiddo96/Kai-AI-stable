"""
Kai Autocoder — Autonomous coding loop: issue → code → test → fix → commit.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path


class Autocoder:
    """Full autonomous coding loop. Give it a task, it handles the rest."""

    def __init__(self, assistant, workspace: Path, require_approval: bool = True) -> None:
        self.assistant = assistant
        self.workspace = workspace
        self.running = False
        self._thread: threading.Thread | None = None
        self._callbacks: list = []
        self.current_task = ""
        self.steps: list[dict] = []
        self.status_msg = "idle"
        self.require_approval = require_approval
        self._pending_changes: list[dict] = []
        self._approved = False
        self._approval_event = threading.Event()
        self.dry_run = False

        # LSP integration (lazy)
        self._lsp_manager = None
        self._init_lsp()

    def add_callback(self, fn):
        self._callbacks.append(fn)

    def _init_lsp(self):
        """Lazy-load LSP manager for IDE-aware refactoring."""
        try:
            from kai_agent.lsp_client import LSPManager
            self._lsp_manager = LSPManager(self.workspace)
        except Exception:
            pass

    def _lsp_check_file(self, filepath: str) -> list[dict]:
        """Check a file for LSP diagnostics (errors, warnings)."""
        if not self._lsp_manager:
            return []
        try:
            client = self._lsp_manager.find_language_for_file(filepath)
            if client:
                diags = client.get_diagnostics(filepath)
                return [d.to_dict() for d in diags if d.severity in (1, 2)]  # errors + warnings
        except Exception:
            pass
        return []

    def _lsp_rename_symbol(self, filepath: str, line: int, col: int, new_name: str) -> dict:
        """Perform LSP-aware rename refactoring and apply to files."""
        if not self._lsp_manager:
            return {"changes": [], "error": "LSP not available"}
        try:
            client = self._lsp_manager.find_language_for_file(filepath)
            if not client:
                return {"changes": [], "error": f"No language server for {filepath}"}
            result = client.rename(filepath, line, col, new_name)
            # Apply the workspace edits
            applied = 0
            for change in result.get("changes", []):
                uri = change.get("uri", "")
                edits = change.get("edits", [])
                if edits:
                    # Convert URI to file path
                    if uri.startswith("file:///"):
                        file_path = uri[8:]
                    else:
                        file_path = uri
                    try:
                        p = Path(file_path)
                        if p.exists():
                            content = p.read_text(encoding="utf-8")
                            # Apply edits in reverse order to preserve positions
                            for edit in sorted(edits, key=lambda e: (e.get("range", {}).get("start", {}).get("line", 0), e.get("range", {}).get("start", {}).get("character", 0)), reverse=True):
                                rng = edit.get("range", {})
                                start_line = rng.get("start", {}).get("line", 0)
                                start_char = rng.get("start", {}).get("character", 0)
                                end_line = rng.get("end", {}).get("line", 0)
                                end_char = rng.get("end", {}).get("character", 0)
                                new_text = edit.get("newText", "")
                                lines = content.split("\n")
                                if start_line == end_line:
                                    lines[start_line] = lines[start_line][:start_char] + new_text + lines[start_line][end_char:]
                                else:
                                    # Multi-line replacement (simplified)
                                    lines[start_line] = lines[start_line][:start_char] + new_text + lines[end_line][end_char:]
                                    del lines[start_line + 1:end_line + 1]
                                content = "\n".join(lines)
                            p.write_text(content, encoding="utf-8")
                            applied += 1
                            self._notify(f"  ✓ LSP rename applied: {p.name}")
                    except Exception as exc:
                        self._notify(f"  ✗ Failed to apply rename to {file_path}: {exc}")
            return {"changes_applied": applied, "total_changes": len(result.get("changes", []))}
        except Exception as exc:
            return {"error": str(exc)}

    def lsp_rename(self, filepath: str, line: int, col: int, new_name: str) -> str:
        """Public method: rename a symbol across the project using LSP."""
        result = self._lsp_rename_symbol(filepath, line, col, new_name)
        if "error" in result:
            return f"LSP rename failed: {result['error']}"
        return f"LSP rename complete: {result.get('changes_applied', 0)}/{result.get('total_changes', 0)} files updated."

    def lsp_validate_changes(self, changes: list[dict]) -> list[dict]:
        """Run LSP diagnostics on changed files to catch errors before saving."""
        issues = []
        for ch in changes:
            filepath = ch.get("filepath", "")
            content = ch.get("content", "")
            target = self.workspace / filepath
            try:
                # Temporarily write the file so LSP can analyze it
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                diags = self._lsp_check_file(filepath)
                if diags:
                    for d in diags[:5]:
                        issues.append({
                            "file": filepath,
                            "line": d.get("line", 0),
                            "severity": "error" if d.get("severity") == 1 else "warning",
                            "message": d.get("message", ""),
                        })
            except Exception:
                pass
        return issues

    def _notify(self, message, step=None):
        entry = {"step": step or len(self.steps), "message": message, "timestamp": datetime.now().isoformat()}
        self.steps.append(entry)
        for cb in self._callbacks:
            try:
                cb(message)
            except Exception:
                pass

    def start_task(self, task_description: str) -> None:
        if self.running:
            self._notify("⚠️ Already running a task. Use /autocoder stop first.")
            return
        self.current_task = task_description
        self.steps.clear()
        self.running = True
        self.status_msg = "starting"
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.status_msg = "stopped"
        if self._thread:
            self._thread.join(timeout=30)
            self._thread = None

    def _ask(self, prompt: str) -> str:
        return self.assistant.ask_sync(prompt)

    def _run_shell(self, cmd: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                cwd=str(self.workspace), capture_output=True,
                text=True, timeout=timeout, encoding="utf-8", errors="replace")
            return result.stdout + result.stderr
        except Exception as exc:
            return f"Shell error: {exc}"

    def _run_loop(self):
        self._notify(f"🚀 Starting autonomous coding task:\n{self.current_task}")
        self.status_msg = "analyzing"

        # Step 1: Analyze the task
        self._notify("📋 Step 1: Analyzing task...")
        analysis = self._ask(
            f"Analyze this coding task and return a structured plan:\n{self.current_task}\n\n"
            "Return: 1) Files to modify/create 2) Specific changes needed 3) Commands to run 4) Tests to verify"
        )
        self._notify(f"📋 Plan:\n{analysis}")

        # Step 2: Read relevant files
        self._notify("📖 Step 2: Reading relevant files...")
        self.status_msg = "reading"

        # Extract file paths from analysis
        file_pattern = r'[\w./\\-]+\.(?:py|js|ts|jsx|tsx|go|rs|rb|html|css|json|toml|yaml|yml|md|sh|ps1)'
        files = re.findall(file_pattern, analysis)
        files = list(set(files))[:10]  # Deduplicate, limit to 10

        file_contexts = []
        for f in files:
            path = self.workspace / f
            if path.exists():
                content = path.read_text(encoding="utf-8", errors="replace")[:3000]
                file_contexts.append(f"## {f}\n{content}")
                self._notify(f"  ✓ Read {f}")

        # Step 3: Generate and apply code
        self._notify("💻 Step 3: Generating code changes...")
        self.status_msg = "coding"

        code_prompt = (
            f"Based on this task: {self.current_task}\n\n"
            f"Plan:\n{analysis}\n\n"
            f"Relevant files:\n" + "\n---\n".join(file_contexts[:5]) + "\n\n"
            "Make the necessary changes. For each file:\n"
            "1. Show the full updated file content\n"
            "2. Include a marker '```SAVE:<filepath>' before each file\n\n"
            "Be precise and complete."
        )

        code_response = self._ask(code_prompt)
        self._notify(f"💻 Code generated ({len(code_response)} chars)")

        # Step 3b: LSP pre-flight validation
        save_pattern = r'```SAVE:([\w./\\-]+)\s*```\s*\n?([\s\S]*?)(?=```SAVE:|$)'
        saves = re.findall(save_pattern, code_response)
        if self._lsp_manager and saves:
            self._notify("🔍 Step 3b: LSP pre-flight validation...")
            self.status_msg = "validating"
            preflight_changes = []
            for filepath, content in saves:
                filepath = filepath.strip()
                code_block = re.search(r'```[\w]*\n([\s\S]*?)```', content)
                preflight_changes.append({
                    "filepath": filepath,
                    "content": code_block.group(1) if code_block else content,
                })
            lsp_issues = self.lsp_validate_changes(preflight_changes)
            if lsp_issues:
                issue_summary = "\n".join(
                    f"  [{i['severity']}] {i['file']}:{i['line']} — {i['message'][:100]}"
                    for i in lsp_issues[:10]
                )
                self._notify(f"⚠️ LSP found {len(lsp_issues)} issue(s):\n{issue_summary}")
                # Feed issues back to LLM for self-correction
                fix_prompt = (
                    f"LSP diagnostics found these issues in the generated code:\n{issue_summary}\n\n"
                    "Fix all errors and re-generate the corrected files with ```SAVE:<filepath> markers."
                )
                fix_response = self._ask(fix_prompt)
                if "```SAVE:" in fix_response:
                    code_response = fix_response
                    saves = re.findall(save_pattern, code_response)
                    self._notify("✓ LSP issues addressed, code regenerated.")
            else:
                self._notify("✓ LSP validation passed — no errors.")

        # Step 4: Extract and prepare changes for approval
        self._notify("💾 Step 4: Preparing file changes...")
        self.status_msg = "awaiting_approval"

        self._pending_changes.clear()
        self._approved = False

        for filepath, content in saves:
            filepath = filepath.strip()
            target = self.workspace / filepath
            # Extract code between markdown fences if present
            code_block = re.search(r'```[\w]*\n([\s\S]*?)```', content)
            if code_block:
                content = code_block.group(1)

            change = {
                "filepath": filepath,
                "content": content,
                "target": str(target),
                "exists": target.exists(),
            }
            if change["exists"]:
                try:
                    change["original"] = target.read_text(encoding="utf-8", errors="replace")[:500]
                except Exception:
                    change["original"] = "(could not read)"
            self._pending_changes.append(change)

        if self._pending_changes:
            preview = f"📝 {len(self._pending_changes)} file change(s) ready:\n"
            for ch in self._pending_changes:
                action = "CREATE" if not ch["exists"] else "MODIFY"
                preview += f"  [{action}] {ch['filepath']} ({len(ch['content'])} chars)\n"

            if self.dry_run:
                preview += "\n(DRY RUN — no files will be written)"
                self._notify(preview)
                self._approved = True  # Auto-approve in dry run
            elif self.require_approval:
                preview += "\n⏸️ Waiting for approval. Click Approve in dashboard or run: /autocoder approve"
                self._notify(preview)
                self._approval_event.clear()
                self._approval_event.wait(timeout=300)  # Wait up to 5 minutes
                if not self._approved:
                    self._notify("⏹️ Approval timeout or rejected. Skipping file saves.")
                    self._pending_changes.clear()
            else:
                self._notify(preview + "\n(Auto-approved — saving changes)")
                self._approved = True
        else:
            self._notify("No explicit SAVE markers found.")

        # Step 4b: Apply approved changes
        saved_count = 0
        if self._approved and not self.dry_run:
            self._notify("💾 Applying changes...")
            self.status_msg = "saving"
            for ch in self._pending_changes:
                target = self.workspace / ch["filepath"]
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(ch["content"], encoding="utf-8")
                    saved_count += 1
                    self._notify(f"  ✓ Saved {ch['filepath']}")
                except Exception as exc:
                    self._notify(f"  ✗ Failed to save {ch['filepath']}: {exc}")
            self._pending_changes.clear()
        elif self.dry_run:
            self._notify("💾 Dry run complete — no files were written.")
            self._pending_changes.clear()

        # Step 5: Run tests / verification
        self._notify("🧪 Step 5: Running verification...")
        self.status_msg = "testing"

        test_output = ""
        # Try common test commands
        test_cmds = [
            "python -m pytest --tb=short -q 2>&1",
            "python run_all_tests.py 2>&1",
            "npm test 2>&1",
            "cargo test 2>&1",
        ]
        for cmd in test_cmds:
            output = self._run_shell(cmd, timeout=60)
            if "not found" not in output.lower() and output.strip():
                test_output = output[:2000]
                self._notify(f"🧪 Test output:\n{test_output[:500]}")
                break

        # Step 6: Fix errors if any
        if any(kw in test_output.lower() for kw in ["failed", "error", "exception", "traceback"]):
            self._notify("⚠️ Tests failed. Attempting to fix...")
            self.status_msg = "fixing"

            fix_prompt = (
                f"The task was: {self.current_task}\n\n"
                f"Test output shows errors:\n{test_output[:1500]}\n\n"
                "Fix the errors and show the corrected file content with ```SAVE:<filepath> markers."
            )
            fix_response = self._ask(fix_prompt)

            # Save fixes
            for filepath, content in re.findall(save_pattern, fix_response):
                filepath = filepath.strip()
                target = self.workspace / filepath
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    code_block = re.search(r'```[\w]*\n([\s\S]*?)```', content)
                    if code_block:
                        content = code_block.group(1)
                    target.write_text(content, encoding="utf-8")
                    self._notify(f"  ✓ Fixed and saved {filepath}")
                except Exception as exc:
                    self._notify(f"  ✗ Fix failed for {filepath}: {exc}")

        # Step 7: Commit
        self._notify("📦 Step 7: Creating git commit...")
        self.status_msg = "committing"

        commit_status = self._run_shell("git status --short")
        if commit_status.strip():
            self._run_shell("git add -A")
            commit_msg = self._ask(
                f"Based on this task: {self.current_task}\n"
                "Write a concise, descriptive git commit message (one line)."
            ).strip()
            self._run_shell(f'git commit -m "{commit_msg}"')
            self._notify(f"📦 Committed: {commit_msg}")
        else:
            self._notify("📦 No changes to commit (already tracked or no modifications).")

        # Done
        self.running = False
        self.status_msg = "done"
        self._notify(f"✅ Task complete: {self.current_task}")

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "current_task": self.current_task,
            "status_msg": self.status_msg,
            "steps": self.steps[-20:],  # Last 20 steps
            "total_steps": len(self.steps),
            "pending_changes": [
                {"filepath": ch["filepath"], "exists": ch["exists"], "size": len(ch["content"])}
                for ch in self._pending_changes
            ],
            "require_approval": self.require_approval,
            "dry_run": self.dry_run,
        }

    def approve_changes(self) -> bool:
        """Approve pending file changes."""
        if not self._pending_changes:
            return False
        self._approved = True
        self._approval_event.set()
        self._notify(f"✅ Approved {len(self._pending_changes)} change(s). Applying...")
        return True

    def reject_changes(self) -> bool:
        """Reject pending file changes."""
        if not self._pending_changes:
            return False
        self._approved = False
        self._approval_event.set()
        count = len(self._pending_changes)
        self._pending_changes.clear()
        self._notify(f"⏹️ Rejected {count} change(s).")
        return True
