import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from kai_agent.assistant import KaiAssistant
from kai_agent.bridge_auth import KaiBridgeAuth
from kai_agent.desktop_tools import TESSERACT_PATH
from kai_agent.environment import EnvironmentMonitor


ROOT = Path(__file__).resolve().parents[1]
WIDGET_DIR = ROOT / "widget"
CHAT_TIMEOUT_SECONDS = int(os.environ.get("KAI_CHAT_TIMEOUT", "45"))
STATIC_FILES = {
    "/": ("kai-unified-dashboard.html", "text/html; charset=utf-8"),
    "/dashboard": ("kai-unified-dashboard.html", "text/html; charset=utf-8"),
    "/dashboard-creative": ("kai-dashboard-creative.html", "text/html; charset=utf-8"),
    "/dashboard-professional": ("kai-dashboard-professional.html", "text/html; charset=utf-8"),
    "/dashboard-offwall": ("kai-dashboard-offwall.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/kai-dashboard.html": ("kai-dashboard.html", "text/html; charset=utf-8"),
    "/kai-dashboard-creative.html": ("kai-dashboard-creative.html", "text/html; charset=utf-8"),
    "/kai-dashboard-professional.html": ("kai-dashboard-professional.html", "text/html; charset=utf-8"),
    "/kai-dashboard-offwall.html": ("kai-dashboard-offwall.html", "text/html; charset=utf-8"),
    "/kai-unified-dashboard.html": ("kai-unified-dashboard.html", "text/html; charset=utf-8"),
    "/command-center": ("kai-command-center.html", "text/html; charset=utf-8"),
    "/kai-command-center.html": ("kai-command-center.html", "text/html; charset=utf-8"),
    "/soul": ("kai-soul-portal.html", "text/html; charset=utf-8"),
    "/kai-soul-portal.html": ("kai-soul-portal.html", "text/html; charset=utf-8"),
    "/portal": ("kai-soul-portal.html", "text/html; charset=utf-8"),
    "/lab": ("kai-pentesting-lab.html", "text/html; charset=utf-8"),
    "/pentesting": ("kai-pentesting-lab.html", "text/html; charset=utf-8"),
    "/kai-pentesting-lab.html": ("kai-pentesting-lab.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/claude-tab-styles.css": ("claude-tab-styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/claude-tab.js": ("claude-tab.js", "application/javascript; charset=utf-8"),
    "/sw.js": ("sw.js", "application/javascript; charset=utf-8"),
    "/manifest.json": ("manifest.json", "application/json"),
    "/favicon.ico": ("favicon.svg", "image/svg+xml"),
    "/kai-logo.svg": ("kai-logo.svg", "image/svg+xml"),
    "/paw.svg": ("paw.svg", "image/svg+xml"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


class KaiWidgetServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, assistant: KaiAssistant) -> None:
        super().__init__(server_address, handler_class)
        self.assistant = assistant
        self.auth = KaiBridgeAuth(save_path=assistant.workspace / "memory" / "devices.json")
        self.environment = EnvironmentMonitor(save_path=assistant.workspace / "memory" / "environment.json")
        self.pending_messages: list[dict] = []  # Proactive messages waiting for widget
        # Response caching for expensive operations
        self._status_cache: dict = {}
        self._status_cache_time: float = 0
        self._status_cache_ttl: float = 1  # 1 second cache
        self._mood_cache: dict = {}
        self._mood_cache_time: float = 0
        self._mood_cache_ttl: float = 0.5  # 0.5 second cache


class Handler(BaseHTTPRequestHandler):
    server: KaiWidgetServer

    def _json_load(self, raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "raw": raw}

    def _stable_angle(self, label: str) -> float:
        digest = hashlib.sha256(label.encode("utf-8", errors="ignore")).hexdigest()
        seed = int(digest[:8], 16)
        return (seed % 360) * (math.pi / 180.0)

    def _estimate_distance_meters(self, strength: float) -> float:
        # Heuristic only: stronger signal -> closer. Clamp to a small room / home-scale map.
        strength = max(1.0, min(100.0, strength))
        return round(max(1.0, min(30.0, 35.0 - (strength * 0.32))), 1)

    def _signal_map(self) -> dict:
        assistant = self.server.assistant
        wifi = assistant.signals.scan_wifi()
        bluetooth = assistant.signals.scan_bluetooth()
        current_wifi = assistant.signals.get_current_wifi()
        current_link = assistant.signals.get_current_link_insights()

        nodes: list[dict] = []
        spectrum = {
            "radio_2_4ghz": 0,
            "radio_5ghz": 0,
            "radio_6ghz": 0,
            "bluetooth_devices": int(bluetooth.get("count", 0) or 0),
        }

        for index, network in enumerate(wifi.get("networks", [])[:12]):
            name = str(network.get("ssid") or f"wifi-{index}")
            strength = float(network.get("signal", 0) or 0)
            freq_raw = str(network.get("freq", "") or "")
            freq_mhz = int(freq_raw) if freq_raw.isdigit() else 0
            band = "2.4 GHz"
            if freq_mhz >= 5925:
                band = "6 GHz"
                spectrum["radio_6ghz"] += 1
            elif freq_mhz >= 4900:
                band = "5 GHz"
                spectrum["radio_5ghz"] += 1
            else:
                spectrum["radio_2_4ghz"] += 1
            distance = self._estimate_distance_meters(strength)
            angle = self._stable_angle(f"wifi:{name}")
            radius = min(46.0, distance * 1.6)
            is_current = bool(current_wifi.get("connected") and current_wifi.get("ssid") == name)
            nodes.append(
                {
                    "id": f"wifi:{name}",
                    "kind": "wifi",
                    "label": name,
                    "strength": strength,
                    "band": band,
                    "distance_m": distance,
                    "security": network.get("security", ""),
                    "x": 50.0 if is_current else round(50 + (math.cos(angle) * radius), 1),
                    "y": 50.0 if is_current else round(50 + (math.sin(angle) * radius), 1),
                    "is_current": is_current,
                }
            )

        for index, device in enumerate(bluetooth.get("devices", [])[:12]):
            name = str(device.get("name") or f"bluetooth-{index}")
            angle = self._stable_angle(f"bluetooth:{name}")
            distance = round(3.0 + (index * 1.6), 1)
            radius = min(42.0, distance * 2.0)
            nodes.append(
                {
                    "id": f"bluetooth:{name}",
                    "kind": "bluetooth",
                    "label": name,
                    "strength": max(15, 82 - (index * 7)),
                    "band": "2.4 GHz",
                    "distance_m": distance,
                    "security": device.get("type", ""),
                    "x": round(50 + (math.cos(angle) * radius), 1),
                    "y": round(50 + (math.sin(angle) * radius), 1),
                    "is_current": False,
                }
            )

        nodes.sort(key=lambda item: (item["distance_m"], -item["strength"]))
        return {
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "center_label": "You",
            "current_link": current_link,
            "nodes": nodes,
            "counts": {
                "wifi": sum(1 for node in nodes if node["kind"] == "wifi"),
                "bluetooth": sum(1 for node in nodes if node["kind"] == "bluetooth"),
                "total": len(nodes),
            },
            "spectrum": spectrum,
            "note": "Distances are inferred from signal strength and device order, not measured by triangulation.",
        }

    def _runtime_ability_status(self) -> dict:
        assistant = self.server.assistant
        kali_status = self._json_load(assistant.tools.get_kali_session_status())
        policy = self._json_load(assistant.tools.policy_status())
        autonomy = self._json_load(assistant.autonomy.status())
        host_platform = platform.system()
        signal_supported = host_platform in {"Windows", "Linux", "Darwin"}
        wifi_supported = signal_supported
        bluetooth_supported = signal_supported
        network_supported = signal_supported
        system_supported = True

        return {
            "timestamp": datetime.now().isoformat(),
            "policy_mode": policy.get("mode", "unknown"),
            "abilities": {
                "chat": {"available": True, "live": True, "path": "/api/chat"},
                "health": {"available": True, "live": True, "path": "/api/health"},
                "mood": {"available": True, "live": True, "path": "/api/mood"},
                "status": {"available": True, "live": True, "path": "/api/status"},
                "memory": {
                    "available": True,
                    "live": True,
                    "total_facts": assistant.semantic_mem.get_stats().get("total_facts", 0),
                },
                "autonomy": {
                    "available": True,
                    "live": True,
                    "enabled": autonomy.get("state", {}).get("enabled", False),
                },
                "kali_terminal": {
                    "available": True,
                    "live": bool(kali_status.get("running")),
                    "cwd": kali_status.get("cwd", ""),
                },
                "screen_ocr": {
                    "available": TESSERACT_PATH.exists(),
                    "live": TESSERACT_PATH.exists(),
                },
                "active_window_ocr": {
                    "available": TESSERACT_PATH.exists(),
                    "live": TESSERACT_PATH.exists(),
                },
                "webcam_vision": {
                    "available": bool(assistant.vision.is_available),
                    "live": bool(assistant.vision.is_available),
                },
                "speech_to_text": {
                    "available": bool(assistant.stt.available),
                    "live": bool(assistant.stt.available),
                    "backend": assistant.stt.backend_name,
                },
                "text_to_speech": {
                    "available": bool(getattr(assistant.tts, "_backend", "none") != "none"),
                    "live": bool(getattr(assistant.tts, "_backend", "none") != "none"),
                },
                "watcher": {
                    "available": True,
                    "live": True,
                },
                "legion_registry": {
                    "available": True,
                    "live": True,
                    "path": "/api/legion/status",
                    "workers": assistant.legion.stats().get("total_workers", 0),
                },
                "chimera_state": {
                    "available": True,
                    "live": True,
                    "path": "/api/chimera/status",
                    "mutations": assistant.chimera.snapshot().get("mutation_count", 0),
                },
                "wifi_scan": {
                    "available": wifi_supported,
                    "live": wifi_supported,
                },
                "bluetooth_scan": {
                    "available": bluetooth_supported,
                    "live": bluetooth_supported,
                },
                "network_status": {
                    "available": network_supported,
                    "live": network_supported,
                },
                "system_overview": {
                    "available": system_supported,
                    "live": system_supported,
                },
                "browser_tools": {"available": True, "live": True},
                "document_tools": {"available": True, "live": True},
                "capabilities_catalog": {"available": True, "live": True, "path": "/api/capabilities"},
            },
        }

    def _system_overview(self) -> dict:
        assistant = self.server.assistant
        if assistant is None:
            return {"ok": False, "error": "assistant unavailable"}

        system_cmd = (
            "Get-CimInstance Win32_OperatingSystem | "
            "Select-Object CSName,LastBootUpTime,@{Name='FreeMemoryMB';Expression={[math]::Round($_.FreePhysicalMemory/1024,0)}},"
            "@{Name='TotalVisibleMemoryMB';Expression={[math]::Round($_.TotalVisibleMemorySize/1024,0)}} | ConvertTo-Json -Compress"
        )
        process_cmd = (
            "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 ProcessName,Id,CPU,WS | ConvertTo-Json -Compress"
        )

        system_payload = self._json_load(assistant.tools.run_shell(system_cmd))
        process_payload = self._json_load(assistant.tools.run_shell(process_cmd))
        if system_payload.get("returncode") != 0 or process_payload.get("returncode") != 0:
            return {
                "ok": False,
                "system": system_payload,
                "processes": process_payload,
            }

        system_json = self._json_load(str(system_payload.get("stdout", "")).strip())
        process_json = self._json_load(str(process_payload.get("stdout", "")).strip())
        processes = process_json if isinstance(process_json, list) else [process_json]
        return {
            "ok": True,
            "system": system_json,
            "top_processes": processes,
        }

    def _threat_overview(self) -> dict:
        try:
            snapshot = self.server.environment.ghost_check()
        except Exception as exc:
            return {"ok": False, "error": f"threat overview failed: {exc}"}

        reading = snapshot.get("reading", {}) if isinstance(snapshot, dict) else {}
        blockers = snapshot.get("blockers", []) if isinstance(snapshot, dict) else []
        return {
            "ok": True,
            "threat_level": snapshot.get("threat_level", "unknown"),
            "go": bool(snapshot.get("go", False)),
            "recommendation": snapshot.get("recommendation", "unknown"),
            "blockers": blockers,
            "checks": snapshot.get("checks", {}),
            "reading": reading,
            "summary": (
                f"Threat {snapshot.get('threat_level', 'unknown')} | "
                f"detections {reading.get('detection_count', 0)} | "
                f"location {reading.get('location', 'unknown')}"
            ),
        }

    def _documented_ability_audit(self) -> dict:
        runtime = self._runtime_ability_status()
        abilities = runtime["abilities"]
        vision_live = abilities["active_window_ocr"]["live"]
        webcam_live = abilities["webcam_vision"]["live"]
        browser_live = abilities["browser_tools"]["live"]
        docs_live = abilities["document_tools"]["live"]
        shell_live = abilities["chat"]["live"]
        kali_live = abilities["kali_terminal"]["available"]
        autonomy_live = abilities["autonomy"]["available"]
        wifi_live = abilities["wifi_scan"]["live"]
        bluetooth_live = abilities["bluetooth_scan"]["live"]
        network_live = abilities["network_status"]["live"]
        system_live = abilities["system_overview"]["live"]
        watcher_live = abilities["watcher"]["live"]

        checks = [
            {
                "name": "capture the screen",
                "category": "Vision & Screen",
                "status": "live" if abilities["screen_ocr"]["live"] else "missing",
                "backing": ["capture_screen_ocr"],
            },
            {
                "name": "what do you see / active window analysis",
                "category": "Vision & Screen",
                "status": "live" if vision_live else "missing",
                "backing": ["capture_active_window_ocr"],
            },
            {
                "name": "scan the room / webcam vision",
                "category": "Vision & Screen",
                "status": "live" if webcam_live else "missing",
                "backing": ["KaiVision"],
            },
            {
                "name": "scan the system",
                "category": "System Monitoring",
                "status": "live" if system_live else "partial" if shell_live else "missing",
                "backing": ["/api/system/overview", "run_shell", "status API"],
            },
            {
                "name": "what's running",
                "category": "System Monitoring",
                "status": "live" if system_live else "partial" if shell_live else "missing",
                "backing": ["/api/system/overview", "run_shell"],
            },
            {
                "name": "monitor the network",
                "category": "System Monitoring",
                "status": "live" if network_live else "partial" if shell_live else "missing",
                "backing": ["/api/signals/interfaces", "run_shell", "run_kali_session_command"],
            },
            {
                "name": "are there any threats",
                "category": "System Monitoring",
                "status": "live",
                "backing": ["/api/system/threats", "EnvironmentMonitor", "playbooks"],
            },
            {
                "name": "scan wifi",
                "category": "Network & Security",
                "status": "live" if wifi_live else "missing",
                "backing": ["/api/signals/wifi", "assistant /signal wifi CLI path"],
            },
            {
                "name": "bluetooth scan",
                "category": "Network & Security",
                "status": "live" if bluetooth_live else "missing",
                "backing": ["/api/signals/bluetooth", "assistant /signal bt CLI path"],
            },
            {
                "name": "network status",
                "category": "Network & Security",
                "status": "live" if network_live else "missing",
                "backing": ["/api/signals/interfaces", "assistant /signal net CLI path"],
            },
            {
                "name": "check security",
                "category": "Network & Security",
                "status": "live",
                "backing": ["/api/capabilities", "/api/abilities", "policy status"],
            },
            {
                "name": "read/list/find files",
                "category": "File Operations",
                "status": "live" if docs_live else "missing",
                "backing": ["read_file", "list_files", "find_document"],
            },
            {
                "name": "organize my downloads",
                "category": "File Operations",
                "status": "live" if docs_live else "missing",
                "backing": ["organize_downloads"],
            },
            {
                "name": "run whoami / shell commands",
                "category": "Shell Commands",
                "status": "live" if shell_live else "missing",
                "backing": ["/api/chat", "run_shell"],
            },
            {
                "name": "Kali terminal session",
                "category": "Shell Commands",
                "status": "live" if kali_live else "missing",
                "backing": ["/api/kali/start", "/api/kali/command"],
            },
            {
                "name": "search for topic",
                "category": "Browser & Research",
                "status": "live" if browser_live else "missing",
                "backing": ["search_browser", "search_web"],
            },
            {
                "name": "download file from site",
                "category": "Browser & Research",
                "status": "live" if browser_live else "missing",
                "backing": ["download_file"],
            },
            {
                "name": "document operations",
                "category": "Document Operations",
                "status": "live" if docs_live else "missing",
                "backing": ["list_documents", "find_document", "read_document", "document_stats"],
            },
            {
                "name": "do task / task planner",
                "category": "Tasks & Autonomy",
                "status": "live" if autonomy_live else "missing",
                "backing": ["TaskPlanner", "KaiAutonomy"],
            },
            {
                "name": "autonomy on/off/tick",
                "category": "Tasks & Autonomy",
                "status": "live" if autonomy_live else "missing",
                "backing": ["KaiAutonomy"],
            },
            {
                "name": "remember / memory",
                "category": "Memory & Learning",
                "status": "live",
                "backing": ["KaiMemory", "SemanticMemory"],
            },
            {
                "name": "forget item",
                "category": "Memory & Learning",
                "status": "live",
                "backing": ["KaiMemory.forget_note", "assistant forget command"],
            },
            {
                "name": "voice input",
                "category": "Voice",
                "status": "missing" if not abilities["speech_to_text"]["live"] else "live",
                "backing": ["KaiSTT"],
            },
            {
                "name": "voice output",
                "category": "Voice",
                "status": "live" if abilities["text_to_speech"]["available"] else "missing",
                "backing": ["KaiTTS", "/api/tts/speak", "/api/tts/toggle"],
            },
            {
                "name": "proactive watch mode",
                "category": "Voice",
                "status": "live",
                "backing": ["/api/watcher/status", "/api/watcher/events", "KaiWatcher CLI path", "dashboard OCR watch"],
            },
            {
                "name": "legion worker registry",
                "category": "Distributed Runtime",
                "status": "live",
                "backing": ["/api/legion/status", "/api/legion/recruit", "LegionController", "memory/legion_army.json"],
            },
            {
                "name": "chimera fingerprint state",
                "category": "Distributed Runtime",
                "status": "live",
                "backing": ["/api/chimera/status", "/api/chimera/mutate", "ChimeraController", "memory/chimera_fingerprint.json"],
            },
            {
                "name": "legion heartbeat",
                "category": "Distributed Runtime",
                "status": "live",
                "backing": ["/api/legion/heartbeat", "LegionController.heartbeat"],
            },
            {
                "name": "chimera header preview",
                "category": "Distributed Runtime",
                "status": "live",
                "backing": ["/api/chimera/headers", "ChimeraController.headers"],
            },
            {
                "name": "legacy source manifest",
                "category": "Distributed Runtime",
                "status": "live",
                "backing": ["/api/legacy/manifest", "kai-legion&chimera.py"],
            },
        ]

        counts = {
            "live": sum(1 for item in checks if item["status"] == "live"),
            "partial": sum(1 for item in checks if item["status"] == "partial"),
            "missing": sum(1 for item in checks if item["status"] == "missing"),
        }

        return {
            "timestamp": runtime["timestamp"],
            "counts": counts,
            "checks": checks,
            "notes": [
                "Live means backed by the current HTTP/dashboard runtime.",
                "Partial means code paths exist but are not fully surfaced or verified in the unified dashboard.",
                "Missing means documented or discussed capability has no confirmed live path yet.",
            ],
        }

    def _legacy_manifest(self) -> dict:
        assistant = self.server.assistant
        source_path = assistant.workspace / "kai-legion&chimera.py"
        source_text = ""
        source_present = source_path.exists()
        if source_present:
            try:
                source_text = source_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                source_text = ""

        def has(token: str) -> bool:
            return token in source_text

        source_capabilities = {
            "proxychains_manager": has("class ProxychainsManager"),
            "traffic_evasion": has("class TrafficEvasion"),
            "dns_over_tor": has("class DNSOverTor"),
            "ollama_brain": has("class OllamaBrain"),
            "profiler": has("def profiler("),
            "mass_daemon": has("def mass_daemon("),
            "flaw_cascade": has("def flaw_cascade("),
            "blackout": has("def blackout("),
            "ghost_persist": has("def ghost_persist("),
            "payload_factory": has("class PayloadFactory"),
            "legion": has("class Legion"),
            "chimera": has("class Chimera"),
            "agent_crew": has("class Agent"),
        }
        surfaced_safe = {
            "legion_registry": True,
            "legion_recruit": True,
            "legion_heartbeat": True,
            "chimera_state": True,
            "chimera_mutate": True,
            "chimera_headers": True,
            "legacy_manifest": True,
        }
        blocked_unsafe = [
            "proxychains_manager",
            "traffic_evasion",
            "dns_over_tor",
            "mass_daemon",
            "flaw_cascade",
            "blackout",
            "ghost_persist",
            "payload_factory",
        ]
        legacy_safe_total = sum(1 for value in surfaced_safe.values() if value)
        return {
            "ok": True,
            "source_script": str(source_path),
            "source_present": source_present,
            "source_capabilities": source_capabilities,
            "surfaced_safe_capabilities": surfaced_safe,
            "surfaced_safe_count": legacy_safe_total,
            "blocked_unsafe_capabilities": blocked_unsafe,
            "legion": assistant.legion.snapshot(),
            "chimera": {
                **assistant.chimera.snapshot(),
                "signature_catalog": {
                    "user_agents": len(getattr(assistant.chimera, "USER_AGENTS", []) or []),
                    "accept_headers": len(getattr(assistant.chimera, "ACCEPT_HEADERS", []) or []),
                    "accept_languages": len(getattr(assistant.chimera, "ACCEPT_LANGUAGES", []) or []),
                    "tls_versions": len(getattr(assistant.chimera, "TLS_VERSIONS", []) or []),
                },
            },
        }

    def _local_chat_fallback(self, message: str, error_text: str = "") -> str:
        lowered = message.lower()
        if any(token in lowered for token in ("hi", "hello", "hey")):
            return "Kai is here. The local model is dragging right now, but the chat link is alive."
        if "help" in lowered:
            return "Kai's model backend is slow right now. The stable dashboard is still up, but the model needs a moment."
        if "status" in lowered or "working" in lowered:
            return "The chat path is up, but the local model backend is timing out."
        if "wifi" in lowered:
            return "The model is slow right now, but WiFi scan is still available in Ops and at /api/signals/wifi."
        if "bluetooth" in lowered:
            return "The model is slow right now, but Bluetooth scan is still available in Ops and at /api/signals/bluetooth."
        if "screen" in lowered or "ocr" in lowered:
            return "The model is slow right now, but OCR is still available in Ops and at /api/ocr/active-window."
        if error_text:
            return f"Kai hit a local model issue: {error_text}"
        return "Kai's local model is slow right now, but the stable dashboard path is still alive."

    def _resilient_chat_fallback(self, message: str, error_text: str = "") -> str:
        assistant = self.server.assistant
        try:
            recovered = assistant._fallback_response(message, message, error_text)
            if recovered:
                return recovered
        except Exception:
            pass
        return self._fast_local_chat_reply(message) or self._local_chat_fallback(message, error_text)

    def _fast_local_chat_reply(self, message: str) -> str:
        lowered = message.lower()
        assistant = self.server.assistant
        route = assistant.router.route(message)
        if route.get("handler") in {"direct", "cached"}:
            response = str(route.get("data", {}).get("response", "")).strip()
            if response:
                return response
        if route.get("handler") == "web":
            response = assistant._web_route_response(message, route).strip()
            if response:
                return response

        if "wifi" in lowered:
            wifi = assistant.signals.scan_wifi()
            networks = wifi.get("networks", [])
            if not networks:
                return "No WiFi networks are showing right now."
            names = ", ".join(str(net.get("ssid") or "hidden") for net in networks[:3])
            return f"WiFi scan sees {int(wifi.get('count', 0) or len(networks))} networks. Strongest: {names}."

        if "bluetooth" in lowered or "bt" == lowered.strip():
            bluetooth = assistant.signals.scan_bluetooth()
            devices = bluetooth.get("devices", [])
            if not devices:
                return "Bluetooth scan is live. No nearby devices are showing right now."
            names = ", ".join(str(device.get("name") or "unknown") for device in devices[:3])
            return f"Bluetooth scan sees {int(bluetooth.get('count', 0) or len(devices))} devices. Top results: {names}."

        if any(token in lowered for token in ("what do you see", "active window", "read my screen", "ocr", "screen")):
            text = assistant.tools.capture_active_window_ocr().strip()
            if not text:
                return "OCR ran, but no readable text came back from the active window."
            compact = " ".join(text.split())
            if len(compact) > 360:
                compact = compact[:357] + "..."
            return f"Active window OCR: {compact}"

        if any(token in lowered for token in ("network", "current link", "connection")):
            link = assistant.signals.get_current_link_insights()
            current_wifi = link.get("current_wifi", {}) if isinstance(link.get("current_wifi"), dict) else {}
            active = str(
                link.get("active_interface")
                or current_wifi.get("ssid")
                or ("wireless" if link.get("connected") else "local-network")
            )
            address = str(link.get("active_ip") or link.get("local_ip") or "unknown")
            clients = int(link.get("client_count", len(link.get("clients", []) or [])) or 0)
            return f"Current link: {active} on {address}. Nearby clients detected: {clients}."

        if any(token in lowered for token in ("status", "health", "are you working", "are you up")):
            wifi = assistant.signals.scan_wifi()
            bluetooth = assistant.signals.scan_bluetooth()
            return (
                f"Kai dashboard is up. "
                f"WiFi networks: {int(wifi.get('count', 0) or 0)}. "
                f"Bluetooth devices: {int(bluetooth.get('count', 0) or 0)}."
            )

        return ""

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "kai-widget",
                    "surface": "dashboard-only",
                    "model": getattr(self.server.assistant.client, "model", ""),
                    "ollama_reachable": bool(self.server.assistant.client.is_reachable(timeout=2)),
                }
            )
            return

        if route == "/api/status":
            import time
            now = time.time()
            # Check cache
            if self.server._status_cache and (now - self.server._status_cache_time) < self.server._status_cache_ttl:
                self._send_json(self.server._status_cache)
                return
            
            status = {}
            if hasattr(self.server, 'assistant'):
                a = self.server.assistant
                # Emotional state
                if hasattr(a, 'emotions'):
                    status["emotion"] = a.emotions.get_state()
                # Relationship
                if hasattr(a, 'relationship'):
                    status["relationship"] = a.relationship.get_stats()
                # Social timing
                if hasattr(a, 'social_timing'):
                    status["timing"] = a.social_timing.get_status()
                # Inner monologue
                if hasattr(a, 'inner_voice'):
                    status["thoughts"] = a.inner_voice.get_stats()
                # Memory
                if hasattr(a, 'semantic_mem'):
                    status["memory"] = a.semantic_mem.get_stats()
                status["active_task"] = a.memory.get_active_task()
                status["task_summary"] = a.memory.summarize_tasks()
                status["conversation_summary"] = getattr(a, "conversation_summary", "")
                status["last_action_preview"] = getattr(a, "last_action_preview", "")
                status["legacy_bridge"] = {
                    "source_present": bool((a.workspace / "kai-legion&chimera.py").exists()),
                    "safe_surface_count": 7,
                    "legion_workers": a.legion.stats().get("total_workers", 0),
                    "chimera_mutations": a.chimera.snapshot().get("mutation_count", 0),
                }
            
            # Cache the result
            self.server._status_cache = status
            self.server._status_cache_time = now
            self._send_json(status)
            return

        if route == "/api/mood":
            import time
            now = time.time()
            # Check cache
            if self.server._mood_cache and (now - self.server._mood_cache_time) < self.server._mood_cache_ttl:
                self._send_json(self.server._mood_cache)
                return
            
            mood_data = {"mood": "neutral", "emoji": "🦊", "modifiers": []}
            if hasattr(self.server, 'assistant') and hasattr(self.server.assistant, 'emotions'):
                mood_data = self.server.assistant.emotions.get_response_color()
                state = self.server.assistant.emotions.get_state()
                mood_data["dimensions"] = state["dimensions"]
            
            # Cache the result
            self.server._mood_cache = mood_data
            self.server._mood_cache_time = now
            self._send_json(mood_data)
            return

        if route == "/api/capabilities":
            self._send_json(self._json_load(self.server.assistant.tools.list_capabilities()))
            return

        if route == "/api/abilities":
            self._send_json(self._runtime_ability_status())
            return

        if route == "/api/ability-audit":
            self._send_json(self._documented_ability_audit())
            return

        if route == "/api/system/overview":
            self._send_json(self._system_overview())
            return

        if route == "/api/system/threats":
            self._send_json(self._threat_overview())
            return

        if route == "/api/legion/status":
            self._send_json(self.server.assistant.legion.snapshot())
            return

        if route == "/api/chimera/status":
            self._send_json(self.server.assistant.chimera.snapshot())
            return

        if route == "/api/chimera/headers":
            chimera = self.server.assistant.chimera
            self._send_json(
                {
                    "ok": True,
                    "headers": chimera.headers(),
                    "fingerprint_id": chimera.snapshot().get("current_fingerprint", {}).get("fingerprint_id", ""),
                    "updated_at": chimera.snapshot().get("updated_at", ""),
                }
            )
            return

        if route == "/api/legacy/manifest":
            self._send_json(self._legacy_manifest())
            return

        if route == "/api/kali/status":
            self._send_json(self._json_load(self.server.assistant.tools.get_kali_session_status()))
            return

        if route == "/api/signals/wifi":
            self._send_json(self.server.assistant.signals.scan_wifi())
            return

        if route == "/api/signals/bluetooth":
            self._send_json(self.server.assistant.signals.scan_bluetooth())
            return

        if route == "/api/signals/interfaces":
            self._send_json(self.server.assistant.signals.get_interfaces())
            return

        if route == "/api/signals/map":
            self._send_json(self._signal_map())
            return

        if route == "/api/signals/current-link":
            self._send_json(self.server.assistant.signals.get_current_link_insights())
            return

        if route == "/api/signals/discover":
            self._send_json(self.server.assistant.signals.get_current_link_insights(resolve_hostnames=False))
            return

        if route == "/api/watcher/status":
            self._send_json(self.server.assistant.watcher.status_snapshot())
            return

        if route == "/api/watcher/events":
            watcher = self.server.assistant.watcher
            self._send_json(
                {
                    "ok": True,
                    "running": bool(getattr(watcher, "_running", False)),
                    "events": watcher.recent_events(limit=25),
                }
            )
            return

        if route == "/api/tts/status":
            tts = self.server.assistant.tts
            self._send_json(
                {
                    "ok": True,
                    "enabled": bool(tts.enabled),
                    "available": bool(tts.available),
                    "backend_available": bool(getattr(tts, "_backend", "none") != "none"),
                    "backend": getattr(tts, "_backend", "none"),
                    "speaking": bool(getattr(tts, "_speaking", False)),
                }
            )
            return

        if route == "/api/ocr/screen":
            text = self.server.assistant.tools.capture_screen_ocr()
            self._send_json(
                {
                    "ok": bool(text and "failed" not in text.lower() and "not found" not in text.lower()),
                    "text": text,
                    "source": "screen",
                }
            )
            return

        if route == "/api/ocr/active-window":
            text = self.server.assistant.tools.capture_active_window_ocr()
            self._send_json(
                {
                    "ok": bool(text and "failed" not in text.lower() and "not found" not in text.lower()),
                    "text": text,
                    "source": "active-window",
                }
            )
            return

        # Claude Integration Endpoints
        if route == "/api/claude/status":
            self._send_json({
                "status": "ready",
                "mode": "advisory",
                "integrated": True,
                "description": "Claude available as Kai panel tab - transparency mode"
            })
            return

        if route == "/api/claude/context":
            context = {
                "status": "ready",
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "kai_mood": "neutral",
                "kai_energy": 0.5,
                "last_consultation": None
            }
            if hasattr(self.server, 'assistant'):
                a = self.server.assistant
                if hasattr(a, 'emotions'):
                    state = a.emotions.get_state()
                    context["kai_mood"] = state.get("mood", "neutral")
                    context["kai_energy"] = state.get("energy", 0.5)
            self._send_json(context)
            return

        if route == "/api/claude/history":
            # Return empty history for now
            self._send_json({"consultations": []})
            return

        if route == "/api/pending":
            query = parse_qs(urlparse(self.path).query)
            since = 0.0
            try:
                since = float((query.get("since") or ["0"])[0] or "0")
            except (TypeError, ValueError):
                since = 0.0
            messages = []
            if hasattr(self.server, 'assistant') and hasattr(self.server.assistant, 'pending_messages'):
                messages = [
                    item for item in self.server.assistant.pending_messages
                    if float(item.get("timestamp", 0) or 0) > since
                ]
            last_timestamp = max((float(item.get("timestamp", 0) or 0) for item in messages), default=since)
            self._send_json({"messages": messages, "last_timestamp": last_timestamp})
            return

        target = STATIC_FILES.get(route)
        if not target:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        filename, content_type = target
        body = (WIDGET_DIR / filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))

        if filename.endswith(('.css', '.js', '.svg', '.woff', '.woff2')):
            self.send_header("Cache-Control", "public, max-age=3600")
        elif filename.endswith('.html'):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        elif filename.endswith('.json'):
            self.send_header("Cache-Control", "public, max-age=3600")

        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        # Device registration
        if route == "/api/device/register":
            name = payload.get("device_name", "unknown")
            dtype = payload.get("device_type", "browser")
            result = self.server.auth.register_device(name, dtype)
            self._send_json(result)
            return

        # Device authentication
        if route == "/api/device/auth":
            device_id = payload.get("device_id", "")
            token = payload.get("token", "")
            ok = self.server.auth.authenticate(device_id, token)
            self._send_json({"ok": ok}, HTTPStatus.OK if ok else HTTPStatus.UNAUTHORIZED)
            return

        # Device heartbeat
        if route == "/api/device/heartbeat":
            device_id = payload.get("device_id", "")
            token = payload.get("token", "")
            if self.server.auth.authenticate(device_id, token):
                self.server.auth.set_active(device_id, "ws")
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False}, HTTPStatus.UNAUTHORIZED)
            return

        # Push endpoint registration
        if route == "/api/device/push":
            device_id = payload.get("device_id", "")
            token = payload.get("token", "")
            endpoint = payload.get("endpoint", "")
            if self.server.auth.authenticate(device_id, token):
                self.server.auth.set_push_endpoint(device_id, endpoint)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False}, HTTPStatus.UNAUTHORIZED)
            return

        # Claude consultation endpoint
        if route == "/api/claude/consult":
            consultation = {
                "status": "advisory",
                "confidence": 0.0,
                "suggestion": "Claude integration will connect here",
                "reasoning": [],
                "kai_decision_required": True,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
            }
            self._send_json(consultation)
            return

        if route == "/api/kali/start":
            self._send_json(self._json_load(self.server.assistant.tools.start_kali_session()))
            return

        if route == "/api/kali/stop":
            self._send_json(self._json_load(self.server.assistant.tools.stop_kali_session()))
            return

        if route == "/api/kali/reset":
            stop_payload = self._json_load(self.server.assistant.tools.stop_kali_session())
            start_payload = self._json_load(self.server.assistant.tools.start_kali_session())
            self._send_json(
                {
                    "action": "kali_reset",
                    "ok": bool(start_payload.get("ok")),
                    "stop": stop_payload,
                    "start": start_payload,
                }
            )
            return

        if route == "/api/kali/command":
            command = str(payload.get("command", "")).strip()
            if not command:
                self._send_json({"ok": False, "error": "Command is required."}, status=HTTPStatus.BAD_REQUEST)
                return
            result = self._json_load(self.server.assistant.tools.run_kali_session_command(command))
            self._send_json(result, status=HTTPStatus.OK if result.get("ok", False) else HTTPStatus.BAD_REQUEST)
            return

        if route == "/api/watcher/start":
            self.server.assistant.watcher.start()
            self._send_json(self.server.assistant.watcher.status_snapshot())
            return

        if route == "/api/watcher/stop":
            self.server.assistant.watcher.stop()
            self._send_json(self.server.assistant.watcher.status_snapshot())
            return

        if route == "/api/tts/toggle":
            enabled = self.server.assistant.tts.toggle()
            self._send_json(
                {
                    "ok": True,
                    "enabled": bool(enabled),
                    "available": bool(self.server.assistant.tts.available),
                    "backend": getattr(self.server.assistant.tts, "_backend", "none"),
                }
            )
            return

        if route == "/api/tts/speak":
            text = str(payload.get("text", "")).strip()
            if not text:
                self._send_json({"ok": False, "error": "Text is required."}, status=HTTPStatus.BAD_REQUEST)
                return
            if getattr(self.server.assistant.tts, "_backend", "none") != "none" and not self.server.assistant.tts.enabled:
                self.server.assistant.tts.enabled = True
            ok = self.server.assistant.tts.speak(text)
            self._send_json(
                {
                    "ok": bool(ok),
                    "enabled": bool(self.server.assistant.tts.enabled),
                    "available": bool(self.server.assistant.tts.available),
                },
                status=HTTPStatus.OK if ok else HTTPStatus.BAD_REQUEST,
            )
            return

        if route == "/api/stt/listen":
            duration = float(payload.get("duration", 8) or 8)
            silence_timeout = float(payload.get("silence_timeout", 2.5) or 2.5)
            stt = self.server.assistant.stt
            if not stt.available:
                self._send_json(
                    {"ok": False, "error": "Speech-to-text backend is unavailable.", "backend": stt.backend_name},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            text = stt.listen(duration=duration, silence_timeout=silence_timeout)
            self._send_json(
                {
                    "ok": bool(text),
                    "text": text or "",
                    "backend": stt.backend_name,
                },
                status=HTTPStatus.OK if text else HTTPStatus.BAD_REQUEST,
            )
            return

        if route == "/api/legion/recruit":
            provider = str(payload.get("provider", "")).strip()
            endpoint = str(payload.get("endpoint", "")).strip()
            region = str(payload.get("region", "unknown") or "unknown").strip()
            max_concurrent = int(payload.get("max_concurrent", 5) or 5)
            raw_tags = payload.get("tags", [])
            if isinstance(raw_tags, str):
                tags = [part.strip() for part in raw_tags.split(",") if part.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(part).strip() for part in raw_tags if str(part).strip()]
            else:
                tags = []
            try:
                worker = self.server.assistant.legion.recruit_worker(
                    provider=provider,
                    endpoint=endpoint,
                    region=region,
                    max_concurrent=max_concurrent,
                    tags=tags,
                )
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "worker": worker.__dict__, "stats": self.server.assistant.legion.stats()})
            return

        if route == "/api/legion/heartbeat":
            worker_id = str(payload.get("worker_id", "")).strip()
            if not worker_id:
                self._send_json({"ok": False, "error": "worker_id is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                worker = self.server.assistant.legion.heartbeat(worker_id)
            except KeyError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "worker": worker.__dict__, "stats": self.server.assistant.legion.stats()})
            return

        if route == "/api/chimera/mutate":
            intensity = str(payload.get("intensity", "medium") or "medium").strip().lower()
            if intensity not in {"low", "medium", "high"}:
                self._send_json({"ok": False, "error": "intensity must be low, medium, or high"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(self.server.assistant.chimera.mutate(intensity=intensity))
            return

        if route != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        message = str(payload.get("message", "")).strip()

        if not message:
            self._send_json({"error": "Message is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        route = self.server.assistant.router.route(message)
        fast_reply = self._fast_local_chat_reply(message)
        if fast_reply:
            self.server.assistant.memory.append_session("user", message)
            self.server.assistant._append_history_pair(message, fast_reply)
            self.server.assistant.memory.append_session("assistant", fast_reply)
            fast_source = "web" if route.get("handler") == "web" else "local-tools"
            self._send_json({"reply": fast_reply, "degraded": False, "source": fast_source})
            return

        try:
            reply = asyncio.run(self.server.assistant.ask(message))
        except Exception as exc:
            fallback_reply = self._resilient_chat_fallback(message, str(exc))
            self._send_json({"reply": fallback_reply, "degraded": True})
            return

        self._send_json({"reply": reply})

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kai stable dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8127)
    parser.add_argument("--model", default=os.environ.get("KAI_MODEL", "qwen3:4b-q4_K_M"))
    parser.add_argument("--workspace", default=str(ROOT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assistant = KaiAssistant(model=args.model, workspace=Path(args.workspace))
    server = KaiWidgetServer((args.host, args.port), Handler, assistant)
    print(f"Kai widget ready at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
