"""
Kai Swarm — Multi-agent parallel execution on top of Legion.
"""
from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from kai_agent.legion_chimera import LegionController


class SwarmTask:
    def __init__(self, task_id: str, description: str, prompt: str, status: str = "pending") -> None:
        self.id = task_id
        self.description = description
        self.prompt = prompt
        self.status = status
        self.result = ""
        self.error = ""
        self.started_at = ""
        self.finished_at = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "prompt": self.prompt,
            "status": self.status,
            "result": self.result[:2000],
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class SwarmController:
    """Manages parallel multi-agent task execution."""

    def __init__(self, assistant, legion: LegionController, max_workers: int = 5) -> None:
        self.assistant = assistant
        self.legion = legion
        self.max_workers = max_workers
        self._lock = threading.Lock()
        self.tasks: dict[str, SwarmTask] = {}
        self._executor: ThreadPoolExecutor | None = None
        self._callbacks: list = []
        self.running = False
        self._current_run_id = ""

    def add_callback(self, fn):
        self._callbacks.append(fn)

    def _notify(self, message):
        for cb in self._callbacks:
            try:
                cb(message)
            except Exception:
                pass

    def create_swarm(self, tasks: list[dict[str, str]]) -> str:
        """Create a swarm of parallel tasks."""
        run_id = f"swarm_{uuid.uuid4().hex[:8]}"
        self._current_run_id = run_id

        for t in tasks:
            task_id = f"{run_id}_{uuid.uuid4().hex[:6]}"
            task = SwarmTask(
                task_id=task_id,
                description=t.get("description", t.get("prompt", "")),
                prompt=t["prompt"],
            )
            with self._lock:
                self.tasks[task_id] = task

        self._notify(f"🐝 Swarm '{run_id}' created with {len(tasks)} agents.")
        return run_id

    def execute_swarm(self, run_id: str) -> None:
        """Execute all tasks in the swarm in parallel."""
        def _run_task(task: SwarmTask):
            task.status = "running"
            task.started_at = datetime.now().isoformat()
            self._notify(f"  ▶ Agent {task.id[:20]}: {task.description}")
            try:
                result = self.assistant.ask_sync(task.prompt)
                task.result = result
                task.status = "done"
                self._notify(f"  ✓ Agent {task.id[:20]}: Done")
            except Exception as exc:
                task.error = str(exc)
                task.status = "error"
                self._notify(f"  ✗ Agent {task.id[:20]}: {exc}")
            finally:
                task.finished_at = datetime.now().isoformat()

        run_tasks = [t for t in self.tasks.values() if t.id.startswith(run_id)]
        self.running = True

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(_run_task, t): t for t in run_tasks}
            for future in as_completed(futures):
                pass  # Tasks self-report via callbacks

        self.running = False
        self._notify(f"✅ Swarm '{run_id}' complete. {sum(1 for t in run_tasks if t.status == 'done')} succeeded, {sum(1 for t in run_tasks if t.status == 'error')} failed.")

    def get_results(self, run_id: str) -> list[dict]:
        return [t.to_dict() for t in self.tasks.values() if t.id.startswith(run_id)]

    def get_all_tasks(self) -> list[dict]:
        return [t.to_dict() for t in self.tasks.values()]

    def merge_results(self, run_id: str) -> str:
        """Merge all swarm results into a single report."""
        results = self.get_results(run_id)
        done = [r for r in results if r["status"] == "done"]
        errors = [r for r in results if r["status"] == "error"]

        report = f"# Swarm Report: {run_id}\n\n"
        report += f"Total agents: {len(results)}\n"
        report += f"Succeeded: {len(done)}\n"
        report += f"Failed: {len(errors)}\n\n"

        for r in done:
            report += f"## {r['description']}\n\n{r['result']}\n\n---\n\n"

        for r in errors:
            report += f"## ❌ {r['description']} — Error: {r['error']}\n\n---\n\n"

        return report

    def status(self) -> dict:
        total = len(self.tasks)
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        done = sum(1 for t in self.tasks.values() if t.status == "done")
        errors = sum(1 for t in self.tasks.values() if t.status == "error")
        return {
            "running": self.running,
            "total_tasks": total,
            "running_tasks": running,
            "done_tasks": done,
            "error_tasks": errors,
            "current_run": self._current_run_id,
        }
