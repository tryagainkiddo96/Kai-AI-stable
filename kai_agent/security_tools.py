"""
Security tools integration for Kai pentesting capabilities.
Provides policy-gated access to Kali security tooling.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


class SecurityToolsConfig:
    """Configuration and metadata for security tools"""
    
    TOOLS = {
        "nmap": {
            "category": "recon",
            "risk": "medium",
            "requires_auth": False,
            "description": "Network mapping and port scanning",
            "command": "nmap",
        },
        "metasploit": {
            "category": "exploitation",
            "risk": "high",
            "requires_auth": True,
            "description": "Metasploit Framework exploitation",
            "command": "msfconsole",
        },
        "sqlmap": {
            "category": "web",
            "risk": "medium",
            "requires_auth": False,
            "description": "SQL injection testing",
            "command": "sqlmap",
        },
        "burp": {
            "category": "web",
            "risk": "medium",
            "requires_auth": False,
            "description": "Burp Suite web proxy",
            "command": "burpsuite",
        },
        "wireshark": {
            "category": "network",
            "risk": "low",
            "requires_auth": False,
            "description": "Network packet analyzer",
            "command": "wireshark",
        },
        "aircrack": {
            "category": "wireless",
            "risk": "high",
            "requires_auth": True,
            "description": "WiFi cracking suite",
            "command": "aircrack-ng",
        },
        "hashcat": {
            "category": "password",
            "risk": "medium",
            "requires_auth": False,
            "description": "Hash cracking",
            "command": "hashcat",
        },
        "john": {
            "category": "password",
            "risk": "medium",
            "requires_auth": False,
            "description": "John the Ripper password cracker",
            "command": "john",
        },
        "nikto": {
            "category": "web",
            "risk": "medium",
            "requires_auth": False,
            "description": "Web server scanner",
            "command": "nikto",
        },
        "ffuf": {
            "category": "web",
            "risk": "medium",
            "requires_auth": False,
            "description": "Fast web fuzzer",
            "command": "ffuf",
        },
        "gobuster": {
            "category": "web",
            "risk": "medium",
            "requires_auth": False,
            "description": "Directory/DNS/VHost busting",
            "command": "gobuster",
        },
        "hydra": {
            "category": "password",
            "risk": "medium",
            "requires_auth": False,
            "description": "Credential brute forcing",
            "command": "hydra",
        },
        "msfvenom": {
            "category": "exploitation",
            "risk": "high",
            "requires_auth": True,
            "description": "Metasploit payload generator",
            "command": "msfvenom",
        },
        "searchsploit": {
            "category": "recon",
            "risk": "low",
            "requires_auth": False,
            "description": "ExploitDB search",
            "command": "searchsploit",
        },
        "whois": {
            "category": "recon",
            "risk": "low",
            "requires_auth": False,
            "description": "Domain/IP WHOIS lookup",
            "command": "whois",
        },
        "dig": {
            "category": "recon",
            "risk": "low",
            "requires_auth": False,
            "description": "DNS lookup",
            "command": "dig",
        },
    }
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get tool configuration by name"""
        return cls.TOOLS.get(name.lower())
    
    @classmethod
    def list_by_category(cls, category: str) -> list[Dict[str, Any]]:
        """List tools by category"""
        return [
            {"name": name, **config}
            for name, config in cls.TOOLS.items()
            if config["category"] == category
        ]
    
    @classmethod
    def list_by_risk(cls, risk: str) -> list[Dict[str, Any]]:
        """List tools by risk level"""
        return [
            {"name": name, **config}
            for name, config in cls.TOOLS.items()
            if config["risk"] == risk
        ]


