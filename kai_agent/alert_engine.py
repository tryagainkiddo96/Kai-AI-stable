"""Alert Engine — rule-based triggers for notifications and actions.

Rules match events to actions:
  Event types: idle_detect, error_count, new_device, time_of_day, traffic_spike
  Action types: notify_phone, send_toast, run_command, log_event

Rules are stored in CTOS DB and evaluated on each event registration.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Optional


class AlertEngine:
    """Rule-based alerting engine with event matching."""

    def __init__(self, db, notify_fn: Callable = None):
        self.db = db
        self._notify = notify_fn or (lambda m, p="normal", t="Kai": None)
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._event_buffer: list[dict] = []
        self._buffer_lock = threading.Lock()
        self._last_triggers: dict[str, float] = {}  # cooldown tracking

    def start(self):
        if self._enabled:
            return
        self._enabled = True

    def stop(self):
        self._enabled = False

    def register_event(self, event_type: str, data: dict = None):
        """Register an event and evaluate against all rules."""
        if not self._enabled:
            return

        with self._buffer_lock:
            self._event_buffer.append({
                "type": event_type,
                "data": data or {},
                "time": time.time(),
            })
            if len(self._event_buffer) > 500:
                self._event_buffer = self._event_buffer[-500:]

        self._evaluate_rules(event_type, data or {})

    def _evaluate_rules(self, event_type: str, data: dict):
        rules = self.db.get_alert_rules(enabled_only=True)
        for rule in rules:
            if rule["event_type"] != event_type and rule["event_type"] != "*":
                continue

            params = rule.get("params", {})
            cooldown_key = rule["name"]
            now = time.time()

            # Check cooldown
            min_interval = params.get("cooldown", 0)
            if min_interval > 0:
                last = self._last_triggers.get(cooldown_key, 0)
                if now - last < min_interval:
                    continue

            # Evaluate condition
            if not self._evaluate_condition(params.get("condition", {}), data):
                continue

            # Execute action
            self._execute_action(rule["action_type"], rule["name"], params, data)
            self._last_triggers[cooldown_key] = now

    def _evaluate_condition(self, condition: dict, data: dict) -> bool:
        if not condition:
            return True

        field = condition.get("field", "")
        op = condition.get("op", "eq")
        value = condition.get("value")

        actual = data.get(field)
        if actual is None:
            return False

        if op == "eq":
            return actual == value
        elif op == "gt":
            return actual > (value or 0)
        elif op == "lt":
            return actual < (value or 0)
        elif op == "gte":
            return actual >= (value or 0)
        elif op == "lte":
            return actual <= (value or 0)
        elif op == "contains":
            return str(value or "").lower() in str(actual).lower()
        return True

    def _execute_action(self, action_type: str, rule_name: str, params: dict, data: dict):
        fmt_data = {k: str(v)[:100] for k, v in data.items()}
        if "uptime" not in fmt_data:
            fmt_data["uptime"] = self._get_uptime()
        message = params.get("message", "").format(**fmt_data)
        priority = params.get("priority", "normal")
        title = params.get("title", f"Kai Alert: {rule_name}")

        if action_type == "notify_phone":
            if self._notify:
                self._notify(message, priority=priority, title=title)

        elif action_type == "notify_all":
            if self._notify:
                self._notify(message, priority=priority, title=title)

        elif action_type == "log_only":
            if self.db:
                self.db.journal_entry("alert", {
                    "rule": rule_name, "message": message[:200], "data": data
                }, source="alert_engine", importance=1)

    @staticmethod
    def _get_uptime() -> str:
        try:
            import subprocess as sp
            r = sp.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"],
                       capture_output=True, text=True, timeout=5)
            boot_str = r.stdout.strip()
            if boot_str:
                from datetime import datetime
                boot = datetime.strptime(boot_str.split(".")[0], "%Y%m%d%H%M%S")
                delta = datetime.now() - boot
                h, rem = divmod(int(delta.total_seconds()), 3600)
                m = rem // 60
                return f"{h}h {m}m"
        except Exception:
            pass
        return "unknown"

        # action_type can be extended with more handlers

    # ── Pre-built Rules ──────────────────────────────────────────────────────

    def add_default_rules(self):
        """Seed some useful alert rules."""
        defaults = [
            {
                "name": "Idle Alert",
                "event_type": "idle_detect",
                "action_type": "notify_phone",
                "params": {
                    "message": "Kai here — you've been away from keyboard for 15+ minutes. Everything is running smoothly.",
                    "priority": "normal",
                    "title": "Kai Status",
                    "cooldown": 900,
                },
            },
            {
                "name": "New Device Alert",
                "event_type": "new_device",
                "action_type": "notify_all",
                "params": {
                    "message": "New device detected on network! IP: {ip}, MAC: {mac}",
                    "priority": "high",
                    "title": "Network Alert",
                    "cooldown": 60,
                },
            },
            {
                "name": "Daily Digest",
                "event_type": "time_of_day",
                "action_type": "notify_phone",
                "params": {
                    "message": "Daily digest ready. Your system has been running for {uptime}.",
                    "priority": "normal",
                    "title": "Kai Daily",
                    "cooldown": 86400,
                    "condition": {"field": "hour", "op": "eq", "value": 20},
                },
            },
        ]
        for rule in defaults:
            self.db.save_alert_rule(
                rule["name"], rule["event_type"],
                rule["action_type"], rule["params"],
            )

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        with self._buffer_lock:
            return list(self._event_buffer[-limit:])
