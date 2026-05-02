"""
Kai NetworkMesh — discovers, connects, and orchestrates devices on your local network.
Supports Windows (WinRM), Linux/Mac (SSH), smart TVs (UPnP), phones (ADB), and Kai agent nodes.
"""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class NetworkDevice:
    """A discovered device on the network."""
    id: str
    name: str
    ip_address: str
    mac_address: str
    device_type: str  # windows, linux, mac, phone, tv, iot, unknown
    os_version: str = ""
    open_ports: list[int] = field(default_factory=list)
    connection_method: str = ""  # winrm, ssh, kai_agent, adb, upnp, none
    connection_status: str = "discovered"  # discovered, connecting, connected, failed
    credentials: dict = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    last_seen: str = field(default_factory=_utc_now_iso)
    last_heartbeat: str = field(default_factory=_utc_now_iso)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class NetworkMesh:
    """Discovers and manages network devices for distributed task execution."""

    def __init__(self, workspace: Path, save_path: Path | None = None) -> None:
        self.workspace = workspace
        self.save_path = save_path or (workspace / "memory" / "network_mesh.json")
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        self.devices: dict[str, NetworkDevice] = {}
        self._lock = threading.Lock()
        self._scan_thread: threading.Thread | None = None
        self._scanning = False

        # Network config
        self.local_ip = self._get_local_ip()
        self.subnet = self._get_subnet()
        self.scan_range = self.subnet + "/24"

        # Connection pools
        self._ssh_connections: dict[str, Any] = {}
        self._winrm_connections: dict[str, Any] = {}

        self._load()

    def _load(self) -> None:
        if self.save_path.exists():
            try:
                data = json.loads(self.save_path.read_text(encoding="utf-8"))
                for dev_data in data.get("devices", []):
                    dev = NetworkDevice(**dev_data)
                    self.devices[dev.id] = dev
            except Exception:
                pass

    def _save(self) -> None:
        payload = {
            "devices": [d.to_dict() for d in self.devices.values()],
            "local_ip": self.local_ip,
            "subnet": self.subnet,
            "updated_at": _utc_now_iso(),
        }
        self.save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _get_subnet(self) -> str:
        parts = self.local_ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3])
        return "192.168.1"

    # === DISCOVERY ===

    def discover(self, scan_type: str = "quick") -> list[dict]:
        """Discover devices on the network."""
        self._scanning = True
        results: list[dict] = []

        if scan_type == "quick":
            results = self._ping_sweep()
        elif scan_type == "deep":
            results = self._ping_sweep()
            results.extend(self._arp_scan())
            results.extend(self._mdns_scan())
        elif scan_type == "port_scan":
            for dev in self.devices.values():
                dev.open_ports = self._scan_ports(dev.ip_address)

        self._save()
        self._scanning = False
        return results

    def _ping_sweep(self) -> list[dict]:
        """Quick ping sweep of the subnet."""
        results = []
        subnet = self.subnet

        if platform.system() == "Windows":
            # Windows ping
            for i in range(1, 255):
                ip = f"{subnet}.{i}"
                try:
                    proc = subprocess.run(
                        ["ping", "-n", "1", "-w", "500", ip],
                        capture_output=True, text=True, timeout=2
                    )
                    if "TTL" in proc.stdout or "Reply" in proc.stdout:
                        dev = self._classify_device(ip)
                        if dev:
                            results.append(dev.to_dict())
                            self.devices[dev.id] = dev
                except Exception:
                    pass
        else:
            # Linux/Mac ping
            for i in range(1, 255):
                ip = f"{subnet}.{i}"
                try:
                    proc = subprocess.run(
                        ["ping", "-c", "1", "-W", "1", ip],
                        capture_output=True, text=True, timeout=2
                    )
                    if proc.returncode == 0:
                        dev = self._classify_device(ip)
                        if dev:
                            results.append(dev.to_dict())
                            self.devices[dev.id] = dev
                except Exception:
                    pass

        return results

    def _arp_scan(self) -> list[dict]:
        """Use ARP to discover devices (more reliable than ping)."""
        results = []
        try:
            if platform.system() == "Windows":
                proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
                for line in proc.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and "." in parts[0] and "-" in parts[1]:
                        ip = parts[0]
                        mac = parts[1].replace("-", ":").upper()
                        if ip != self.local_ip and not ip.startswith("255"):
                            dev = self._get_or_create_device(ip, mac)
                            results.append(dev.to_dict())
            else:
                proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
                for line in proc.stdout.splitlines():
                    if "(" in line and ")" in line:
                        ip = line.split("(")[1].split(")")[0]
                        mac = ""
                        if "at" in line:
                            mac = line.split("at")[-1].strip().split()[0].replace("-", ":").upper()
                        if ip != self.local_ip:
                            dev = self._get_or_create_device(ip, mac)
                            results.append(dev.to_dict())
        except Exception:
            pass
        return results

    def _mdns_scan(self) -> list[dict]:
        """Scan for mDNS/Bonjour services (phones, TVs, smart devices)."""
        results = []
        try:
            # Try to discover via socket multicast
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Query for _googlecast._tcp.local. (Chromecast/Android TV)
            # and _airplay._tcp.local. (Apple devices)
            services = [
                "_googlecast._tcp.local.",
                "_airplay._tcp.local.",
                "_ssh._tcp.local.",
                "_http._tcp.local.",
            ]

            for service in services:
                try:
                    sock.sendto(
                        b"",
                        ("224.0.0.251", 5353)
                    )
                except Exception:
                    pass
        except Exception:
            pass
        return results

    def _classify_device(self, ip: str, mac: str = "") -> Optional[NetworkDevice]:
        """Classify a device based on IP, MAC, and port scans."""
        dev = self._get_or_create_device(ip, mac)

        # Quick port scan to determine type
        common_ports = {
            135: "windows",
            139: "windows",
            445: "windows",
            3389: "windows",  # RDP
            22: "linux",
            8080: "linux",
            5000: "linux",
            80: "web_device",
            443: "web_device",
            8009: "tv",  # Chromecast
            8443: "tv",
            554: "camera",  # RTSP
        }

        open_ports = self._scan_ports(ip, ports=list(common_ports.keys()))
        dev.open_ports = open_ports

        # Classify based on ports
        device_type = "unknown"
        for port, dev_type in common_ports.items():
            if port in open_ports:
                device_type = dev_type
                break

        # MAC OUI lookup for better classification
        if mac:
            oui_prefix = mac.replace(":", "").upper()[:6]
            # Common OUIs
            if oui_prefix in ("001B63", "00D023", "001E8C", "5C4979"):
                device_type = "tv"
            elif oui_prefix in ("001A11", "002608", "0024E4"):
                device_type = "phone"
            elif oui_prefix in ("001560", "0017C4", "001E8E"):
                device_type = "windows"

        dev.device_type = device_type
        dev.last_seen = _utc_now_iso()

        # Set connection method
        if 5985 in open_ports or 5986 in open_ports:
            dev.connection_method = "winrm"
            dev.capabilities.append("winrm")
        elif 22 in open_ports:
            dev.connection_method = "ssh"
            dev.capabilities.append("ssh")
        elif 8009 in open_ports or 8443 in open_ports:
            dev.connection_method = "upnp"
            dev.capabilities.append("cast")
        elif 5555 in open_ports:
            dev.connection_method = "adb"
            dev.capabilities.append("adb")

        return dev

    def _scan_ports(self, ip: str, ports: list[int] | None = None) -> list[int]:
        """Scan common ports on a device."""
        if ports is None:
            ports = [22, 80, 443, 445, 3389, 5985, 5986, 8080, 8009, 8443, 5555]

        open_ports = []
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                pass
        return open_ports

    def _get_or_create_device(self, ip: str, mac: str = "") -> NetworkDevice:
        """Get existing device or create new one."""
        # Check by IP first
        for dev in self.devices.values():
            if dev.ip_address == ip:
                dev.last_seen = _utc_now_iso()
                return dev

        # Create new
        device_id = f"dev_{ip.replace('.', '_')}"
        name = mac if mac else f"device_{ip.split('.')[-1]}"
        return NetworkDevice(
            id=device_id,
            name=name,
            ip_address=ip,
            mac_address=mac,
            device_type="unknown",
        )

    # === CONNECTION ===

    def connect_device(self, device_id: str, method: str = "auto", credentials: dict | None = None) -> dict:
        """Connect to a device."""
        with self._lock:
            dev = self.devices.get(device_id)
            if not dev:
                return {"ok": False, "error": f"Device {device_id} not found"}

            if method == "auto":
                method = dev.connection_method or self._detect_connection_method(dev)

            if not method:
                return {"ok": False, "error": "No connection method available for this device"}

            dev.connection_status = "connecting"
            dev.credentials = credentials or dev.credentials

            try:
                if method == "winrm":
                    result = self._connect_winrm(dev, credentials)
                elif method == "ssh":
                    result = self._connect_ssh(dev, credentials)
                elif method == "kai_agent":
                    result = self._connect_kai_agent(dev, credentials)
                elif method == "adb":
                    result = self._connect_adb(dev)
                elif method == "upnp":
                    result = self._connect_upnp(dev)
                else:
                    result = {"ok": False, "error": f"Unsupported connection method: {method}"}

                if result.get("ok"):
                    dev.connection_status = "connected"
                    dev.connection_method = method
                    dev.capabilities.append(method)
                    dev.last_heartbeat = _utc_now_iso()
                else:
                    dev.connection_status = "failed"

                self._save()
                return result
            except Exception as exc:
                dev.connection_status = "failed"
                self._save()
                return {"ok": False, "error": str(exc)}

    def _detect_connection_method(self, dev: NetworkDevice) -> str:
        """Auto-detect best connection method for a device."""
        if 5985 in dev.open_ports or 5986 in dev.open_ports:
            return "winrm"
        if 22 in dev.open_ports:
            return "ssh"
        if 8009 in dev.open_ports or 8443 in dev.open_ports:
            return "upnp"
        if 5555 in dev.open_ports:
            return "adb"
        if dev.device_type == "windows":
            return "winrm"
        if dev.device_type in ("linux", "mac"):
            return "ssh"
        return ""

    def _connect_winrm(self, dev: NetworkDevice, credentials: dict | None = None) -> dict:
        """Connect via WinRM (Windows Remote Management)."""
        creds = credentials or dev.credentials
        username = creds.get("username", "")
        password = creds.get("password", "")

        # Test WinRM connection
        try:
            if platform.system() == "Windows":
                # Use PowerShell to test WinRM
                cmd = f'Invoke-Command -ComputerName {dev.ip_address} -ScriptBlock {{ hostname }}'
                if username:
                    cmd = f'$secpasswd = ConvertTo-SecureString "{password}" -AsPlainText -Force; $cred = New-Object System.Management.Automation.PSCredential("{username}", $secpasswd); {cmd} -Credential $cred'

                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    dev.name = proc.stdout.strip()
                    dev.os_version = "Windows"
                    return {"ok": True, "message": f"Connected to {dev.name} via WinRM"}
                return {"ok": False, "error": proc.stderr.strip()[:500]}
            else:
                # Linux: try with python-winrm if available
                try:
                    import winrm
                    session = winrm.Session(
                        f"http://{dev.ip_address}:5985/wsman",
                        auth=(username, password) if username else None,
                    )
                    result = session.run_cmd("hostname")
                    if result.status_code == 0:
                        dev.name = result.std_out.decode().strip()
                        return {"ok": True, "message": f"Connected to {dev.name} via WinRM"}
                except ImportError:
                    pass
                return {"ok": False, "error": "WinRM not supported from this platform. Install python-winrm or connect from Windows."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _connect_ssh(self, dev: NetworkDevice, credentials: dict | None = None) -> dict:
        """Connect via SSH."""
        creds = credentials or dev.credentials
        username = creds.get("username", "root")
        password = creds.get("password", "")
        key_file = creds.get("key_file", "")

        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if key_file:
                ssh.connect(dev.ip_address, username=username, key_filename=key_file, timeout=10)
            else:
                ssh.connect(dev.ip_address, username=username, password=password, timeout=10)

            # Get hostname and OS info
            stdin, stdout, stderr = ssh.exec_command("uname -a && hostname")
            output = stdout.read().decode().strip()
            dev.name = output.split("\n")[-1] if output else dev.ip_address
            dev.os_version = output.split("\n")[0] if output else "unknown"

            self._ssh_connections[dev.id] = ssh
            return {"ok": True, "message": f"Connected to {dev.name} via SSH"}
        except ImportError:
            return {"ok": False, "error": "paramiko not installed. Run: pip install paramiko"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _connect_kai_agent(self, dev: NetworkDevice, credentials: dict | None = None) -> dict:
        """Connect to a device running a Kai agent node."""
        port = credentials.get("port", 8765) if credentials else 8765
        try:
            import urllib.request
            url = f"http://{dev.ip_address}:{port}/health"
            req = urllib.request.Request(url, timeout=5)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                dev.name = data.get("name", dev.ip_address)
                dev.os_version = data.get("os", "unknown")
                return {"ok": True, "message": f"Connected to Kai agent: {dev.name}"}
        except Exception as exc:
            return {"ok": False, "error": f"Kai agent not responding: {exc}"}

    def _connect_adb(self, dev: NetworkDevice) -> dict:
        """Connect via ADB (Android Debug Bridge)."""
        try:
            proc = subprocess.run(
                ["adb", "connect", f"{dev.ip_address}:5555"],
                capture_output=True, text=True, timeout=10
            )
            if "connected" in proc.stdout.lower() or "already connected" in proc.stdout.lower():
                dev.connection_method = "adb"
                dev.device_type = "phone"
                return {"ok": True, "message": f"Connected to Android device via ADB"}
            return {"ok": False, "error": proc.stderr.strip()[:500] or "ADB connection failed"}
        except FileNotFoundError:
            return {"ok": False, "error": "ADB not found. Install Android SDK platform-tools."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _connect_upnp(self, dev: NetworkDevice) -> dict:
        """Connect via UPnP (smart TVs, Chromecast)."""
        try:
            # Simple UPnP discovery via HTTP
            import urllib.request
            url = f"http://{dev.ip_address}:8008/setup/eureka_info"
            req = urllib.request.Request(url, timeout=5)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                dev.name = data.get("name", dev.ip_address)
                dev.device_type = "tv"
                return {"ok": True, "message": f"Connected to {dev.name} (Chromecast/TV)"}
        except Exception:
            # Try generic UPnP
            try:
                url = f"http://{dev.ip_address}:8443/"
                req = urllib.request.Request(url, timeout=5)
                with urllib.request.urlopen(req) as resp:
                    dev.device_type = "tv"
                    return {"ok": True, "message": f"Connected to device via UPnP"}
            except Exception as exc:
                return {"ok": False, "error": f"UPnP connection failed: {exc}"}

    # === EXECUTION ===

    def run_command(self, device_id: str, command: str, timeout: int = 30) -> dict:
        """Run a command on a connected device."""
        with self._lock:
            dev = self.devices.get(device_id)
            if not dev:
                return {"ok": False, "error": f"Device {device_id} not found"}
            if dev.connection_status != "connected":
                return {"ok": False, "error": f"Device {device_id} is not connected"}

            method = dev.connection_method

            try:
                if method == "winrm":
                    return self._run_winrm(dev, command, timeout)
                elif method == "ssh":
                    return self._run_ssh(dev, command, timeout)
                elif method == "kai_agent":
                    return self._run_kai_agent(dev, command, timeout)
                elif method == "adb":
                    return self._run_adb(dev, command, timeout)
                else:
                    return {"ok": False, "error": f"No execution method available for {method}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def _run_winrm(self, dev: NetworkDevice, command: str, timeout: int) -> dict:
        """Run command via WinRM."""
        try:
            if platform.system() == "Windows":
                cmd = f'Invoke-Command -ComputerName {dev.ip_address} -ScriptBlock {{ {command} }}'
                if dev.credentials.get("username"):
                    cmd = (
                        f'$secpasswd = ConvertTo-SecureString "{dev.credentials.get("password")}" -AsPlainText -Force; '
                        f'$cred = New-Object System.Management.Automation.PSCredential("{dev.credentials.get("username")}", $secpasswd); '
                        f'{cmd} -Credential $cred'
                    )
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, timeout=timeout
                )
                return {
                    "ok": proc.returncode == 0,
                    "stdout": proc.stdout.strip()[:8000],
                    "stderr": proc.stderr.strip()[:4000],
                }
            else:
                try:
                    import winrm
                    session = winrm.Session(
                        f"http://{dev.ip_address}:5985/wsman",
                        auth=(dev.credentials.get("username", ""), dev.credentials.get("password", "")),
                    )
                    result = session.run_cmd("powershell", [command])
                    return {
                        "ok": result.status_code == 0,
                        "stdout": result.std_out.decode().strip()[:8000],
                        "stderr": result.std_err.decode().strip()[:4000],
                    }
                except ImportError:
                    return {"ok": False, "error": "python-winrm not installed"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_ssh(self, dev: NetworkDevice, command: str, timeout: int) -> dict:
        """Run command via SSH."""
        ssh = self._ssh_connections.get(dev.id)
        if not ssh:
            return {"ok": False, "error": "No SSH connection established"}

        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            output = stdout.read().decode()
            errors = stderr.read().decode()
            exit_code = stdout.channel.recv_exit_status()
            return {
                "ok": exit_code == 0,
                "stdout": output.strip()[:8000],
                "stderr": errors.strip()[:4000],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_kai_agent(self, dev: NetworkDevice, command: str, timeout: int) -> dict:
        """Run command on a Kai agent node."""
        port = dev.credentials.get("port", 8765)
        try:
            import urllib.request
            url = f"http://{dev.ip_address}:{port}/execute"
            data = json.dumps({"command": command, "timeout": timeout}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _run_adb(self, dev: NetworkDevice, command: str, timeout: int) -> dict:
        """Run command via ADB."""
        try:
            proc = subprocess.run(
                ["adb", "-s", f"{dev.ip_address}:5555", "shell", command],
                capture_output=True, text=True, timeout=timeout
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout.strip()[:8000],
                "stderr": proc.stderr.strip()[:4000],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # === MANAGEMENT ===

    def disconnect_device(self, device_id: str) -> dict:
        """Disconnect from a device."""
        with self._lock:
            dev = self.devices.get(device_id)
            if not dev:
                return {"ok": False, "error": f"Device {device_id} not found"}

            # Close SSH connection
            if dev.id in self._ssh_connections:
                try:
                    self._ssh_connections[dev.id].close()
                except Exception:
                    pass
                del self._ssh_connections[dev.id]

            dev.connection_status = "discovered"
            dev.last_heartbeat = _utc_now_iso()
            self._save()
            return {"ok": True, "message": f"Disconnected from {dev.name}"}

    def list_devices(self) -> list[dict]:
        """List all discovered devices."""
        return [d.to_dict() for d in self.devices.values()]

    def status(self) -> dict:
        """Get mesh status."""
        devices = list(self.devices.values())
        connected = [d for d in devices if d.connection_status == "connected"]
        by_type = {}
        for d in devices:
            by_type[d.device_type] = by_type.get(d.device_type, 0) + 1

        return {
            "total_devices": len(devices),
            "connected": len(connected),
            "by_type": by_type,
            "local_ip": self.local_ip,
            "subnet": self.subnet,
            "devices": [
                {
                    "id": d.id,
                    "name": d.name,
                    "ip": d.ip_address,
                    "type": d.device_type,
                    "status": d.connection_status,
                    "method": d.connection_method,
                }
                for d in devices
            ],
        }

    def deploy_agent(self, device_id: str) -> dict:
        """Deploy a Kai agent to a device."""
        with self._lock:
            dev = self.devices.get(device_id)
            if not dev:
                return {"ok": False, "error": f"Device {device_id} not found"}

            if dev.device_type == "windows":
                return self._deploy_windows_agent(dev)
            elif dev.device_type in ("linux", "mac"):
                return self._deploy_linux_agent(dev)
            elif dev.device_type == "phone":
                return {"ok": False, "error": "Deploy agent via ADB: connect the phone first"}
            else:
                return {"ok": False, "error": f"Agent deployment not supported for {dev.device_type}"}

    def _deploy_windows_agent(self, dev: NetworkDevice) -> dict:
        """Deploy Kai agent to Windows device."""
        agent_script = self._get_agent_script()
        script_path = f"\\\\{dev.ip_address}\\C$\\Users\\Public\\kai_agent.py"

        try:
            # Try to copy via SMB
            import shutil
            from pathlib import Path as P
            agent_file = self.workspace / "kai_agent_node.py"
            agent_file.write_text(agent_script, encoding="utf-8")

            # Copy to remote machine
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Copy-Item -Path "{agent_file}" -Destination "{script_path}" -Force'],
                capture_output=True, text=True, timeout=30
            )

            # Schedule task to run it
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Invoke-Command -ComputerName {dev.ip_address} -ScriptBlock {{ python "{script_path}" --daemon }}'],
                capture_output=True, text=True, timeout=30
            )

            return {"ok": True, "message": f"Kai agent deployed to {dev.name}. Starting agent..."}
        except Exception as exc:
            return {"ok": False, "error": f"Deployment failed: {exc}"}

    def _deploy_linux_agent(self, dev: NetworkDevice) -> dict:
        """Deploy Kai agent to Linux device."""
        agent_script = self._get_agent_script()

        try:
            ssh = self._ssh_connections.get(dev.id)
            if not ssh:
                return {"ok": False, "error": "SSH connection required for deployment"}

            # Copy script
            import paramiko
            sftp = ssh.open_sftp()
            remote_path = "/tmp/kai_agent_node.py"
            sftp.put(StringIO(agent_script), remote_path)
            sftp.close()

            # Start agent
            ssh.exec_command(f"chmod +x {remote_path} && nohup python3 {remote_path} --daemon &")
            return {"ok": True, "message": f"Kai agent deployed to {dev.name}. Starting agent..."}
        except Exception as exc:
            return {"ok": False, "error": f"Deployment failed: {exc}"}

    def _get_agent_script(self) -> str:
        """Get the Kai agent node script for deployment."""
        agent_path = Path(__file__).parent / "kai_agent_node.py"
        if agent_path.exists():
            return agent_path.read_text(encoding="utf-8")
        return self._generate_agent_script()

    def _generate_agent_script(self) -> str:
        """Generate a minimal Kai agent node script."""
        return '''#!/usr/bin/env python3
"""Lightweight Kai agent node for remote execution."""
import json
import socket
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8765
WORKSPACE = Path.home() / ".kai_node"
WORKSPACE.mkdir(exist_ok=True)

class KaiAgentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "name": socket.gethostname(),
                "os": sys.platform,
                "status": "running",
                "port": PORT,
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            command = data.get("command", "")
            timeout = data.get("timeout", 30)

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(WORKSPACE),
                )
                response = {
                    "ok": result.returncode == 0,
                    "stdout": result.stdout[:8000],
                    "stderr": result.stderr[:4000],
                }
            except subprocess.TimeoutExpired:
                response = {"ok": False, "error": f"Command timed out after {timeout}s"}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

def run_daemon():
    server = HTTPServer(("0.0.0.0", PORT), KaiAgentHandler)
    print(f"Kai agent node listening on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        print(f"Kai agent node v1.0 — run with --daemon to start server")
        print(f"Health check: http://localhost:{PORT}/health")
'''

    def heartbeat(self, device_id: str) -> dict:
        """Send heartbeat check to a connected device."""
        with self._lock:
            dev = self.devices.get(device_id)
            if not dev:
                return {"ok": False, "error": f"Device {device_id} not found"}
            if dev.connection_status != "connected":
                return {"ok": False, "error": "Device not connected"}

            # Quick ping to check connectivity
            try:
                result = self.run_command(device_id, "echo pong", timeout=5)
                if result.get("ok"):
                    dev.last_heartbeat = _utc_now_iso()
                    self._save()
                    return {"ok": True, "message": "Device responsive"}
                return {"ok": False, "error": "Device not responding"}
            except Exception as exc:
                dev.connection_status = "failed"
                self._save()
                return {"ok": False, "error": str(exc)}
