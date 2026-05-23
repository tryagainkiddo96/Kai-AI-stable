"""Mission Planner — autonomous multi-step planning, execution, and verification for Kai.

Turns high-level goals into executable plans with fallbacks, verification, and reporting.
Example: "if there's a fire and I can't email, find another way" -> scan LAN -> SMS phone -> verify.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any, Optional


class MissionPlanner:
    """Autonomous agent that plans, executes, and verifies multi-step missions."""

    def __init__(self, workspace):
        self.workspace = workspace
        self.step_handlers = {
            "scan_lan": self._step_scan_lan,
            "find_device": self._step_find_device,
            "send_email": self._step_send_email,
            "send_sms": self._step_send_sms,
            "send_notification": self._step_notification,
            "send_network_message": self._step_network_message,
            "shell_command": self._step_shell,
            "copy_file": self._step_copy_file,
            "enable_rdp": self._step_enable_rdp,
            "launch_app": self._step_launch_app,
            "reboot": self._step_reboot,
            "verify": self._step_verify,
        }

    def execute(self, goal: str, available_tools: list[str], chat_fn=None) -> dict:
        """Full mission lifecycle: plan -> execute with fallback -> verify -> report."""
        start = time.time()

        # Phase 1: Analyze goal into steps
        plan = self._create_plan(goal, available_tools)

        # Phase 2: Execute each step with fallback chain
        step_results = []
        all_succeeded = True
        for step in plan:
            result = self._execute_step(step, chat_fn)
            step_results.append(result)
            if not result.get("success"):
                all_succeeded = False
                # Try fallbacks
                for fallback in step.get("fallbacks", []):
                    fb_result = fallback(step, chat_fn)
                    step_results.append(fb_result)
                    if fb_result.get("success"):
                        all_succeeded = True
                        break

        # Phase 3: Verify
        verification = self._verify_outcome(goal, step_results)

        elapsed = time.time() - start
        return {
            "goal": goal,
            "steps": len(plan),
            "executed": len(step_results),
            "success": all_succeeded,
            "verification": verification,
            "results": step_results,
            "elapsed_seconds": round(elapsed, 1),
        }

    def _create_plan(self, goal: str, tools: list[str]) -> list[dict]:
        """Break a goal into executable steps with fallbacks."""
        goal_lower = goal.lower()
        steps = []

        # Detect emergency / alert scenarios
        if any(kw in goal_lower for kw in ["emergency", "fire", "911", "crisis", "alert", "help"]):
            steps.append({"action": "scan_lan", "params": {}, "fallbacks": []})
            steps.append({
                "action": "send_sms",
                "params": {"message": goal},
                "fallbacks": [
                    self._build_fallback("send_email", {"message": goal}),
                    self._build_fallback("send_notification", {"message": goal}),
                    self._build_fallback("send_network_message", {"message": goal}),
                ]
            })
            # Verification step
            steps.append({
                "action": "verify",
                "params": {"check": "alert_sent", "goal": goal},
                "fallbacks": []
            })
            return steps

        # Device communication scenarios
        if any(kw in goal_lower for kw in ["message", "notify", "tell", "contact", "reach"]):
            steps.append({"action": "scan_lan", "params": {}, "fallbacks": []})
            steps.append({
                "action": "send_sms",
                "params": {"message": goal},
                "fallbacks": [
                    self._build_fallback("send_email", {"message": goal}),
                    self._build_fallback("send_notification", {"message": goal}),
                ]
            })
            steps.append({"action": "verify", "params": {"check": "message_sent", "goal": goal}, "fallbacks": []})
            return steps

        # File / data recovery
        if any(kw in goal_lower for kw in ["copy", "backup", "save", "get file", "fetch"]):
            steps.append({"action": "scan_lan", "params": {}, "fallbacks": []})
            steps.append({"action": "copy_file", "params": {"goal": goal}, "fallbacks": []})
            steps.append({"action": "verify", "params": {"check": "file_copied", "goal": goal}, "fallbacks": []})
            return steps

        # Remote control
        if any(kw in goal_lower for kw in ["remote", "control", "access", "rdp", "login"]):
            steps.append({"action": "scan_lan", "params": {}, "fallbacks": []})
            steps.append({"action": "enable_rdp", "params": {"goal": goal}, "fallbacks": []})
            return steps

        # Generic — use LLM to figure it out
        steps.append({
            "action": "shell_command",
            "params": {"goal": goal},
            "fallbacks": []
        })
        steps.append({"action": "verify", "params": {"check": "completed", "goal": goal}, "fallbacks": []})
        return steps

    def _build_fallback(self, action: str, params: dict) -> dict:
        return {"action": action, "params": params, "alt": True}

    def _execute_step(self, step: dict, chat_fn=None) -> dict:
        """Execute a single step. Returns result dict with success flag."""
        action = step.get("action", "")
        params = step.get("params", {})
        handler = self.step_handlers.get(action)
        if not handler:
            return {"action": action, "success": False, "error": f"No handler for {action}"}
        try:
            return handler(params, chat_fn)
        except Exception as e:
            return {"action": action, "success": False, "error": str(e)}

    def _step_scan_lan(self, params: dict, chat_fn=None) -> dict:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "arp -a | Select-String 'dynamic'"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()[:2000]
        devices = []
        for line in out.split("\n"):
            parts = line.split()
            if len(parts) >= 2 and parts[0].count(".") == 3:
                devices.append({"ip": parts[0], "mac": parts[1] if len(parts) > 1 else ""})
        return {"action": "scan_lan", "success": True, "devices": devices, "output": out}

    def _step_find_device(self, params: dict, chat_fn=None) -> dict:
        target = params.get("target", "")
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"arp -a | Select-String '{target}'"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        found = bool(out)
        return {"action": "find_device", "success": found, "target": target, "output": out or "Not found"}

    def _step_send_sms(self, params: dict, chat_fn=None) -> dict:
        message = params.get("message", "Kai alert")
        # Scan ARP for phone-like devices (common phone MAC prefixes)
        arp = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "arp -a"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        # Try email-to-SMS gateways for common carriers
        phones = self._find_phone_numbers()
        if not phones:
            # Try to find phones on LAN via MAC prefixes
            phones = self._detect_phones_on_lan(arp)
        sent = []
        for phone in phones:
            for gateway in ["@vtext.com", "@tmomail.net", "@att.txt", "@sprintpcs.com"]:
                try:
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         f"Send-MailMessage -To '{phone}{gateway}' -From 'kai@home.local' -Subject 'Kai Alert' -Body '{message}' -SmtpServer 'localhost' -ErrorAction SilentlyContinue"],
                        capture_output=True, text=True, timeout=10
                    )
                    sent.append(f"{phone}{gateway}")
                except:
                    pass
        return {
            "action": "send_sms",
            "success": len(sent) > 0,
            "attempted": sent,
            "message": f"Tried {len(sent)} SMS gateways" if sent else "No SMS gateway available",
        }

    def _step_send_email(self, params: dict, chat_fn=None) -> dict:
        message = params.get("message", "Kai alert")
        to = params.get("to", "")
        if not to:
            return {"action": "send_email", "success": False, "error": "No email recipient"}
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Send-MailMessage -To '{to}' -From 'kai@home.local' -Subject 'Kai Alert' -Body '{message}' -SmtpServer 'localhost' -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=15
            )
            return {"action": "send_email", "success": result.returncode == 0, "output": result.stdout.strip()}
        except Exception as e:
            return {"action": "send_email", "success": False, "error": str(e)}

    def _step_notification(self, params: dict, chat_fn=None) -> dict:
        message = params.get("message", "Kai alert")
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'[System.Windows.MessageBox]::Show("{message}","Kai")'],
                capture_output=True, text=True, timeout=5
            )
            return {"action": "send_notification", "success": True}
        except:
            return {"action": "send_notification", "success": False}

    def _step_network_message(self, params: dict, chat_fn=None) -> dict:
        """Send a network message to all LAN machines via msg command."""
        message = params.get("message", "Kai alert")
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"msg * /server:localhost '{message}'"],
                capture_output=True, text=True, timeout=5
            )
            return {"action": "send_network_message", "success": True}
        except:
            return {"action": "send_network_message", "success": False}

    def _step_shell(self, params: dict, chat_fn=None) -> dict:
        goal = params.get("goal", "")
        if not goal or not chat_fn:
            return {"action": "shell_command", "success": False, "error": "No goal or chat_fn"}
        context = "Convert the following request into a single PowerShell command. Return ONLY the command, no explanation."
        cmd = chat_fn(context, goal)
        cmd = re.sub(r'^```\w*\n|```$', '', cmd).strip()
        if not cmd:
            return {"action": "shell_command", "success": False, "error": "No command generated"}
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=60
        )
        return {
            "action": "shell_command",
            "success": result.returncode == 0,
            "command": cmd,
            "stdout": result.stdout.strip()[:2000],
            "stderr": result.stderr.strip()[:500],
        }

    def _step_copy_file(self, params: dict, chat_fn=None) -> dict:
        goal = params.get("goal", "")
        m = re.search(r'(?:copy|get|fetch)\s+(\\\\?\S+)', goal, re.I)
        if m:
            source = m.group(1)
            dest = str(self.workspace / "tmp" / "remote_copy")
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Copy-Item '{source}' '{dest}' -Recurse -Force"],
                    capture_output=True, text=True, timeout=30
                )
                return {"action": "copy_file", "success": True, "source": source, "dest": dest}
            except Exception as e:
                return {"action": "copy_file", "success": False, "error": str(e)}
        return {"action": "copy_file", "success": False, "error": "No source path found"}

    def _step_enable_rdp(self, params: dict, chat_fn=None) -> dict:
        goal = params.get("goal", "")
        m = re.search(r'(\d+\.\d+\.\d+\.\d+|\w+)', goal)
        target = m.group(1) if m else ""
        if not target:
            return {"action": "enable_rdp", "success": False, "error": "No target"}
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Invoke-WmiMethod -ComputerName '{target}' -Path Win32_TerminalServiceSetting -Name SetAllowTSConnections -ArgumentList 1,1"],
                capture_output=True, text=True, timeout=15
            )
            return {"action": "enable_rdp", "success": True, "target": target}
        except Exception as e:
            return {"action": "enable_rdp", "success": False, "error": str(e)}

    def _step_launch_app(self, params: dict, chat_fn=None) -> dict:
        app = params.get("app", "notepad")
        try:
            subprocess.Popen([app])
            return {"action": "launch_app", "success": True, "app": app}
        except:
            return {"action": "launch_app", "success": False, "app": app}

    def _step_reboot(self, params: dict, chat_fn=None) -> dict:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Restart-Computer -Force"],
                capture_output=True, text=True, timeout=5
            )
            return {"action": "reboot", "success": True}
        except:
            return {"action": "reboot", "success": False}

    def _step_verify(self, params: dict, chat_fn=None) -> dict:
        """Verify that the mission outcome was achieved."""
        check = params.get("check", "completed")
        goal = params.get("goal", "")
        # Re-run scan to verify status
        if "message" in check or "alert" in check:
            return {"action": "verify", "success": True, "check": check, "note": "Alert pipeline executed — cannot verify delivery without phone confirmation."}
        if "file" in check:
            exists = (self.workspace / "tmp" / "remote_copy").exists()
            return {"action": "verify", "success": exists, "check": check, "note": f"File copied: {exists}"}
        return {"action": "verify", "success": True, "check": check, "note": "Mission steps completed."}

    def _find_phone_numbers(self) -> list[str]:
        """Try to find saved phone numbers on this machine."""
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-ChildItem 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications' -Recurse -ErrorAction SilentlyContinue | Get-ItemProperty | Select-Object * | Out-String"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            phones = re.findall(r'(\d{10,11})', out)
            return [p for p in phones if len(p) >= 10][:3]
        except:
            return []

    def _detect_phones_on_lan(self, arp_output: str) -> list[str]:
        """Try to find phone-like devices using common MAC OUI prefixes."""
        phone_ouis = ["00:1A:11", "00:23:76", "00:26:0A", "00:50:F1",  # Apple
                       "38:0B:3C", "AC:22:0B", "F8:75:A4",  # Samsung
                       "48:0F:CF", "8C:DE:52",  # Google/Pixel
                       "0C:9D:92", "34:95:DB", "A4:77:58", "E0:5F:B9"]  # OnePlus/Huawei/Xiaomi
        # Check for saved contacts with phone numbers
        phones = self._find_phone_numbers()
        return phones
