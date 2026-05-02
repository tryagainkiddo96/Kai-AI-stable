"""
Kai Reasoning Framework — ReAct, Tree of Thoughts, and Self-Reflection.
Provides structured reasoning patterns for complex problem solving.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Thought:
    """A single reasoning step."""
    id: int
    content: str
    type: str  # "thought", "action", "observation", "reflection"
    parent_id: Optional[int] = None
    depth: int = 0
    score: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ReasoningTrace:
    """A complete reasoning trace (ReAct or ToT)."""
    task: str
    framework: str  # "react", "tot", "reflection"
    thoughts: List[Thought] = field(default_factory=list)
    result: str = ""
    success: bool = False
    steps_taken: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "framework": self.framework,
            "thoughts": [
                {
                    "id": t.id,
                    "content": t.content[:200],
                    "type": t.type,
                    "score": t.score,
                    "depth": t.depth,
                }
                for t in self.thoughts
            ],
            "result": self.result,
            "success": self.success,
            "steps_taken": self.steps_taken,
            "duration_seconds": self.duration_seconds,
        }


class ReActAgent:
    """
    ReAct (Reason + Act) reasoning loop.
    Alternates between thinking about what to do and taking actions.

    Pattern: Thought -> Action -> Observation -> Thought -> ... -> Final Answer
    """

    MAX_ITERATIONS = 8
    ACTION_PREFIX = "Action:"
    OBSERVATION_PREFIX = "Observation:"
    THOUGHT_PREFIX = "Thought:"
    FINAL_ANSWER_PREFIX = "Final Answer:"

    ACTIONS = {
        "search": "Search knowledge base or web for information",
        "read_file": "Read a file to inspect its contents",
        "run_command": "Execute a shell command and see the output",
        "analyze": "Analyze code or data for patterns/issues",
        "calculate": "Perform a calculation or logical deduction",
        "reflect": "Step back and evaluate current progress",
    }

    def __init__(self, ask_fn: Callable[[str], str], workspace: Optional[Path] = None) -> None:
        self.ask_fn = ask_fn
        self.workspace = workspace
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, fn: Callable) -> None:
        """Register a tool that the ReAct loop can invoke."""
        self.tools[name] = fn

    def _build_system_prompt(self, task: str) -> str:
        tools_str = "\n".join(f"  - {name}: {desc}" for name, desc in self.ACTIONS.items())
        if self.tools:
            tools_str += "\n" + "\n".join(f"  - {name}: (custom tool)" for name in self.tools)

        return f"""You are solving this problem step by step using ReAct reasoning:

Task: {task}

Available actions:
{tools_str}

Use this format strictly. Alternate between thoughts, actions, and observations:

Thought: [Your reasoning about what to do next]
Action: [action_name] [arguments]
Observation: [Result of the action — this is filled in by the system]
Thought: [Reasoning based on the observation]
...
Final Answer: [Your complete answer]

