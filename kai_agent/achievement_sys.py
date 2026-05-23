"""Achievement System — gamification badges for user milestones."""
from __future__ import annotations

import threading
import time


class AchievementSystem:
    """Tracks events, unlocks badges, returns progress data."""

    ACHIEVEMENTS = {
        "first_words": {"name": "First Words", "desc": "Send your first message", "icon": "💬", "tracker": "messages_sent", "target": 1},
        "conversationalist": {"name": "Conversationalist", "desc": "Send 100 messages", "icon": "🗣️", "tracker": "messages_sent", "target": 100},
        "network_scout": {"name": "Network Scout", "desc": "Discover 5 devices", "icon": "🔍", "tracker": "devices_discovered", "target": 5},
        "netmap_master": {"name": "NetMap Master", "desc": "Discover 20 devices", "icon": "🌐", "tracker": "devices_discovered", "target": 20},
        "first_breach": {"name": "First Blood", "desc": "Run your first breach", "icon": "⚔️", "tracker": "breaches_run", "target": 1},
        "hacker": {"name": "Hacker", "desc": "Run 10 breaches", "icon": "💀", "tracker": "breaches_run", "target": 10},
        "first_hunt": {"name": "The Hunt Begins", "desc": "Execute your first hunt", "icon": "🎯", "tracker": "hunts_run", "target": 1},
        "predator": {"name": "Predator", "desc": "Hunt 5 targets", "icon": "🐺", "tracker": "hunts_run", "target": 5},
        "ghost_protocol": {"name": "Ghost Protocol", "desc": "Activate Ghost Protocol", "icon": "👻", "tracker": "ghost_runs", "target": 1},
        "ritual_master": {"name": "Ritual Master", "desc": "Create 3 rituals", "icon": "📜", "tracker": "rituals_created", "target": 3},
        "shell_jockey": {"name": "Shell Jockey", "desc": "Run 50 commands", "icon": "🖥️", "tracker": "commands_run", "target": 50},
        "power_user": {"name": "Power User", "desc": "Run 200 commands", "icon": "⚡", "tracker": "commands_run", "target": 200},
        "avatar": {"name": "Digital Avatar", "desc": "Digital Twin passes all health checks", "icon": "🧬", "tracker": "twin_healthy", "target": 1},
        "night_owl": {"name": "Night Owl", "desc": "Send messages after midnight 10 times", "icon": "🦉", "tracker": "night_messages", "target": 10},
        "timeline_keeper": {"name": "Timeline Keeper", "desc": "Query your timeline 5 times", "icon": "📖", "tracker": "timeline_queries", "target": 5},
        "butler": {"name": "The Butler", "desc": "Learn 5 daily patterns", "icon": "🎩", "tracker": "patterns_learned", "target": 5},
        "archivist": {"name": "Archivist", "desc": "Log 100 clipboard entries", "icon": "📋", "tracker": "clipboard_entries", "target": 100},
    }

    def __init__(self, db):
        self.db = db
        self._init_progress()

    def _init_progress(self):
        for aid, info in self.ACHIEVEMENTS.items():
            existing = False
            for p in self.db.get_progress():
                if p["tracker_name"] == info["tracker"]:
                    existing = True
                    break
            if not existing:
                self.db.update_progress(info["tracker"], increment=0, target=info["target"])

    def register_event(self, event_type: str, data: dict = None):
        """Register an event that might trigger an achievement."""
        tracker_map = {
            "message": "messages_sent",
            "device_discovered": "devices_discovered",
            "breach": "breaches_run",
            "hunt": "hunts_run",
            "ghost": "ghost_runs",
            "ritual_created": "rituals_created",
            "command": "commands_run",
            "twin_healthy": "twin_healthy",
            "timeline_query": "timeline_queries",
            "pattern_learned": "patterns_learned",
            "clipboard_entry": "clipboard_entries",
        }
        tracker = tracker_map.get(event_type)
        if not tracker:
            return []

        self.db.update_progress(tracker, increment=1)
        return self._check_unlocks()

    def _check_unlocks(self) -> list[str]:
        progress = {p["tracker_name"]: p["current_value"] for p in self.db.get_progress()}
        unlocked = []
        for aid, info in self.ACHIEVEMENTS.items():
            if self.db.is_achievement_unlocked(info["name"]):
                continue
            if progress.get(info["tracker"], 0) >= info["target"]:
                if self.db.unlock_achievement(info["name"], info["desc"], info["icon"]):
                    unlocked.append(info["name"])
        return unlocked

    def get_all(self) -> list[dict]:
        progress = {p["tracker_name"]: p for p in self.db.get_progress()}
        unlocked_badges = {a["name"] for a in self.db.get_achievements()}
        result = []
        for aid, info in self.ACHIEVEMENTS.items():
            p = progress.get(info["tracker"], {})
            current = p.get("current_value", 0) if isinstance(p, dict) else 0
            target = info["target"]
            result.append({
                "id": aid,
                "name": info["name"],
                "desc": info["desc"],
                "icon": info["icon"],
                "unlocked": info["name"] in unlocked_badges,
                "progress": min(1.0, current / max(target, 1)),
                "current": current,
                "target": target,
            })
        return sorted(result, key=lambda x: (-x["unlocked"], -x["progress"]))

    def get_unlocked(self) -> list[dict]:
        return [a for a in self.get_all() if a["unlocked"]]
