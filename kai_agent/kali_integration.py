"""
Kai Kali Integration - Real Kali Linux tool execution
Closes the major Kali tools gap with actual container execution
"""

import asyncio
import docker
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KaiKaliIntegration:
    """
    Real Kali Linux integration for Kai.
    Provides actual tool execution in isolated containers.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.tools_dir = workspace / "kali_tools"
        self.tools_dir.mkdir(exist_ok=True)
        self.container_name = "kai-kali-tools"
        self.image_name = "kalilinux/kali-rolling:latest"

        # Tool registry with installation commands
        self.tool_registry = {
            "nmap": {
                "description": "Network scanner",
                "install_cmd": "apt-get update && apt-get install -y nmap",
                "test_cmd": "nmap --version",
                "risk_level": "low",
            },
            "nikto": {
                "description": "Web server scanner",
                "install_cmd": "apt-get update && apt-get install -y nikto",
                "test_cmd": "nikto -Version",
                "risk_level": "low",
            },
            "sqlmap": {
                "description": "SQL injection tool",
                "install_cmd": "apt-get update && apt-get install -y sqlmap",
                "test_cmd": "sqlmap --version",
                "risk_level": "medium",
            },
            "metasploit": {
                "description": "Exploitation framework",
                "install_cmd": "apt-get update && apt-get install -y metasploit-framework",
                "test_cmd": "msfconsole --version",
                "risk_level": "high",
            },
            "burpsuite": {
                "description": "Web application security testing",
                "install_cmd": "apt-get update && apt-get install -y burpsuite",
                "test_cmd": "burpsuite --version || echo 'GUI tool'",
                "risk_level": "medium",
            },
            "wireshark": {
                "description": "Network protocol analyzer",
                "install_cmd": "apt-get update && apt-get install -y wireshark-common",
                "test_cmd": "tshark --version",
                "risk_level": "low",
            },
            "john": {
                "description": "Password cracker",
                "install_cmd": "apt-get update && apt-get install -y john",
                "test_cmd": "john --version",
                "risk_level": "medium",
            },
            "hashcat": {
                "description": "Advanced password recovery",
                "install_cmd": "apt-get update && apt-get install -y hashcat",
                "test_cmd": "hashcat --version",
                "risk_level": "high",
            },
            "hydra": {
                "description": "Network logon cracker",
                "install_cmd": "apt-get update && apt-get install -y hydra",
                "test_cmd": "hydra -h | head -1",
                "risk_level": "high",
            },
            "aircrack-ng": {
                "description": "Wireless network auditing",
                "install_cmd": "apt-get update && apt-get install -y aircrack-ng",
                "test_cmd": "aircrack-ng --help | head -1",
                "risk_level": "high",
            },
        }

    def check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    async def ensure_kali_container(self) -> bool:
        """Ensure Kali container is running"""
        if not self.check_docker_available():
            print("Docker not available - Kali tools require Docker")
            return False

        try:
            client = docker.from_env()

            # Check if container exists
            try:
                container = client.containers.get(self.container_name)
                if container.status != "running":
                    container.start()
                    print("Started existing Kali container")
                else:
                    print("Kali container already running")
            except docker.errors.NotFound:
                # Create new container
                print("Creating new Kali container...")
                container = client.containers.run(
                    self.image_name,
                    name=self.container_name,
                    detach=True,
                    tty=True,
                    volumes={str(self.workspace): {"bind": "/workspace", "mode": "rw"}},
                    command="tail -f /dev/null",  # Keep running
                )
                print("Kali container created and started")

            return True

        except Exception as e:
            print("Failed to setup Kali container: {}".format(e))
            return False

    async def install_tool(self, tool_name: str) -> Dict[str, Any]:
        """Install a specific tool in the Kali container"""
        if tool_name not in self.tool_registry:
            return {
                "success": False,
                "error": "Tool '{}' not found in registry".format(tool_name),
            }

        if not await self.ensure_kali_container():
            return {"success": False, "error": "Kali container not available"}

        tool_info = self.tool_registry[tool_name]

        try:
            client = docker.from_env()
            container = client.containers.get(self.container_name)

            # Install the tool
            print("Installing {}...".format(tool_name))
            result = container.exec_run(
                cmd=["bash", "-c", tool_info["install_cmd"]], tty=True
            )

            if result.exit_code == 0:
                print("{} installed successfully".format(tool_name))
                return {
                    "success": True,
                    "tool": tool_name,
                    "description": tool_info["description"],
                    "risk_level": tool_info["risk_level"],
                }
            else:
                return {
                    "success": False,
                    "error": "Installation failed: {}".format(result.output.decode()),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_tool_command(
        self, tool_name: str, command: str, timeout: int = 60
    ) -> Dict[str, Any]:
        """Execute a command with a specific tool"""
        if not await self.ensure_kali_container():
            return {"success": False, "error": "Kali container not available"}

        # Ensure tool is installed
        install_result = await self.install_tool(tool_name)
        if not install_result["success"]:
            return install_result

        try:
            client = docker.from_env()
            container = client.containers.get(self.container_name)

            # Execute the command
            print("Executing: {} {}".format(tool_name, command))
            result = container.exec_run(
                cmd=["bash", "-c", "cd /workspace && {}".format(command)],
                tty=True,
                timeout=timeout,
            )

            return {
                "success": result.exit_code == 0,
                "tool": tool_name,
                "command": command,
                "exit_code": result.exit_code,
                "output": result.output.decode("utf-8", errors="ignore"),
                "execution_time": timeout,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "command": command,
            }

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available Kali tools"""
        tools = []
        for name, info in self.tool_registry.items():
            tools.append(
                {
                    "name": name,
                    "description": info["description"],
                    "risk_level": info["risk_level"],
                    "category": self._categorize_tool(name),
                }
            )
        return tools

    async def scan_with_nmap(
        self, target: str, scan_type: str = "basic"
    ) -> Dict[str, Any]:
        """Perform nmap scan"""
        scan_commands = {
            "basic": "nmap -T4 -F {}".format(target),
            "full": "nmap -T4 -A -v {}".format(target),
            "stealth": "nmap -sS -T2 {}".format(target),
            "service": "nmap -sV -T4 {}".format(target),
        }

        command = scan_commands.get(scan_type, scan_commands["basic"])

        result = await self.execute_tool_command("nmap", command, timeout=300)

        if result["success"]:
            # Parse basic results
            lines = result["output"].split("\n")
            open_ports = []
            for line in lines:
                if "/tcp" in line and "open" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        port = parts[0].split("/")[0]
                        service = parts[2] if len(parts) > 2 else "unknown"
                        open_ports.append({"port": port, "service": service})

            result["parsed_results"] = {
                "open_ports": open_ports,
                "total_ports_found": len(open_ports),
            }

        return result

    async def web_scan_with_nikto(self, url: str) -> Dict[str, Any]:
        """Perform web server scan with nikto"""
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        command = "nikto -h {} -Tuning 123".format(url)

        result = await self.execute_tool_command("nikto", command, timeout=300)

        if result["success"]:
            # Parse nikto output for vulnerabilities
            lines = result["output"].split("\n")
            vulnerabilities = []
            for line in lines:
                if "+ " in line and ("vulnerable" in line.lower() or "OSVDB" in line):
                    vulnerabilities.append(line.strip())

            result["parsed_results"] = {
                "vulnerabilities_found": len(vulnerabilities),
                "vulnerability_details": vulnerabilities[:10],  # First 10
            }

        return result

    async def sql_test_with_sqlmap(self, url: str) -> Dict[str, Any]:
        """Test for SQL injection with sqlmap"""
        command = "sqlmap -u '{}' --batch --risk=3 --level=5".format(url)

        result = await self.execute_tool_command("sqlmap", command, timeout=600)

        if result["success"]:
            # Parse sqlmap results
            output = result["output"]
            injectable = "Parameter:" in output and (
                "might be injectable" in output or "is vulnerable" in output
            )

            result["parsed_results"] = {
                "sql_injection_found": injectable,
                "parameter_details": "Check full output for injection details",
            }

        return result

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize a tool by its primary function"""
        categories = {
            "scanning": ["nmap", "nikto", "masscan"],
            "exploitation": ["metasploit", "sqlmap"],
            "web": ["burpsuite", "nikto"],
            "network": ["nmap", "wireshark"],
            "password": ["john", "hashcat", "hydra"],
            "wireless": ["aircrack-ng"],
        }

        for category, tools in categories.items():
            if tool_name in tools:
                return category

        return "general"

    async def cleanup_containers(self) -> Dict[str, Any]:
        """Clean up Kali containers"""
        try:
            client = docker.from_env()

            # Stop and remove our container
            try:
                container = client.containers.get(self.container_name)
                container.stop()
                container.remove()
                print("Kali container cleaned up")
                return {"success": True, "message": "Container cleaned up"}
            except docker.errors.NotFound:
                return {"success": True, "message": "No container to clean"}

        except Exception as e:
            return {"success": False, "error": str(e)}