Rules:
- Think carefully before each action
- Only one action per step
- Use observations to guide next thoughts
- When you have enough information, give Final Answer
- Maximum {self.MAX_ITERATIONS} steps"""

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response to extract thought, action, or final answer."""
        result = {"thought": "", "action": "", "final_answer": ""}

        # Extract thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|Observation:|Final Answer:|$)", response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(r"Action:\s*(.+?)(?=Observation:|Thought:|Final Answer:|$)", response, re.DOTALL)
        if action_match:
            result["action"] = action_match.group(1).strip()

        # Extract final answer
        answer_match = re.search(r"Final Answer:\s*(.+?)(?=$)", response, re.DOTALL)
        if answer_match:
            result["final_answer"] = answer_match.group(1).strip()

        return result

    def _execute_action(self, action_str: str) -> str:
        """Execute an action and return the observation."""
        parts = action_str.split(None, 1)
        if not parts:
            return "No action specified."

        action_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Built-in actions
        if action_name == "reflect":
            return "Reflection noted. Continue reasoning."

        # Custom tools
        if action_name in self.tools:
            try:
                return str(self.tools[action_name](args))
            except Exception as e:
                return f"Tool error: {e}"

        return f"Unknown action: {action_name}. Available: {', '.join(self.ACTIONS.keys())}"

    def run(self, task: str) -> ReasoningTrace:
        """Execute the ReAct reasoning loop."""
        trace = ReasoningTrace(
            task=task,
            framework="react",
            start_time=datetime.utcnow().isoformat(),
        )

        system_prompt = self._build_system_prompt(task)
        conversation_history = [{"role": "system", "content": system_prompt}]
        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            trace.steps_taken = iteration

            # Get LLM response
            prompt = f"\n--- Step {iteration} ---\nContinue reasoning:"
            conversation_history.append({"role": "user", "content": prompt})
            full_prompt = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in conversation_history
            )
            response = self.ask_fn(full_prompt)

            parsed = self._parse_llm_response(response)

            # Record thought
            if parsed["thought"]:
                trace.thoughts.append(Thought(
                    id=iteration * 3 - 2,
                    content=parsed["thought"],
                    type="thought",
                    depth=iteration,
                ))

            # Check for final answer
            if parsed["final_answer"]:
                trace.result = parsed["final_answer"]
                trace.success = True
                trace.thoughts.append(Thought(
                    id=iteration * 3,
                    content=parsed["final_answer"],
                    type="thought",
                    depth=iteration,
                ))
                break

            # Execute action
            if parsed["action"]:
                observation = self._execute_action(parsed["action"])

                trace.thoughts.append(Thought(
                    id=iteration * 3 - 1,
                    content=parsed["action"],
                    type="action",
                    depth=iteration,
                ))
                trace.thoughts.append(Thought(
                    id=iteration * 3,
                    content=observation[:500],
                    type="observation",
                    depth=iteration,
                ))

                # Feed observation back
                conversation_history.append({
                    "role": "user",
                    "content": f"{self.ACTION_PREFIX} {parsed['action']}\n{self.OBSERVATION_PREFIX} {observation}",
                })

        trace.end_time = datetime.utcnow().isoformat()
        trace.duration_seconds = round(
            (datetime.fromisoformat(trace.end_time) - datetime.fromisoformat(trace.start_time)).total_seconds(), 2
        )

        if not trace.success:
            trace.result = f"Reached maximum iterations ({self.MAX_ITERATIONS}) without a final answer."

        return trace


