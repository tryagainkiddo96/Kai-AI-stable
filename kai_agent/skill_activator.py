"""
Skill Activator — automatically matches user intent to relevant skills and activates them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kai_agent.skills_system import KaiSkillsSystem, Skill


# Intent patterns mapped to skill categories and keywords
INTENT_MAP = {
    "recon": {
        "keywords": ["scout", "recon", "scan", "enumerate", "discover", "map", "probe", "fingerprint"],
        "category": "security",
        "action_hint": "Run network scanning, service enumeration, and target fingerprinting.",
    },
    "web_research": {
        "keywords": ["search", "research", "look up", "find info", "browse", "web", "google"],
        "category": "web",
        "action_hint": "Use Tavily search, browser tools, and web scraping to gather information.",
    },
    "file_analysis": {
        "keywords": ["analyze", "read file", "inspect", "examine", "review code", "parse"],
        "category": "file",
        "action_hint": "Read and analyze files, extract patterns, summarize content.",
    },
    "file_organization": {
        "keywords": ["organize", "sort", "clean up", "restructure", "move files", "categorize"],
        "category": "file",
        "action_hint": "Organize files, rename, sort by type/date/size, create folder structure.",
    },
    "system_monitoring": {
        "keywords": ["monitor", "watch", "track", "observe", "check status", "health"],
        "category": "system",
        "action_hint": "Monitor system resources, track processes, watch for changes.",
    },
    "web_automation": {
        "keywords": ["automate", "fill form", "click", "download", "interact with", "navigate"],
        "category": "web",
        "action_hint": "Use Playwright to automate browser interactions, fill forms, click elements.",
    },
    "pentest": {
        "keywords": ["breach", "pentest", "attack", "exploit", "vulnerability", "cve", "hack"],
        "category": "security",
        "action_hint": "Run vulnerability scans, check for known CVEs, enumerate attack surface.",
    },
    "code_editing": {
        "keywords": ["edit", "fix", "refactor", "write code", "create file", "modify"],
        "category": "automation",
        "action_hint": "Edit code files, fix bugs, refactor, write new implementations.",
    },
    "project_setup": {
        "keywords": ["setup", "install", "clone", "init", "configure", "bootstrap"],
        "category": "automation",
        "action_hint": "Clone repos, install dependencies, configure projects, set up environments.",
    },
    "data_extraction": {
        "keywords": ["extract", "grab", "pull", "exfil", "scrape", "harvest", "collect"],
        "category": "web",
        "action_hint": "Extract data from web pages, files, or APIs. Structure and save results.",
    },
}


class SkillActivator:
    """Matches user intent to available skills and provides activation guidance."""

    def __init__(self, skills_system: KaiSkillsSystem) -> None:
        self.skills = skills_system
        self._cache: dict[str, list[Skill]] = {}

    def find_relevant_skills(self, user_input: str, limit: int = 3) -> list[dict[str, Any]]:
        """Find skills relevant to the user's intent."""
        lowered = user_input.lower()
        matched_intents: list[tuple[float, str, dict]] = []

        for intent_key, intent_data in INTENT_MAP.items():
            score = 0
            for kw in intent_data["keywords"]:
                if kw in lowered:
                    score += len(kw)
            if score > 0:
                matched_intents.append((score, intent_key, intent_data))

        matched_intents.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        seen_skill_ids: set[str] = set()

        for score, intent_key, intent_data in matched_intents[:limit]:
            category = intent_data["category"]
            action_hint = intent_data["action_hint"]

            # Find skills in this category
            category_skills = self.skills.list_skills(category=category)
            # Also search by keyword
            keyword_skills = self.skills.search_skills(intent_key.replace("_", " "))

            combined = []
            for s in category_skills + keyword_skills:
                if s.id not in seen_skill_ids:
                    seen_skill_ids.add(s.id)
                    combined.append(s)

            combined.sort(key=lambda s: (s.confidence, s.usage_count), reverse=True)

            for skill in combined[:2]:
                results.append({
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "confidence": round(skill.confidence, 2),
                    "usage_count": skill.usage_count,
                    "success_rate": round(skill.success_rate, 2),
                    "steps": skill.steps,
                    "learned_patterns": skill.learned_patterns[:3],
                    "intent": intent_key,
                    "action_hint": action_hint,
                })

        # If no learned skills found, return intent-based suggestions
        if not results and matched_intents:
            for score, intent_key, intent_data in matched_intents[:limit]:
                results.append({
                    "skill_id": None,
                    "skill_name": None,
                    "confidence": 0.0,
                    "usage_count": 0,
                    "success_rate": 0.0,
                    "steps": [],
                    "learned_patterns": [],
                    "intent": intent_key,
                    "action_hint": intent_data["action_hint"],
                    "note": "No learned skill yet — Kai will create one from this execution.",
                })

        return results

    def build_activation_context(self, user_input: str) -> str:
        """Build system prompt context for activated skills."""
        skills = self.find_relevant_skills(user_input)
        if not skills:
            return ""

        lines = ["SKILLS ACTIVATED — follow these learned procedures:"]
        for i, skill in enumerate(skills, 1):
            lines.append(f"\nSkill {i}: {skill['skill_name'] or 'New skill (will be learned)'}")
            lines.append(f"  Confidence: {skill['confidence']} | Usage: {skill['usage_count']} | Success: {skill['success_rate']}")
            if skill.get("steps"):
                lines.append(f"  Learned steps: {' -> '.join(skill['steps'][:5])}")
            if skill.get("learned_patterns"):
                lines.append(f"  Patterns: {', '.join(skill['learned_patterns'])}")
            lines.append(f"  Action hint: {skill['action_hint']}")

            if skill.get("note"):
                lines.append(f"  NOTE: {skill['note']} Record your steps so a skill can be created.")

        lines.append(
            "\nWhen executing, follow the learned steps where applicable. "
            "If a skill has high confidence (>0.7), prioritize its approach. "
            "If you discover a better approach, note it so the skill can improve."
        )

        return "\n".join(lines)

    def skill_status(self) -> dict[str, Any]:
        """Get overall skill system status."""
        all_skills = self.skills.list_skills()
        insights = self.skills.get_learning_insights()

        return {
            "total_skills": len(all_skills),
            "skills_by_category": {},
            "top_skills": [
                {
                    "name": s.name,
                    "category": s.category,
                    "confidence": round(s.confidence, 2),
                    "usage_count": s.usage_count,
                    "success_rate": round(s.success_rate, 2),
                }
                for s in all_skills[:10]
            ],
            "insights": insights,
        }

    def _skills_by_category(self, all_skills: list[Skill]) -> dict[str, int]:
        cats: dict[str, int] = {}
        for s in all_skills:
            cats[s.category] = cats.get(s.category, 0) + 1
        return cats
