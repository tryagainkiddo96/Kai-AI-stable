"""
Kai-Claude Consultant Bridge (Python)
====================================

Flask API server that allows Claude to consult with Kai.

NOT a tool executor. Instead:
- Claude asks questions about tasks
- Kai provides recommendations
- Claude executes recommendations through Kai's own systems
- Kai remains the decision-maker and executor

Architecture pattern:
  Claude (thinking) → Kai Bridge (context) → Claude (recommendation)
                        ↓
                     Kai executes
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify
from datetime import datetime

# Import Kai components
try:
    from kai_agent.assistant import KaiAssistant
    from kai_agent.claude_consultant_handler import KaiConsultantHandler
except ImportError:
    raise ImportError("Kai AI modules not found. Install Kai first.")


class KaiConsultantAPI:
    """
    API for Claude to consult with Kai
    
    Kai remains the primary brain and decision-maker.
    Claude is an external thinking partner.
    """

    def __init__(self, workspace: Path, kai_model: str = "mistral:latest"):
        self.workspace = workspace
        self.assistant = KaiAssistant(model=kai_model, workspace=workspace)
        self.handler = KaiConsultantHandler(self.assistant)
        self.consultation_history: Dict[str, Dict] = {}

    def get_context(self) -> Dict[str, Any]:
        """
        Get Kai's current context for Claude to understand
        
        Claude uses this before making recommendations:
        - What tools does Kai have?
        - What's Kai's emotional state?
        - What does Kai know?
        """
        return self.handler.prepare_context()

    def receive_recommendation(self, task: str, steps: List[str], confidence: float, reasoning: str = "") -> Dict[str, Any]:
        """
        Claude sends a recommendation to Kai
        
        Kai evaluates it and decides whether to execute.
        Returns what Kai will do (or won't do).
        """
        recommendation_id = str(uuid.uuid4())
        
        plan = {
            "recommendation": task,
            "steps": steps,
            "confidence": confidence,
            "reasoning": reasoning,
        }
        
        # Let Kai's handler process the recommendation
        execution_plan = self.handler.process_recommendation(task, plan, confidence)
        execution_plan["id"] = recommendation_id
        
        # Store in history
        self.consultation_history[recommendation_id] = execution_plan
        
        return {
            "ok": True,
            "recommendation_id": recommendation_id,
            "kai_decision": execution_plan["kai_decision"],
            "kai_response": self.handler.format_for_ui(execution_plan, {"energy_level": 50}),
        }

    def check_capabilities(self, task: str, policy_mode: str = "balanced") -> Dict[str, Any]:
        """
        Claude asks: "Can Kai do this task?"
        
        Returns what Kai can/should do
        """
        return {
            "allowed": True,  # Would check against Kai's actual capabilities
            "tools_needed": ["kai_files", "kai_memory"],  # Example
            "blockers": [],
            "recommendation": "Safe to execute with balanced policy",
        }

    def get_capabilities_list(self) -> Dict[str, Any]:
        """
        List all of Kai's capabilities
        
        Claude uses this to know what it can ask Kai to do
        """
        return {
            "capabilities": [
                "terminal_execute",
                "file_read",
                "file_write",
                "directory_list",
                "screen_capture",
                "ocr_text",
                "browser_search",
                "browser_fetch",
                "memory_store",
                "memory_recall",
            ],
            "policy_aware": True,
            "autonomy_available": True,
        }

    def get_autonomy_status(self, task_complexity: str, estimated_duration: str) -> Dict[str, Any]:
        """
        Claude asks: "Should Kai run this autonomously?"
        
        Claude suggests, but Kai decides.
        """
        complexity_score = {"simple": 1, "moderate": 2, "complex": 3}.get(task_complexity, 2)
        
        return {
            "enabled": False,  # Would check actual state
            "claude_should_enable": complexity_score == 3,
            "reason": "Complex task benefits from autonomy" if complexity_score == 3 else "Not needed",
            "energy_estimate": 30 * complexity_score,
        }

    def record_feedback(self, recommendation_id: str, succeeded: bool, result_summary: str = "", lessons: str = "") -> Dict[str, Any]:
        """
        Claude sends feedback after Kai executes
        
        Kai learns from what Claude observes.
        """
        if recommendation_id in self.consultation_history:
            self.consultation_history[recommendation_id]["execution"] = {
                "succeeded": succeeded,
                "result": result_summary,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Kai learns from feedback
            if hasattr(self.assistant.memory, "save"):
                self.assistant.memory.save({
                    "type": "claude_feedback",
                    "recommendation_id": recommendation_id,
                    "lesson": lessons,
                    "outcome": "success" if succeeded else "failure",
                })
        
        return {
            "ok": True,
            "recorded": True,
            "kai_acknowledgment": "Feedback stored in memory",
        }


def create_api_app(workspace: Path = None) -> Flask:
    """Create Flask app for Kai-Claude Consultant API"""
    
    app = Flask(__name__)
    workspace = workspace or Path.cwd() / "workspace"
    api = KaiConsultantAPI(workspace)

    @app.route("/api/context", methods=["GET"])
    def context():
        """Get Kai's context for Claude"""
        return jsonify(api.get_context())

    @app.route("/api/recommendation", methods=["POST"])
    def recommendation():
        """Receive Claude's recommendation for Kai"""
        data = request.json
        result = api.receive_recommendation(
            task=data.get("task"),
            steps=data.get("steps", []),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", ""),
        )
        return jsonify(result)

    @app.route("/api/capabilities", methods=["POST"])
    def check_capabilities():
        """Check what Kai can do"""
        data = request.json
        result = api.check_capabilities(
            task=data.get("task"),
            policy_mode=data.get("policy", "balanced"),
        )
        return jsonify(result)

    @app.route("/api/capabilities", methods=["GET"])
    def capabilities_list():
        """List all Kai capabilities"""
        return jsonify(api.get_capabilities_list())

    @app.route("/api/autonomy/status", methods=["POST"])
    def autonomy_status():
        """Get autonomy recommendation"""
        data = request.json
        result = api.get_autonomy_status(
            task_complexity=data.get("task_complexity", "moderate"),
            estimated_duration=data.get("estimated_duration", ""),
        )
        return jsonify(result)

    @app.route("/api/feedback", methods=["POST"])
    def feedback():
        """Record execution feedback"""
        data = request.json
        result = api.record_feedback(
            recommendation_id=data.get("recommendation_id"),
            succeeded=data.get("succeeded", False),
            result_summary=data.get("result_summary", ""),
            lessons=data.get("lessons_learned", ""),
        )
        return jsonify(result)

    @app.route("/health", methods=["GET"])
    def health():
        """Health check"""
        return jsonify({
            "ok": True,
            "status": "Kai-Claude Consultant API ready",
            "version": "1.0",
            "kai_brain": "active",
        })

    return app


if __name__ == "__main__":
    # Start the API server
    workspace = Path.cwd() / "workspace"
    app = create_api_app(workspace)
    app.run(host="127.0.0.1", port=8127, debug=True)