class TreeOfThoughts:
    """
    Tree of Thoughts (ToT) reasoning.
    Explores multiple reasoning paths, evaluates them, and selects the best.

    Pattern: Generate multiple thoughts -> Evaluate each -> Branch promising paths -> Select best
    """

    MAX_DEPTH = 3
    BRANCH_FACTOR = 3
    EVALUATION_THRESHOLD = 0.5

    def __init__(self, ask_fn: Callable[[str], str], workspace: Optional[Path] = None) -> None:
        self.ask_fn = ask_fn
        self.workspace = workspace
        self._all_thoughts: List[Thought] = []
        self._thought_counter = 0

    def _next_id(self) -> int:
        self._thought_counter += 1
        return self._thought_counter

    def _generate_branches(self, task: str, context: str, depth: int) -> List[str]:
        """Generate multiple reasoning branches at this depth."""
        prompt = (
            f"Task: {task}\n\n"
            f"Current context:\n{context}\n\n"
            f"Generate exactly {self.BRANCH_FACTOR} different approaches to solve this problem. "
            f"Each approach should be distinct and numbered. "
            f"Format each as:\n"
            f"1. [Approach description with specific steps]\n"
            f"2. [Approach description with specific steps]\n"
            f"3. [Approach description with specific steps]"
        )
        response = self.ask_fn(prompt)

        # Extract numbered approaches
        branches = re.findall(r"\d+\.\s*(.+?)(?=\d+\.|$)", response, re.DOTALL)
        return [b.strip() for b in branches if b.strip()][:self.BRANCH_FACTOR]

    def _evaluate_branch(self, task: str, branch: str, depth: int) -> float:
        """Score a reasoning branch on a 0-1 scale."""
        prompt = (
            f"Task: {task}\n\n"
            f"Proposed approach:\n{branch}\n\n"
            f"Rate this approach on a scale of 0.0 to 1.0 based on:\n"
            f"- Likelihood of solving the task\n"
            f"- Efficiency (fewer steps = better)\n"
            f"- Correctness of the reasoning\n\n"
            f"Return ONLY a number between 0.0 and 1.0."
        )
        response = self.ask_fn(prompt)
        match = re.search(r"(\d+\.?\d*)", response)
        if match:
            score = float(match.group(1))
            return min(1.0, max(0.0, score))
        return 0.5

    def _expand_branch(self, task: str, branch: str, depth: int, parent_id: int) -> List[Thought]:
        """Recursively expand a reasoning branch."""
        thoughts = []

        if depth >= self.MAX_DEPTH:
            # Final evaluation
            score = self._evaluate_branch(task, branch, depth)
            t = Thought(
                id=self._next_id(),
                content=f"[Depth {depth}] {branch}",
                type="thought",
                parent_id=parent_id,
                depth=depth,
                score=score,
            )
            thoughts.append(t)
            return thoughts

        # Generate sub-branches
        context = f"Parent approach: {branch}"
        sub_branches = self._generate_branches(task, context, depth)

        for sub in sub_branches:
            t_parent = Thought(
                id=self._next_id(),
                content=f"[Depth {depth}] {sub[:150]}",
                type="thought",
                parent_id=parent_id,
                depth=depth,
            )
            thoughts.append(t_parent)

            # Recursive expansion
            child_thoughts = self._expand_branch(task, sub, depth + 1, t_parent.id)
            thoughts.extend(child_thoughts)

        return thoughts

    def _get_best_leaf(self, thoughts: List[Thought]) -> Thought:
        """Find the highest-scoring leaf thought."""
        leaves = [t for t in thoughts if t.type == "thought" and t.score > 0]
        if not leaves:
            return thoughts[-1] if thoughts else Thought(id=0, content="No solution found", type="thought")
        return max(leaves, key=lambda t: t.score)

    def run(self, task: str) -> ReasoningTrace:
        """Execute the Tree of Thoughts reasoning process."""
        self._all_thoughts.clear()
        self._thought_counter = 0

        trace = ReasoningTrace(
            task=task,
            framework="tot",
            start_time=datetime.utcnow().isoformat(),
        )

        # Generate initial branches
        initial_branches = self._generate_branches(task, "", 0)

        all_thoughts: List[Thought] = []
        for i, branch in enumerate(initial_branches):
            root = Thought(
                id=self._next_id(),
                content=branch[:200],
                type="thought",
                depth=0,
            )
            all_thoughts.append(root)

            # Evaluate and expand
            score = self._evaluate_branch(task, branch, 0)
            root.score = score

            if score >= self.EVALUATION_THRESHOLD:
                children = self._expand_branch(task, branch, 1, root.id)
                all_thoughts.extend(children)

        trace.thoughts = all_thoughts
        best = self._get_best_leaf(all_thoughts)

        # Generate final answer from best path
        best_path = self._reconstruct_path(all_thoughts, best.id)
        path_context = "\n".join(f"- {t.content}" for t in best_path)

        final_prompt = (
            f"Task: {task}\n\n"
            f"Best reasoning path:\n{path_context}\n\n"
            f"Based on this reasoning, provide a complete final answer."
        )
        trace.result = self.ask_fn(final_prompt)
        trace.success = best.score >= self.EVALUATION_THRESHOLD
        trace.end_time = datetime.utcnow().isoformat()
        trace.duration_seconds = round(
            (datetime.fromisoformat(trace.end_time) - datetime.fromisoformat(trace.start_time)).total_seconds(), 2
        )

        return trace

    def _reconstruct_path(self, thoughts: List[Thought], leaf_id: int) -> List[Thought]:
        """Reconstruct the path from root to a leaf thought."""
        path = []
        current_id = leaf_id
        thought_map = {t.id: t for t in thoughts}

        while current_id is not None:
            t = thought_map.get(current_id)
            if t is None:
                break
            path.append(t)
            current_id = t.parent_id

        return list(reversed(path))


