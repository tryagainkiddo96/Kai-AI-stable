"""
Claude consultation tab integration for Kai's widget.
Adds /api/claude/* endpoints to the widget server for transparency-mode consultation.
Kai makes decisions; Claude provides advisory context visible in the widget.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ClaudeWidgetIntegration:
    """Integrates Claude consultation as a read-only advisory tab in Kai's widget."""
    
    def __init__(self, kai_assistant):
        """Initialize with reference to KaiAssistant for context."""
        self.kai_assistant = kai_assistant
        self.consultation_history = []
        self.max_history = 50
        
    async def get_claude_context(self) -> Dict[str, Any]:
        """Get current context that Claude would see."""
        try:
            mood = self.kai_assistant.emotional_state.get_mood() if hasattr(self.kai_assistant, 'emotional_state') else "neutral"
            energy = self.kai_assistant.emotional_state.energy if hasattr(self.kai_assistant, 'emotional_state') else 0.5
            
            return {
                "status": "ready",
                "kai_mood": mood,
                "kai_energy": energy,
                "timestamp": datetime.now().isoformat(),
                "last_consultation": self.consultation_history[-1] if self.consultation_history else None,
            }
        except Exception as e:
            logger.error(f"Error getting Claude context: {e}")
            return {"status": "error", "message": str(e)}
    
    async def consult_claude(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Ask Claude for advisory input on a decision.
        Returns structured recommendation (Kai decides actual execution).
        """
        try:
            # Build consultation request
            consultation_request = {
                "query": user_query,
                "kai_context": context or await self.get_claude_context(),
                "timestamp": datetime.now().isoformat(),
                "mode": "advisory",  # Key: Claude is advisory, not executive
            }
            
            # For now, return structured empty recommendation
            # In full implementation, this calls Claude Code backend
            recommendation = {
                "status": "advisory",
                "confidence": 0.0,
                "suggestion": "Claude service not yet integrated",
                "reasoning": [],
                "kai_decision_required": True,  # Kai always decides
                "timestamp": datetime.now().isoformat(),
            }
            
            # Store in history
            self.consultation_history.append({
                "request": consultation_request,
                "recommendation": recommendation,
            })
            
            # Trim history
            if len(self.consultation_history) > self.max_history:
                self.consultation_history = self.consultation_history[-self.max_history:]
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error consulting Claude: {e}")
            return {
                "status": "error",
                "message": str(e),
                "kai_decision_required": True,
            }
    
    async def get_consultation_history(self, limit: int = 20) -> list:
        """Get recent consultations for the widget tab."""
        return self.consultation_history[-limit:] if self.consultation_history else []
    
    async def get_claude_recommendation(self, task_type: str) -> Dict[str, Any]:
        """Get Claude's recommendation for a specific task type."""
        return {
            "task_type": task_type,
            "status": "ready_for_consultation",
            "available_actions": [],
            "requires_kai_approval": True,
        }


def register_claude_endpoints(widget_server_handler_class, claude_integration: ClaudeWidgetIntegration):
    """
    Register Claude consultation endpoints on the widget server.
    Call this in widget_server.py's Handler class initialization.
    """
    
    # Patch the handler to add Claude routes
    original_do_get = widget_server_handler_class.do_GET
    original_do_post = widget_server_handler_class.do_POST
    
    async def handle_claude_route(self, path: str, method: str) -> tuple[int, str]:
        """Handle Claude-specific API routes."""
        
        if path == "/api/claude/context":
            context = await claude_integration.get_claude_context()
            return 200, json.dumps(context)
        
        elif path == "/api/claude/history":
            history = await claude_integration.get_consultation_history()
            return 200, json.dumps({"consultations": history})
        
        elif path == "/api/claude/status":
            return 200, json.dumps({
                "status": "ready",
                "mode": "advisory",
                "integrated": True,
                "description": "Claude available for consultation",
            })
        
        return None  # Not a Claude route
    
    def new_do_GET(self):
        """Extended GET to handle Claude routes."""
        path = self.path.split("?")[0]
        
        if path.startswith("/api/claude/"):
            try:
                result = asyncio.run(handle_claude_route(self, path, "GET"))
                if result:
                    status_code, response_body = result
                    body = response_body.encode("utf-8")
                    self.send_response(status_code)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception as e:
                logger.error(f"Claude endpoint error: {e}")
                self.send_response(500)
                self.end_headers()
                return
        
        # Fall back to original handler
        return original_do_get(self)
    
    def new_do_POST(self):
        """Extended POST to handle Claude consultation requests."""
        path = self.path.split("?")[0]
        
        if path == "/api/claude/consult":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode("utf-8"))
                
                query = request_data.get("query", "")
                context = request_data.get("context")
                
                recommendation = asyncio.run(claude_integration.consult_claude(query, context))
                response_body = json.dumps(recommendation).encode("utf-8")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
                return
                
            except Exception as e:
                logger.error(f"Claude consultation error: {e}")
                self.send_response(400)
                self.end_headers()
                return
        
        # Fall back to original handler
        return original_do_post(self)
    
    # Apply patches
    widget_server_handler_class.do_GET = new_do_GET
    widget_server_handler_class.do_POST = new_do_POST
