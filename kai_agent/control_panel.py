#!/usr/bin/env python3
# kai_agent/control_panel.py
# Kai Control Panel - Access all capabilities in one dashboard
# Updated: 2026

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))


class KaiControlPanel:
    """
    Central control panel for all Kai capabilities.
    Use this to access Ghost Mode, Recon, Security Agents, and more.
    """
    
    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self._ghost_mode = None
        self._recon = None
        self._correlation = None
        self._loaded = {
            "ghost_mode": False,
            "recon": False,
            "correlation": False,
            "security_agents": False,
        }
    
    # --- Lazy Loading ---
    
    def _load_ghost_mode(self):
        if not self._loaded["ghost_mode"]:
            try:
                from ghost_mode import GhostMode
                self._ghost_mode = GhostMode(self.workspace / "memory")
                self._loaded["ghost_mode"] = True
                print("[✓] Ghost Mode loaded")
            except Exception as e:
                print(f"[!] Ghost Mode failed: {e}")
    
    def _load_recon(self):
        if not self._loaded["recon"]:
            try:
                from enhanced_recon import KaiReconnaissance
                self._recon = KaiReconnaissance(self.workspace)
                self._loaded["recon"] = True
                print("[✓] Enhanced Recon loaded")
            except Exception as e:
                print(f"[!] Recon failed: {e}")
    
    def _load_correlation(self):
        if not self._loaded["correlation"]:
            try:
                from correlation_engine import CorrelationEngine
                self._correlation = CorrelationEngine(self.workspace)
                self._loaded["correlation"] = True
                print("[✓] Correlation Engine loaded")
            except Exception as e:
                print(f"[!] Correlation failed: {e}")
    
    def _load_security_agents(self):
        if not self._loaded["security_agents"]:
            try:
                from security_prompts import get_agent, list_agents
                self._security_agents = True
                self._loaded["security_agents"] = True
                print("[✓] Security Agents loaded")
            except Exception as e:
                print(f"[!] Security Agents failed: {e}")
    
    def load_all(self):
        """Pre-load all modules."""
        print("Loading Kai capabilities...")
        self._load_ghost_mode()
        self._load_recon()
        self._load_correlation()
        self._load_security_agents()
        print("=" * 40)
        print("All modules loaded!")
        return self
    
    # --- Ghost Mode Control ---
    
    def ghost_on(self, use_tor: bool = False) -> dict:
        """Activate Ghost Mode (anonymous operations)."""
        self._load_ghost_mode()
        if self._ghost_mode:
            return self._ghost_mode.activate(tor=use_tor)
        return {"error": "Ghost Mode not available"}
    
    def ghost_off(self) -> dict:
        """Deactivate Ghost Mode and clean all traces."""
        if self._ghost_mode:
            return self._ghost_mode.deactivate()
        return {"error": "Ghost Mode not available"}
    
    def ghost_status(self) -> dict:
        """Get Ghost Mode status."""
        if self._ghost_mode:
            return self._ghost_mode.get_status()
        return {"active": False}
    
    def ghost_browse(self, url: str) -> dict:
        """Browse URL anonymously."""
        if self._ghost_mode:
            return self._ghost_mode.browse(url)
        return {"error": "Ghost Mode not active"}
    
    # --- Enhanced Recon (Ghost Eye) ---
    
    async def recon_scan(self, target: str) -> dict:
        """Run comprehensive reconnaissance."""
        self._load_recon()
        if self._recon:
            result = await self._recon.comprehensive_recon(target)
            return {
                "target": result.target,
                "timestamp": result.timestamp,
                "dns_records": result.dns_records,
                "whois_info": result.whois_info,
                "ip_location": result.ip_location,
                "cms_detection": result.cms_detection,
                "certificate_count": len(result.certificate_info.get("certificates", [])) if result.certificate_info else 0,
            }
        return {"error": "Recon not available"}
    
    def recon_dns(self, target: str) -> dict:
        """Quick DNS lookup."""
        self._load_recon()
        if self._recon:
            return {"dns": self._recon.dns_lookup(target)}
        return {"error": "Recon not available"}
    
    def recon_whois(self, target: str) -> dict:
        """WHOIS lookup."""
        self._load_recon()
        if self._recon:
            return {"whois": self._recon.whois_lookup(target)}
        return {"error": "Recon not available"}
    
    def recon_headers(self, url: str) -> dict:
        """Get HTTP headers."""
        self._load_recon()
        if self._recon:
            return {"headers": self._recon.http_header_grabber(url)}
        return {"error": "Recon not available"}
    
    def recon_cms(self, url: str) -> dict:
        """Detect CMS."""
        self._load_recon()
        if self._recon:
            return {"cms": self._recon.cms_detection(url)}
        return {"error": "Recon not available"}
    
    # --- Correlation Engine (Ghost Scan) ---
    
    def correlate(self, findings: list) -> dict:
        """Correlate and score vulnerabilities."""
        self._load_correlation()
        if self._correlation:
            return self._correlation.correlate(findings)
        return {"error": "Correlation not available"}
    
    def score_risk(self, vuln: dict) -> dict:
        """Score a single vulnerability."""
        self._load_correlation()
        if self._correlation:
            return self._correlation.score_vulnerability(vuln)
        return {"error": "Correlation not available"}
    
    # --- Security Agents ---
    
    def get_security_agent(self, agent_name: str) -> str:
        """Get a security agent prompt."""
        self._load_security_agents()
        try:
            from security_prompts import get_agent
            return get_agent(agent_name)
        except Exception as e:
            return f"Error: {e}"
    
    def list_security_agents(self) -> list:
        """List available security agents."""
        try:
            from security_prompts import list_agents
            return list_agents()
        except:
            return []
    
    # --- Status Dashboard ---
    
    def status(self) -> dict:
        """Get full system status."""
        return {
            "loaded_modules": self._loaded,
            "ghost_mode_active": self.ghost_status().get("active", False),
            "workspace": str(self.workspace),
        }
    
    def dashboard(self) -> str:
        """Get text dashboard."""
        status = self.status()
        lines = [
            "=" * 50,
            "      🐕 Kai Control Panel",
            "=" * 50,
            "",
            "📦 Loaded Modules:",
        ]
        
        for module, loaded in status["loaded_modules"].items():
            mark = "✓" if loaded else "✗"
            lines.append(f"  [{mark}] {module}")
        
        lines.extend([
            "",
            "👻 Ghost Mode:",
            f"  Active: {status['ghost_mode_active']}",
            "",
            "🔍 Recon Commands:",
            "  panel.recon_scan(target)     - Full recon",
            "  panel.recon_dns(target)      - DNS lookup",
            "  panel.recon_whois(target)    - WHOIS",
            "  panel.recon_headers(url)     - HTTP headers",
            "  panel.recon_cms(url)         - Detect CMS",
            "",
            "🎯 Correlation:",
            "  panel.correlate(findings)    - Score vulns",
            "  panel.score_risk(vuln)     - Single score",
            "",
            "🛡️ Security Agents:",
            f"  Available: {', '.join(self.list_security_agents())}",
            "",
            "🔧 Ghost Commands:",
            "  panel.ghost_on()            - Activate",
            "  panel.ghost_off()           - Deactivate",
            "  panel.ghost_browse(url)     - Anonymous browse",
            "",
            "=" * 50,
        ])
        
        return "\n".join(lines)