class SelfReflector:
    """
    Self-reflection framework for reviewing and improving outputs.
    """

    def __init__(self, ask_fn: Callable[[str], str]) -> None:
        self.ask_fn = ask_fn

    def reflect(self, task: str, output: str) -> ReasoningTrace:
        """Review an output and suggest improvements."""
        trace = ReasoningTrace(
            task=f"Reflect on: {task}",
            framework="reflection",
            start_time=datetime.utcnow().isoformat(),
        )

        # Step 1: Identify issues
        critique_prompt = (
            f"Task: {task}\n\n"
            f"Output to review:\n{output[:2000]}\n\n"
            "Critically analyze this output. Identify:\n"
            "1. Factual errors or inaccuracies\n"
            "2. Missing information or edge cases\n"
            "3. Logic flaws or contradictions\n"
            "4. Areas for improvement\n\n"
            "Be specific and constructive."
        )
        critique = self.ask_fn(critique_prompt)
        trace.thoughts.append(Thought(id=1, content=critique[:500], type="reflection"))

        # Step 2: Generate improvements
        improve_prompt = (
            f"Original output:\n{output[:2000]}\n\n"
            f"Review findings:\n{critique[:1000]}\n\n"
            "Generate an improved version that addresses all issues identified."
        )
        improved = self.ask_fn(improve_prompt)
        trace.thoughts.append(Thought(id=2, content=improved[:500], type="thought"))

        # Step 3: Final assessment
        trace.result = improved
        trace.success = True
        trace.steps_taken = 3
        trace.end_time = datetime.utcnow().isoformat()
        trace.duration_seconds = round(
            (datetime.fromisoformat(trace.end_time) - datetime.fromisoformat(trace.start_time)).total_seconds(), 2
        )

        return trace


class ReasoningFramework:
    """
    High-level interface for all reasoning patterns.
    Automatically selects the best framework for the task.
    """

    def __init__(self, ask_fn: Callable[[str], str], workspace: Optional[Path] = None) -> None:
        self.ask_fn = ask_fn
        self.workspace = workspace
        self.react = ReActAgent(ask_fn, workspace)
        self.tot = TreeOfThoughts(ask_fn, workspace)
        self.reflection = SelfReflector(ask_fn)
        self.history: List[ReasoningTrace] = []

    def reason(self, task: str, framework: str = "auto", **kwargs: Any) -> ReasoningTrace:
        """
        Reason about a task using the specified framework.

        Args:
            task: The problem to solve
            framework: "react", "tot", "reflection", or "auto" (default)
            **kwargs: Additional parameters
        """
        if framework == "auto":
            framework = self._select_framework(task)

        if framework == "react":
            trace = self.react.run(task)
        elif framework == "tot":
            trace = self.tot.run(task)
        elif framework == "reflection":
            output = kwargs.get("output", "")
            trace = self.reflection.reflect(task, output)
        else:
            trace = self.react.run(task)

        self.history.append(trace)
        self._save_trace(trace)
        return trace

    def _select_framework(self, task: str) -> str:
        """Select the most appropriate reasoning framework."""
        task_lower = task.lower()

        # Complex multi-step problems benefit from Tree of Thoughts
        if any(kw in task_lower for kw in ["compare", "choose", "evaluate", "which is best", "optimize"]):
            return "tot"

        # Problems requiring external actions benefit from ReAct
        if any(kw in task_lower for kw in ["search", "find", "look up", "run", "execute", "check"]):
            return "react"

        # Code review and output improvement benefit from reflection
        if any(kw in task_lower for kw in ["review", "improve", "critique", "feedback", "better"]):
            return "reflection"

        # Default to ReAct for most problems
        return "react"

    def _save_trace(self, trace: ReasoningTrace) -> None:
        """Persist reasoning trace to memory."""
        if not self.workspace:
            return
        traces_dir = self.workspace / "memory" / "reasoning_traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = traces_dir / f"trace_{trace.framework}_{timestamp}.json"
        path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")

    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent reasoning traces."""
        return [t.to_dict() for t in self.history[-limit:]]

    def format_trace(self, trace: ReasoningTrace) -> str:
        """Format a reasoning trace for display."""
        lines = []
        lines.append(f"REASONING TRACE [{trace.framework.upper()}]")
        lines.append(f"{'='*50}")
        lines.append(f"Task: {trace.task}")
        lines.append(f"Framework: {trace.framework}")
        lines.append(f"Success: {'Yes' if trace.success else 'No'}")
        lines.append(f"Steps: {trace.steps_taken}")
        lines.append(f"Duration: {trace.duration_seconds}s")
        lines.append(f"")

        if trace.thoughts:
            lines.append(f"THOUGHTS:")
            lines.append(f"{'-'*40}")
            for t in trace.thoughts:
                prefix = {"thought": "💭", "action": "⚡", "observation": "👁", "reflection": "🔄"}.get(t.type, "•")
                lines.append(f"{prefix} [{t.type}] {t.content[:200]}")

        lines.append(f"")
        lines.append(f"RESULT:")
        lines.append(f"{'-'*40}")
        lines.append(trace.result)

        return "\n".join(lines)
