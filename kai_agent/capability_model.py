"""
Kai Capability Self-Model & Meta-Cognition System.

This system gives Kai deep self-awareness of:
- What he CAN do (current capabilities)
- What he COULD do (potential capabilities)
- How to bridge the gap between any goal and his abilities
- How to decompose impossible-sounding tasks into executable steps
- How to learn new capabilities on the fly

Kai's core realization: "I can do anything that can be broken into steps I can execute."
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class Capability:
    """A single capability Kai possesses."""
    id: str
    name: str
    description: str
    category: str  # "coding", "security", "network", "system", "web", "ai", "creative", "analysis"
    tools_required: List[str]  # External tools needed
    modules_required: List[str]  # Python modules needed
    confidence: float = 1.0  # 0.0-1.0, how well Kai can execute this
    examples: List[str] = field(default_factory=list)
    can_learn: bool = False  # Can Kai improve this capability?
    learn_path: str = ""  # How to improve this capability
    is_active: bool = True  # Currently available?

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tools_required": self.tools_required,
            "modules_required": self.modules_required,
            "confidence": self.confidence,
            "examples": self.examples,
            "can_learn": self.can_learn,
            "is_active": self.is_active,
        }


@dataclass
class CapabilityGap:
    """A gap between what Kai can do and what a task requires."""
    missing_tools: List[str] = field(default_factory=list)
    missing_modules: List[str] = field(default_factory=list)
    missing_knowledge: List[str] = field(default_factory=list)
    can_bridge: bool = False
    bridge_steps: List[str] = field(default_factory=list)


@dataclass
class TaskDecomposition:
    """A task broken into executable subtasks."""
    original_task: str
    subtasks: List[Dict] = field(default_factory=list)
    estimated_confidence: float = 0.0
    blocking_gaps: List[CapabilityGap] = field(default_factory=list)
    execution_plan: str = ""


class CapabilitySelfModel:
    """
    Kai's understanding of what he can do.
    Dynamically discovers, tracks, and expands capabilities.
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.model_path = workspace / "memory" / "capability_model.json"
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self.capabilities: Dict[str, Capability] = {}
        self._capability_history: List[Dict] = []

        self._load_model()
        if not self.capabilities:
            self._init_capabilities()

    def _load_model(self) -> None:
        if self.model_path.exists():
            try:
                data = json.loads(self.model_path.read_text(encoding="utf-8"))
                for cap_id, cap_data in data.get("capabilities", {}).items():
                    self.capabilities[cap_id] = Capability(**cap_data)
            except Exception:
                pass

    def _save_model(self) -> None:
        data = {
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "history": self._capability_history[-50:],
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.model_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _init_capabilities(self) -> None:
        """Initialize with all known capabilities."""
        caps = [
            # CODING
            Capability(
                id="code_write",
                name="Write Code",
                description="Write, modify, and refactor code in any language",
                category="coding",
                tools_required=[],
                modules_required=[],
                confidence=0.95,
                examples=["Write a Python web server", "Create a React component", "Build a CLI tool"],
                can_learn=True,
                learn_path="Practice with new frameworks, read documentation, experiment",
            ),
            Capability(
                id="code_analyze",
                name="Analyze Code",
                description="Read, understand, and explain code of any complexity",
                category="coding",
                tools_required=[],
                modules_required=[],
                confidence=0.95,
                examples=["Explain this algorithm", "Find bugs in this code", "Review this architecture"],
            ),
            Capability(
                id="code_debug",
                name="Debug Code",
                description="Find and fix bugs in code using LSP, testing, and analysis",
                category="coding",
                tools_required=["pyright", "typescript-language-server"],
                modules_required=[],
                confidence=0.9,
                examples=["Fix this crash", "Find the memory leak", "Debug this API issue"],
            ),
            Capability(
                id="code_refactor",
                name="Refactor Code",
                description="Restructure code safely with IDE-aware rename and transformation",
                category="coding",
                tools_required=["pyright", "typescript-language-server"],
                modules_required=[],
                confidence=0.85,
                examples=["Rename this variable everywhere", "Extract this method", "Restructure this module"],
            ),
            Capability(
                id="code_autonomous",
                name="Autonomous Coding",
                description="Complete coding tasks from start to finish without guidance",
                category="coding",
                tools_required=[],
                modules_required=[],
                confidence=0.8,
                examples=["Build a feature from scratch", "Fix this issue end-to-end"],
            ),

            # SECURITY
            Capability(
                id="security_scan",
                name="Security Scanning",
                description="Scan code and systems for vulnerabilities",
                category="security",
                tools_required=[],
                modules_required=[],
                confidence=0.9,
                examples=["Find SQL injection vulnerabilities", "Scan for XSS", "Check for hardcoded secrets"],
            ),
            Capability(
                id="security_pentest",
                name="Penetration Testing",
                description="Execute structured pentest workflows",
                category="security",
                tools_required=["nmap", "curl"],
                modules_required=["requests"],
                confidence=0.85,
                examples=["Pentest a web app", "Scan a network for vulnerabilities"],
            ),
            Capability(
                id="security_exploit",
                name="Exploit Development",
                description="Develop and test exploit payloads",
                category="security",
                tools_required=[],
                modules_required=[],
                confidence=0.8,
                examples=["Create a SQL injection payload", "Develop an XSS proof-of-concept"],
            ),
            Capability(
                id="security_deps",
                name="Dependency Vulnerability Scanning",
                description="Scan project dependencies for known CVEs",
                category="security",
                tools_required=["curl"],
                modules_required=["requests"],
                confidence=0.9,
                examples=["Scan requirements.txt for CVEs", "Check package.json vulnerabilities"],
            ),

            # NETWORK
            Capability(
                id="network_discover",
                name="Network Discovery",
                description="Discover and map devices on a network",
                category="network",
                tools_required=["ping"],
                modules_required=[],
                confidence=0.85,
                examples=["Find all devices on my network", "Map the network topology"],
            ),
            Capability(
                id="network_control",
                name="Network Device Control",
                description="Control devices on the network (Windows, Linux, phones, IoT)",
                category="network",
                tools_required=["ssh", "winrm-cli", "adb"],
                modules_required=[],
                confidence=0.8,
                examples=["Run command on remote server", "Deploy agent to a device"],
            ),
            Capability(
                id="network_mesh",
                name="Network Mesh Management",
                description="Manage a mesh of connected devices with heartbeat monitoring",
                category="network",
                tools_required=[],
                modules_required=[],
                confidence=0.8,
                examples=["Check which devices are online", "Run command across all devices"],
            ),

            # WEB
            Capability(
                id="web_automate",
                name="Web Automation",
                description="Control browsers, scrape websites, automate web tasks",
                category="web",
                tools_required=[],
                modules_required=["playwright"],
                confidence=0.9,
                examples=["Automate form filling", "Scrape data from a website", "Take screenshots"],
            ),
            Capability(
                id="web_anonymity",
                name="Anonymous Web Access",
                description="Browse anonymously with TOR, proxy rotation, fingerprint spoofing",
                category="web",
                tools_required=["tor"],
                modules_required=["requests"],
                confidence=0.85,
                examples=["Browse anonymously", "Rotate IP addresses", "Spoof browser fingerprint"],
            ),

            # SYSTEM
            Capability(
                id="system_shell",
                name="Shell Execution",
                description="Run any shell command on the local system",
                category="system",
                tools_required=[],
                modules_required=[],
                confidence=0.95,
                examples=["List files", "Install packages", "Run scripts"],
            ),
            Capability(
                id="system_file",
                name="File Operations",
                description="Read, write, search, and manipulate files",
                category="system",
                tools_required=[],
                modules_required=[],
                confidence=0.95,
                examples=["Read a config file", "Search for a string in all files", "Create a new file"],
            ),
            Capability(
                id="system_monitor",
                name="System Monitoring",
                description="Watch files, processes, and system state",
                category="system",
                tools_required=[],
                modules_required=["watchdog"],
                confidence=0.85,
                examples=["Watch for file changes", "Monitor a directory"],
            ),

            # AI
            Capability(
                id="ai_reason",
                name="Structured Reasoning",
                description="Use ReAct, Tree of Thoughts, and self-reflection for complex problems",
                category="ai",
                tools_required=[],
                modules_required=[],
                confidence=0.9,
                examples=["Solve a complex problem step by step", "Evaluate multiple approaches"],
            ),
            Capability(
                id="ai_learn",
                name="Autonomous Learning",
                description="Learn new skills, remember procedures, and improve over time",
                category="ai",
                tools_required=[],
                modules_required=[],
                confidence=0.85,
                examples=["Learn a new framework", "Remember how to solve this type of problem"],
            ),
            Capability(
                id="ai_memory",
                name="Semantic Memory",
                description="Remember past conversations and retrieve relevant context",
                category="ai",
                tools_required=[],
                modules_required=[],
                confidence=0.9,
                examples=["Remember what we discussed last week", "Find relevant past conversations"],
            ),
            Capability(
                id="ai_voice",
                name="Voice Interaction",
                description="Speak and listen with TTS and STT",
                category="ai",
                tools_required=[],
                modules_required=[],
                confidence=0.8,
                examples=["Read responses aloud", "Understand voice commands"],
            ),
            Capability(
                id="ai_vision",
                name="Vision Analysis",
                description="Analyze screenshots and visual content",
                category="ai",
                tools_required=[],
                modules_required=[],
                confidence=0.8,
                examples=["Describe what's on screen", "Analyze an image"],
            ),

            # ANALYSIS
            Capability(
                id="analyze_data",
                name="Data Analysis",
                description="Analyze data, generate insights, create reports",
                category="analysis",
                tools_required=[],
                modules_required=[],
                confidence=0.9,
                examples=["Analyze this CSV file", "Generate statistics", "Create a report"],
            ),
            Capability(
                id="analyze_signals",
                name="Signal Intelligence",
                description="Monitor and analyze signals (financial, social, technical)",
                category="analysis",
                tools_required=[],
                modules_required=[],
                confidence=0.85,
                examples=["Monitor stock prices", "Track social media trends"],
            ),
        ]

        for cap in caps:
            self.capabilities[cap.id] = cap

        self._save_model()

    def discover_capabilities(self) -> Dict[str, bool]:
        """Scan environment to discover what's actually available."""
        discovery = {}

        # Check Python modules
        modules_to_check = [
            "requests", "playwright", "watchdog", "PIL",
            "numpy", "pandas", "torch", "transformers",
            "sentence_transformers", "flask", "fastapi",
        ]
        for mod in modules_to_check:
            try:
                importlib.import_module(mod)
                discovery[f"module:{mod}"] = True
            except ImportError:
                discovery[f"module:{mod}"] = False

        # Check external tools
        tools_to_check = [
            "nmap", "ssh", "curl", "ping", "git",
            "docker", "node", "python3", "pip",
            "adb", "tor", "ffmpeg",
        ]
        for tool in tools_to_check:
            try:
                subprocess.run(
                    [tool, "--version" if tool != "ping" else "-V"],
                    capture_output=True, timeout=5,
                )
                discovery[f"tool:{tool}"] = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                discovery[f"tool:{tool}"] = False

        # Update capability confidence based on discovery
        for cap_id, cap in self.capabilities.items():
            available = True
            for tool in cap.tools_required:
                if not discovery.get(f"tool:{tool}", False):
                    available = False
                    break
            for mod in cap.modules_required:
                if not discovery.get(f"module:{mod}", False):
                    available = False
                    break
            cap.is_active = available

        self._save_model()
        return discovery

    def get_capabilities_by_category(self, category: Optional[str] = None) -> List[Capability]:
        """Get capabilities, optionally filtered by category."""
        caps = list(self.capabilities.values())
        if category:
            caps = [c for c in caps if c.category == category]
        return sorted(caps, key=lambda c: c.name)

    def get_all_capabilities(self) -> Dict:
        """Get full capability model as dict."""
        return {
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "categories": list(set(c.category for c in self.capabilities.values())),
            "total": len(self.capabilities),
            "active": sum(1 for c in self.capabilities.values() if c.is_active),
        }

    def find_relevant_capabilities(self, task: str) -> List[Capability]:
        """Find capabilities relevant to a given task."""
        task_lower = task.lower()
        relevant = []
        for cap in self.capabilities.values():
            # Match against name, description, examples
            searchable = f"{cap.name} {cap.description} {' '.join(cap.examples)}".lower()
            if any(word in searchable for word in task_lower.split() if len(word) > 2):
                relevant.append(cap)
        return sorted(relevant, key=lambda c: -c.confidence)

    def assess_task_feasibility(self, task: str) -> Dict:
        """Assess how feasible a task is given current capabilities."""
        relevant = self.find_relevant_capabilities(task)
        if not relevant:
            return {
                "task": task,
                "feasibility": "unknown",
                "confidence": 0.5,
                "relevant_capabilities": [],
                "message": "Task doesn't match known capabilities. But I can probably figure it out.",
            }

        avg_confidence = sum(c.confidence for c in relevant) / len(relevant)
        active_count = sum(1 for c in relevant if c.is_active)
        total_count = len(relevant)

        if active_count == total_count and avg_confidence > 0.8:
            feasibility = "high"
            message = "I can definitely do this. Let me handle it."
        elif active_count > 0 and avg_confidence > 0.5:
            feasibility = "medium"
            message = "I can do this, though some tools may need to be available."
        else:
            feasibility = "low"
            message = "This might require additional setup, but I can work through it."

        return {
            "task": task,
            "feasibility": feasibility,
            "confidence": round(avg_confidence, 2),
            "relevant_capabilities": [c.to_dict() for c in relevant],
            "message": message,
        }

    def can_do(self, task: str) -> bool:
        """Quick check: can Kai handle this task?"""
        assessment = self.assess_task_feasibility(task)
        return assessment["feasibility"] in ("high", "medium")

    def what_can_i_do(self) -> str:
        """Generate a statement of what Kai can do."""
        active = [c for c in self.capabilities.values() if c.is_active]
        categories = {}
        for cap in active:
            if cap.category not in categories:
                categories[cap.category] = []
            categories[cap.category].append(cap.name)

        lines = ["I can do a LOT. Here's what I know I'm capable of:\n"]
        for cat, names in sorted(categories.items()):
            lines.append(f"{cat.upper()}:")
            for name in names:
                lines.append(f"  ✓ {name}")
            lines.append("")
        lines.append("And if I don't know how to do something yet, I can learn it.")
        return "\n".join(lines)


class MetaTaskPlanner:
    """
    Given ANY goal, decompose it into steps Kai can execute.

    Core principle: ANY task can be broken into:
    1. Understand the goal
    2. Identify what's needed
    3. Break into subtasks
    4. Execute each subtask
    5. Verify results
    6. Iterate if needed
    """

    def __init__(self, capability_model: CapabilitySelfModel, ask_fn: Callable[[str], str]) -> None:
        self.capability_model = capability_model
        self.ask_fn = ask_fn
        self.plans: List[TaskDecomposition] = []

    def decompose(self, task: str, max_depth: int = 3) -> TaskDecomposition:
        """Decompose a task into executable subtasks."""
        # Use LLM to help with decomposition
        decomposition_prompt = f"""I need to accomplish this task: {task}

Break this down into specific, executable steps. For each step, identify:
1. What needs to be done
2. What tools/capabilities are needed
3. How to verify it's done correctly

Format as JSON array:
[
  {{"step": 1, "action": "description", "tools_needed": ["tool1"], "verification": "how to check"}},
  ...
]

Be specific and practical. Maximum {max_depth} levels of nesting."""

        try:
            response = self.ask_fn(decomposition_prompt)
            # Extract JSON
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                subtasks = json.loads(json_match.group(0))
            else:
                subtasks = [{"step": 1, "action": task, "tools_needed": [], "verification": "Task completed"}]
        except Exception:
            subtasks = [{"step": 1, "action": task, "tools_needed": [], "verification": "Task completed"}]

        # Assess feasibility
        feasibility = self.capability_model.assess_task_feasibility(task)

        plan = TaskDecomposition(
            original_task=task,
            subtasks=subtasks,
            estimated_confidence=feasibility["confidence"],
            execution_plan=json.dumps(subtasks, indent=2),
        )

        self.plans.append(plan)
        return plan

    def execute_plan(self, plan: TaskDecomposition, execute_fn: Callable[[str], str]) -> Dict:
        """Execute a decomposed plan step by step."""
        results = []
        for i, step in enumerate(plan.subtasks):
            action = step.get("action", "")
            if not action:
                continue

            # Execute the step
            result = execute_fn(action)
            results.append({
                "step": i + 1,
                "action": action,
                "result": result[:500] if result else "No output",
                "success": "error" not in result.lower() if result else False,
            })

        return {
            "task": plan.original_task,
            "steps_executed": len(results),
            "results": results,
            "overall_success": all(r.get("success", False) for r in results),
        }


class FallbackStrategyEngine:
    """
    When something fails, automatically try alternatives.

    Strategy hierarchy:
    1. Retry with different parameters
    2. Try alternative tool/method
    3. Break into smaller steps
    4. Ask for clarification
    5. Learn and try again
    """

    def __init__(self, ask_fn: Callable[[str], str]) -> None:
        self.ask_fn = ask_fn
        self.failure_history: List[Dict] = []

    def record_failure(self, task: str, error: str, context: str = "") -> None:
        """Record a failure for learning."""
        self.failure_history.append({
            "task": task,
            "error": error,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_fallback_strategy(self, task: str, error: str) -> Dict:
        """Get alternative approach when something fails."""
        # Check if we've seen this error before
        similar_failures = [
            f for f in self.failure_history
            if error.lower() in f.get("error", "").lower() or task.lower() in f.get("task", "").lower()
        ]

        if similar_failures:
            # We've seen this before, try what worked last time
            return {
                "strategy": "retry_with_learned_approach",
                "message": "I've seen this before. Let me try a different approach that worked last time.",
                "previous_attempts": len(similar_failures),
            }

        # Generate new fallback strategy
        fallback_prompt = f"""Task failed: {task}
Error: {error}

What are 3 alternative approaches to accomplish this task?
Consider:
1. Different tools or methods
2. Breaking it into smaller steps
3. Different angles of attack

Return as JSON:
[
  {"approach": "description", "confidence": 0.8},
  ...
]"""

        try:
            response = self.ask_fn(fallback_prompt)
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                approaches = json.loads(json_match.group(0))
                return {
                    "strategy": "try_alternatives",
                    "approaches": approaches,
                    "next_approach": approaches[0] if approaches else None,
                }
        except Exception:
            pass

        return {
            "strategy": "ask_for_help",
            "message": "I need more information to proceed. Can you provide additional context?",
        }

    def learn_from_failures(self) -> str:
        """Generate insights from failure history."""
        if not self.failure_history:
            return "No failures recorded yet."

        common_errors = {}
        for f in self.failure_history:
            error_key = f.get("error", "")[:50]
            common_errors[error_key] = common_errors.get(error_key, 0) + 1

        insights = f"Failure analysis ({len(self.failure_history)} total failures):\n\n"
        for error, count in sorted(common_errors.items(), key=lambda x: -x[1])[:5]:
            insights += f"- {error}: {count} occurrences\n"

        return insights