# --- CLI Interface ---

def main():
    """Run the control panel interactively."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kai Control Panel")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="Workspace path")
    
    # Ghost Mode
    parser.add_argument("--ghost-on", action="store_true", help="Activate Ghost Mode")
    parser.add_argument("--ghost-off", action="store_true", help="Deactivate Ghost Mode")
    parser.add_argument("--ghost-status", action="store_true", help="Ghost Mode status")
    parser.add_argument("--ghost-browse", metavar="URL", help="Browse URL anonymously")
    
    # Recon
    parser.add_argument("--recon", metavar="TARGET", help="Run full recon on target")
    parser.add_argument("--dns", metavar="TARGET", help="DNS lookup")
    parser.add_argument("--whois", metavar="TARGET", help="WHOIS lookup")
    parser.add_argument("--headers", metavar="URL", help="Get HTTP headers")
    parser.add_argument("--cms", metavar="URL", help="Detect CMS")
    
    # Correlation
    parser.add_argument("--correlate", metavar="FILE", help="Correlate findings from file")
    parser.add_argument("--score", metavar="VULN", help="Score a vulnerability")
    
    # Security Agents
    parser.add_argument("--agents", action="store_true", help="List security agents")
    parser.add_argument("--agent", metavar="NAME", help="Get security agent prompt")
    
    # Dashboard
    parser.add_argument("--dashboard", action="store_true", help="Show full dashboard")
    
    args = parser.parse_args()
    
    workspace = Path(args.workspace)
    panel = KaiControlPanel(workspace)
    
    # Load all modules
    panel.load_all()
    print()
    
    # Execute commands
    if args.dashboard:
        print(panel.dashboard())
        return
    
    if args.ghost_on:
        result = panel.ghost_on()
        print(json.dumps(result, indent=2))
        return
    
    if args.ghost_off:
        result = panel.ghost_off()
        print(json.dumps(result, indent=2))
        return
    
    if args.ghost_status:
        result = panel.ghost_status()
        print(json.dumps(result, indent=2))
        return
    
    if args.ghost_browse:
        result = panel.ghost_browse(args.ghost_browse)
        print(json.dumps(result, indent=2))
        return
    
    if args.recon:
        result = asyncio.run(panel.recon_scan(args.recon))
        print(json.dumps(result, indent=2))
        return
    
    if args.dns:
        result = panel.recon_dns(args.dns)
        print(json.dumps(result, indent=2))
        return
    
    if args.whois:
        result = panel.recon_whois(args.whois)
        print(json.dumps(result, indent=2))
        return
    
    if args.headers:
        result = panel.recon_headers(args.headers)
        print(json.dumps(result, indent=2))
        return
    
    if args.cms:
        result = panel.recon_cms(args.cms)
        print(json.dumps(result, indent=2))
        return
    
    if args.agents:
        print("Available Security Agents:")
        for agent in panel.list_security_agents():
            print(f"  - {agent}")
        return
    
    if args.agent:
        prompt = panel.get_security_agent(args.agent)
        print(f"=== {args.agent.upper()} ===")
        print(prompt)
        return
    
    if args.correlate:
        # Read findings from file
        try:
            with open(args.correlate) as f:
                findings = json.load(f)
            result = panel.correlate(findings)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}")
        return
    
    if args.score:
        try:
            vuln = json.loads(args.score)
            result = panel.score_risk(vuln)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error parsing vuln: {e}")
        return
    
    # Default: show dashboard
    print(panel.dashboard())


if __name__ == "__main__":
    main()
