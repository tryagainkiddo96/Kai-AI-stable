"""Minimal MCP orchestrator for Kai in a safe lab mode.

This module provides a lightweight, parallel task orchestrator
that runs simulated reconnaissance and scanning agents. It is
intended for demonstration and testing in a controlled LAB.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Task:
    topic: str
    scope: str = "lab"


class _BaseAgent:
    name: str

    async def run(self, task: Task) -> Dict[str, str]:
        raise NotImplementedError


class ReconSimAgent(_BaseAgent):
    name = "ReconSim"

    async def run(self, task: Task) -> Dict[str, str]:
        # Simulated discovery in a safe lab environment
        await asyncio.sleep(0.5)
        hosts = ["lab1.local", "lab2.local"]
        return {
            "name": self.name,
            "summary": f"Discovered hosts: {', '.join(hosts)} for topic {task.topic}",
            "hosts": ",".join(hosts),
        }


class PortScanSimAgent(_BaseAgent):
    name = "PortScanSim"

    async def run(self, task: Task) -> Dict[str, str]:
        await asyncio.sleep(0.8)
        ports = [22, 80, 443]
        summary = []
        for host in ["lab1.local", "lab2.local"]:
            summary.append(f"{host}: open ports {', '.join(map(str, ports))}")
        return {"name": self.name, "summary": f"Ports discovered for hosts: {'; '.join(summary)}"}


class ReportAgent(_BaseAgent):
    name = "ReportGen"

    async def run(self, task: Task, inputs: List[Dict[str, str]] | None = None) -> Dict[str, str]:
        await asyncio.sleep(0.2)
        sections = []
        if inputs:
            for item in inputs:
                sections.append(f"{item.get('name')} -> {item.get('summary', '')}")
        report = "\n".join(sections) if sections else f"Hunt report for {task.topic} (lab)"
        return {"name": self.name, "summary": report}


class MCPOrchestrator:
    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout
        self.agents = [ReconSimAgent(), PortScanSimAgent(), ReportAgent()]

    async def run_hunt(self, topic: str) -> str:
        task = Task(topic=topic)
        # Run agents in parallel
        results = await asyncio.gather(*(agent.run(task) for agent in self.agents), return_exceptions=True)
        # Build a simple human-readable report
        lines = [f"[MCP Hunt] Topic: {topic}"]
        for r in results:
            if isinstance(r, Exception):
                lines.append(f"[AgentError] {r}")
                continue
            name = r.get("name", "Agent")
            summary = r.get("summary", "")
            lines.append(f"- {name}: {summary}")
        # Final synthesized report
        return "\n".join(lines)

def run_demo_hunt(topic: str) -> str:
    import asyncio
    orchestrator = MCPOrchestrator()
    return asyncio.run(orchestrator.run_hunt(topic))