class SecurityAuditLog:
    """Audit trail for security tool usage"""
    
    def __init__(self, save_path: Path):
        self.save_path = save_path
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[Dict[str, Any]] = self._load_entries()
    
    def _load_entries(self) -> list[Dict[str, Any]]:
        """Load audit entries from disk"""
        if not self.save_path.exists():
            return []
        try:
            return json.loads(self.save_path.read_text(encoding="utf-8"))
        except Exception:
            return []
    
    def record(self, tool: str, args: str, target: str, authorized: bool, reason: str = "") -> None:
        """Record tool execution"""
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "args": args,
            "target": target,
            "authorized": authorized,
            "reason": reason,
        }
        self.entries.append(entry)
        self._save_entries()
    
    def _save_entries(self) -> None:
        """Save audit entries to disk"""
        self.save_path.write_text(
            json.dumps(self.entries[-1000:], indent=2),  # Keep last 1000
            encoding="utf-8"
        )
    
    def get_summary(self, tool: Optional[str] = None) -> Dict[str, Any]:
        """Get audit summary"""
        filtered = [e for e in self.entries if tool is None or e["tool"] == tool]
        authorized_count = sum(1 for e in filtered if e["authorized"])
        blocked_count = sum(1 for e in filtered if not e["authorized"])
        return {
            "total": len(filtered),
            "authorized": authorized_count,
            "blocked": blocked_count,
            "latest": filtered[-5:] if filtered else [],
        }


class SecurityToolsManager:
    """Manages security tool execution with policy enforcement"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.audit_log = SecurityAuditLog(workspace / "memory" / "security_audit.json")
        self.authorized_targets: set[str] = set()
        self.authorized_tools: set[str] = set()
    
    def authorize_target(self, target: str, reason: str = "") -> bool:
        """Authorize a target for testing"""
        self.authorized_targets.add(target)
        self.audit_log.record("authorize_target", "", target, True, reason)
        return True
    
    def authorize_tool(self, tool: str, reason: str = "") -> bool:
        """Authorize a tool for use"""
        tool_lower = tool.lower()
        if tool_lower not in SecurityToolsConfig.TOOLS:
            return False
        self.authorized_tools.add(tool_lower)
        self.audit_log.record("authorize_tool", "", tool, True, reason)
        return True
    
    def is_target_authorized(self, target: str) -> bool:
        """Check if target is authorized"""
        return target in self.authorized_targets or self._is_localhost(target)
    
    def is_tool_authorized(self, tool: str) -> bool:
        """Check if tool is authorized"""
        return tool.lower() in self.authorized_tools
    
    def can_execute(self, tool: str, target: str, policy_mode: str = "balanced") -> tuple[bool, str]:
        """
        Determine if tool execution is permitted
        
        Returns:
            (allowed: bool, reason: str)
        """
        tool_lower = tool.lower()
        tool_config = SecurityToolsConfig.get_tool(tool_lower)
        
        if tool_config is None:
            return False, f"Unknown tool: {tool}"
        
        # Guarded mode: read-only tools only
        if policy_mode == "guarded":
            read_only = ["whois", "dig", "searchsploit", "nikto", "gobuster"]
            if tool_lower not in read_only:
                return False, f"Tool {tool} not allowed in guarded mode"
            return True, "Tool allowed in guarded mode (read-only)"
        
        # Check authorization for high-risk tools
        if tool_config["risk"] == "high":
            if not self.is_tool_authorized(tool):
                return False, f"Tool {tool} requires explicit authorization"
        
        # Check target authorization
        if tool_config["requires_auth"]:
            if not self.is_target_authorized(target):
                return False, f"Target {target} not authorized for testing"
        
        # Balanced mode: all authorized tools allowed
        return True, f"Tool execution authorized"
    
    @staticmethod
    def _is_localhost(target: str) -> bool:
        """Check if target is localhost"""
        localhost_patterns = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]
        return any(pattern in target.lower() for pattern in localhost_patterns)
    
    def get_tool_info(self, tool: str) -> Dict[str, Any]:
        """Get tool information and usage"""
        config = SecurityToolsConfig.get_tool(tool)
        if not config:
            return {"error": f"Tool not found: {tool}"}
        
        audit = self.audit_log.get_summary(tool)
        return {
            **config,
            "name": tool,
            "authorized": self.is_tool_authorized(tool),
            "audit": audit,
        }
    
    def list_tools(self, category: Optional[str] = None, risk: Optional[str] = None) -> list[Dict[str, Any]]:
        """List available tools"""
        if category:
            return SecurityToolsConfig.list_by_category(category)
        if risk:
            return SecurityToolsConfig.list_by_risk(risk)
        return [
            {"name": name, **config}
            for name, config in SecurityToolsConfig.TOOLS.items()
        ]


__all__ = ["SecurityToolsConfig", "SecurityAuditLog", "SecurityToolsManager"]
