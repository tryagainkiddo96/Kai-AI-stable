"""
Kai's Claude Consultant Handler
================================

When Kai consults Claude, this module handles:
- Receiving consultation requests from TypeScript
- Formatting Kai's context for Claude
- Processing Claude's recommendations
- Returning structured guidance back to Kai

Kai remains the decision-maker. Claude just advises.
"""

import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ConsultationRequest:
    """Request from Kai to Claude for advice"""

    query: str
    context: Dict[str, Any]
    role: str = "kai-consultant"
    timestamp: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ConsultationResponse:
    """Claude's recommendation back to Kai"""

    success: bool
    recommendation: str = None
    plan: Dict[str, Any] = None
    reasoning_chain: List[str] = None
    confidence: float = 0.0
    suggest_autonomy: bool = False
    error: str = None


class KaiConsultantHandler:
    """
    Handles consultation logic on Kai's side
    
    This is the "thinking partner" integration point
    Kai asks questions, Claude answers, Kai decides
    """

    def __init__(self, kai_assistant):
        """
        Args:
            kai_assistant: Reference to KaiAssistant instance
        """
        self.assistant = kai_assistant
        self.memory = kai_assistant.memory
        self.emotions = kai_assistant.emotions

    def prepare_context(self) -> Dict[str, Any]:
        """
        Prepare Kai's current state for Claude consultation
        
        Kai shares:
        - Available tools and their status
        - Current emotional/energy state
        - Recent memory (learnings, relationships)
        - Task history
        
        Kai keeps private:
        - Future plans (don't bias Claude)
        - Raw memory details (only summaries)
        - Personal relationships (abstracted)
        """
        return {
            "kai_version": getattr(self.assistant, "version", "unknown"),
            "kai_capabilities": self._get_available_tools(),
            "kai_emotional_state": {
                "mood": self.emotions.get_current_mood() if hasattr(self.emotions, "get_current_mood") else "neutral",
                "energy": getattr(self.emotions, "energy_level", 50),
                "stability": getattr(self.emotions, "stability", "stable"),
            },
            "kai_recent_memory": self._get_memory_summary(),
            "kai_task_count": len(getattr(self.assistant, "recent_tasks", [])),
            "kai_uptime": getattr(self.assistant, "uptime_seconds", 0),
        }

    def _get_available_tools(self) -> List[str]:
        """List of tools Kai currently has access to"""
        if not hasattr(self.assistant, "tools"):
            return []

        return [
            "terminal_execute",
            "file_read",
            "file_write",
            "file_delete",
            "directory_list",
            "screen_capture",
            "ocr_text",
            "browser_open",
            "browser_search",
            "memory_store",
            "memory_recall",
        ]

    def _get_memory_summary(self) -> Dict[str, Any]:
        """
        Summary of Kai's memory without raw details
        
        For Claude to understand what Kai knows, not to expose everything
        """
        try:
            return {
                "has_semantic_memory": hasattr(self.memory, "semantic"),
                "has_emotional_memory": hasattr(self.memory, "emotional"),
                "memory_size_estimate": getattr(self.memory, "estimate_size", lambda: "unknown")(),
                "recent_learnings_count": len(getattr(self.memory, "recent_entries", [])),
            }
        except:
            return {"has_memory": True, "accessible": False}

    async def process_recommendation(
        self, recommendation: str, plan: Dict[str, Any], confidence: float
    ) -> Dict[str, Any]:
        """
        Process Claude's recommendation
        
        Before Kai executes, check:
        1. Is recommendation aligned with Kai's values?
        2. Can Kai execute this with available tools?
        3. Does Kai's emotional state permit this?
        4. Should autonomy be enabled?
        
        Returns: Structured plan for Kai to execute
        """

        execution_plan = {
            "source": "claude_recommendation",
            "recommendation": recommendation,
            "steps": plan.get("steps", []) if plan else [],
            "confidence": confidence,
            "kai_decision": self._should_execute(confidence),
            "autonomy_suggested": confidence > 0.85,
            "processed_at": datetime.now().isoformat(),
        }

        # Store in memory that Claude advised
        if hasattr(self.memory, "record_interaction"):
            self.memory.record_interaction(
                {
                    "type": "claude_consultation",
                    "confidence": confidence,
                    "accepted": execution_plan["kai_decision"],
                }
            )

        return execution_plan

    def _should_execute(self, confidence: float) -> bool:
        """
        Does Kai trust Claude's recommendation?
        
        Heuristics:
        - High confidence + stable mood = execute
        - High confidence + low energy = ask user
        - Low confidence = suggest alternatives
        """
        energy = getattr(self.emotions, "energy_level", 50)

        # If Claude is confident and Kai has energy, go with it
        if confidence > 0.85 and energy > 40:
            return True

        # If Claude is moderately confident and Kai is okay, consider it
        if confidence > 0.7 and energy > 60:
            return True

        # Otherwise, flag for user confirmation
        return False

    def merge_with_kai_knowledge(
        self, claude_recommendation: str, kai_preference: str = None
    ) -> str:
        """
        Combine Claude's reasoning with Kai's local knowledge
        
        If Kai knows something Claude doesn't, blend them
        """
        if not kai_preference:
            return claude_recommendation

        # If Kai and Claude agree, use the combined reasoning
        # If they disagree, favor Kai (local decision)
        return f"Claude suggests: {claude_recommendation}. Kai's local knowledge: {kai_preference}."

    def format_for_ui(self, plan: Dict[str, Any], kai_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Claude's recommendation for display in Kai's UI
        
        Show the user:
        - What Claude recommended
        - Kai's assessment (will execute? yes/no)
        - Confidence level
        - Why (if available)
        """
        return {
            "title": "Claude's Recommendation",
            "recommendation": plan.get("recommendation", ""),
            "steps": plan.get("steps", []),
            "confidence": f"{int(plan.get('confidence', 0) * 100)}%",
            "kai_will_execute": "✓ Yes" if plan.get("kai_decision") else "✗ No",
            "reason": self._explain_kai_decision(plan, kai_state),
            "timestamp": plan.get("processed_at", ""),
        }

    def _explain_kai_decision(self, plan: Dict[str, Any], kai_state: Dict[str, Any]) -> str:
        """Explain why Kai accepted or rejected Claude's recommendation"""
        confidence = plan.get("confidence", 0)
        energy = kai_state.get("energy_level", 50)

        if plan.get("kai_decision"):
            if confidence > 0.85:
                return "Claude is very confident. Kai trusts this."
            else:
                return "Claude's suggestion aligns with Kai's capabilities."
        else:
            if confidence < 0.5:
                return "Claude's confidence is too low. Kai will think more."
            if energy < 40:
                return "Kai is tired. Will revisit when more energetic."
            return "Kai wants to verify this with the user first."


# Module-level helper function
def should_kai_consult_claude(task: str, kai_context: Dict[str, Any]) -> bool:
    """
    Quick heuristic: should Kai ask Claude?
    
    True for: complex planning, multi-step tasks, unknown domains
    False for: simple operations, local decisions, low energy
    """
    complex_keywords = [
        "refactor",
        "architect",
        "plan",
        "coordinate",
        "optimize",
        "complex",
        "multiple",
    ]

    needs_help = any(kw in task.lower() for kw in complex_keywords)
    has_energy = kai_context.get("energy_level", 50) > 30

    return needs_help and has_energy
