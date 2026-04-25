"""
Kai Signals — wireless awareness for the companion.

Detects and monitors:
- WiFi networks (signal strength, names, channels)
- Bluetooth devices (nearby devices, types)
- Network interfaces (IP, status)

Usage:
    from kai_agent.kai_signals import KaiSignals
    signals = KaiSignals()
    wifi = signals.scan_wifi()
    bt = signals.scan_bluetooth()

Platform support:
- Linux: nmcli (WiFi), bluetoothctl/hcitool (BT)
- Windows: netsh (WiFi), PowerShell BLE (BT)
- macOS: networksetup (WiFi), system_profiler (BT)
"""

import json
import os
import platform
import re
import shutil
import socket
import subprocess
from ipaddress import ip_address, ip_interface
from typing import Optional


class KaiSignals:
    def __init__(self):
        self.system = platform.system()
        self._reverse_lookup_cache: dict[str, str] = {}

    # ─── WiFi ───

    def scan_wifi(self) -> dict:
        """Scan for nearby WiFi networks."""
        if self.system == "Linux":
            return self._scan_wifi_linux()
        elif self.system == "Windows":
            return self._scan_wifi_windows()
        elif self.system == "Darwin":
            return self._scan_wifi_macos()
        return {"available": False, "error": "unsupported platform"}

    def get_current_wifi(self) -> dict:
        """Get the currently connected WiFi network."""
        if self.system == "Linux":
            return self._current_wifi_linux()
        elif self.system == "Windows":
            return self._current_wifi_windows()
        elif self.system == "Darwin":
            return self._current_wifi_macos()
        return {"connected": False}

    def _scan_wifi_linux(self) -> dict:
        try:
            # Try nmcli first
            if shutil.which("nmcli"):
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,FREQ", "device", "wifi", "list", "--rescan", "yes"],
                    capture_output=True, text=True, timeout=15
                )
                networks = []
                seen = set()
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ssid = parts[0].strip()
                        if not ssid or ssid in seen:
                            continue
                        seen.add(ssid)
                        networks.append({
                            "ssid": ssid,
                            "signal": int(parts[1]) if parts[1].isdigit() else 0,
                            "security": parts[2] if len(parts) > 2 else "",
                            "freq": parts[3] if len(parts) > 3 else "",
                        })
                networks.sort(key=lambda n: n["signal"], reverse=True)
                return {"available": True, "networks": networks, "count": len(networks)}

            # Fallback: iwlist
            iface = self._get_wifi_interface()
            if iface:
                result = subprocess.run(
                    ["iwlist", iface, "scan"],
                    capture_output=True, text=True, timeout=15
                )
                return self._parse_iwlist(result.stdout)

        except Exception as e:
            return {"available": False, "error": str(e)}
        return {"available": False, "error": "no wifi tool found"}

    def _scan_wifi_windows(self) -> dict:
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, timeout=15
            )
            return self._parse_netsh_wifi(result.stdout)
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _scan_wifi_macos(self) -> dict:
        try:
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                capture_output=True, text=True, timeout=15
            )
            return self._parse_airport(result.stdout)
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _current_wifi_linux(self) -> dict:
        try:
            if shutil.which("nmcli"):
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,BSSID", "device", "wifi"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 3 and parts[0] == "yes":
                        return {
                            "connected": True,
                            "ssid": parts[1],
                            "signal": int(parts[2]) if parts[2].isdigit() else 0,
                            "bssid": parts[3] if len(parts) > 3 else "",
                        }
        except Exception:
            pass
        return {"connected": False}

    def _current_wifi_windows(self) -> dict:
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10
            )
            ssid_match = re.search(r"SSID\s*:\s*(.+)", result.stdout)
            signal_match = re.search(r"Signal\s*:\s*(\d+)", result.stdout)
            if ssid_match:
                return {
                    "connected": True,
                    "ssid": ssid_match.group(1).strip(),
                    "signal": int(signal_match.group(1)) if signal_match else 0,
                }
        except Exception:
            pass
        return {"connected": False}

    def _current_wifi_macos(self) -> dict:
        try:
            result = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True, text=True, timeout=10
            )
            if "Current Wi-Fi Network:" in result.stdout:
                ssid = result.stdout.split("Current Wi-Fi Network:")[1].strip()
                return {"connected": True, "ssid": ssid}
        except Exception:
            pass
        return {"connected": False}

    # ─── Bluetooth ───

    def scan_bluetooth(self) -> dict:
        """Scan for nearby Bluetooth devices."""
        if self.system == "Linux":
            return self._scan_bt_linux()
        elif self.system == "Windows":
            return self._scan_bt_windows()
        elif self.system == "Darwin":
            return self._scan_bt_macos()
        return {"available": False, "error": "unsupported platform"}

    def _scan_bt_linux(self) -> dict:
        devices = []
        try:
            # Try bluetoothctl
            if shutil.which("bluetoothctl"):
                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n"):
                    match = re.match(r"Device\s+([0-9A-F:]+)\s+(.*)", line, re.IGNORECASE)
                    if match:
                        devices.append({
                            "mac": match.group(1),
                            "name": match.group(2).strip(),
                            "type": "paired",
                        })

                # Also check for connected devices
                result_conn = subprocess.run(
                    ["bluetoothctl", "info"],
                    capture_output=True, text=True, timeout=10
                )

            # Try hcitool for nearby scan (quick)
            elif shutil.which("hcitool"):
                subprocess.run(["hcitool", "scan", "--flush"], capture_output=True, timeout=12)

        except Exception as e:
            return {"available": False, "error": str(e), "devices": devices}

        return {"available": True, "devices": devices, "count": len(devices)}

    def _scan_bt_windows(self) -> dict:
        devices = []
        try:
            # Use multiple Windows sources because some systems expose Bluetooth
            # devices via PnP without the Bluetooth class tag.
            ps_cmd = r"""
$devices = New-Object System.Collections.ArrayList

if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) {
  Get-PnpDevice -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Class -match 'Bluetooth' -or
      $_.FriendlyName -match 'Bluetooth' -or
      $_.InstanceId -match '^BTH'
    } |
    ForEach-Object {
      [void]$devices.Add([pscustomobject]@{
        Name = if ($_.FriendlyName) { $_.FriendlyName } else { $_.Class }
        Status = $_.Status
        Class = $_.Class
        DeviceID = $_.InstanceId
      })
    }
}

Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
  Where-Object {
    $_.PNPClass -match 'Bluetooth' -or
    $_.Name -match 'Bluetooth' -or
    $_.DeviceID -match '^BTH'
  } |
  ForEach-Object {
    [void]$devices.Add([pscustomobject]@{
      Name = $_.Name
      Status = $_.Status
      Class = $_.PNPClass
      DeviceID = $_.DeviceID
    })
  }

$devices | Select-Object Name, Status, Class, DeviceID -Unique | ConvertTo-Json -Compress
"""
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout.strip():
                try:
                    parsed = json.loads(result.stdout)
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    seen = set()
                    for dev in parsed:
                        name = dev.get("Name", "Unknown")
                        if not name or name == "Bluetooth":
                            continue
                        dedupe_key = (
                            str(dev.get("DeviceID", "")).strip().lower()
                            or name.strip().lower()
                        )
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        devices.append({
                            "name": name,
                            "status": dev.get("Status", ""),
                            "type": self._classify_bt_device_type(
                                name,
                                dev.get("Class", ""),
                                dev.get("DeviceID", ""),
                            ),
                        })
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            return {"available": False, "error": str(e)}

        return {"available": True, "devices": devices, "count": len(devices)}

    def _scan_bt_macos(self) -> dict:
        devices = []
        try:
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType", "-json"],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout.strip():
                parsed = json.loads(result.stdout)
                bt_data = parsed.get("SPBluetoothDataType", [])
                for controller in bt_data:
                    # Paired devices
                    for key in ("device_connected", "device_not_connected"):
                        for dev in controller.get(key, []):
                            name = dev.get("device_name", "Unknown")
                            devices.append({
                                "name": name,
                                "type": "connected" if key == "device_connected" else "paired",
                            })
        except Exception as e:
            return {"available": False, "error": str(e)}

        return {"available": True, "devices": devices, "count": len(devices)}

    # ─── Network Interfaces ───

    def get_interfaces(self) -> dict:
        """Get all network interfaces and their status."""
        interfaces = []
        try:
            if self.system == "Linux":
                result = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=10)
                if result.stdout.strip():
                    parsed = json.loads(result.stdout)
                    for iface in parsed:
                        addrs = [a["local"] for a in iface.get("addr_info", [])]
                        interfaces.append({
                            "name": iface.get("ifname", ""),
                            "state": iface.get("operstate", ""),
                            "addresses": addrs,
                            "type": self._guess_iface_type(iface.get("ifname", "")),
                        })
            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        r"""
$rows = foreach ($adapter in Get-NetAdapter -ErrorAction SilentlyContinue) {
  $ipEntries = @(
    Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object { $_.IPAddress -and $_.IPAddress -notlike '169.254*' } |
      Select-Object IPAddress, PrefixLength
  )
  $gateway = (
    Get-NetIPConfiguration -InterfaceIndex $adapter.InterfaceIndex -ErrorAction SilentlyContinue
  ).IPv4DefaultGateway.NextHop
  $ipv4 = @(
    $ipEntries |
      Select-Object -ExpandProperty IPAddress
  )
  $prefixes = @(
    $ipEntries |
      Select-Object -ExpandProperty PrefixLength
  )
  [pscustomobject]@{
    Name = $adapter.Name
    Description = $adapter.InterfaceDescription
    InterfaceIndex = $adapter.InterfaceIndex
    Status = $adapter.Status
    MacAddress = $adapter.MacAddress
    LinkSpeed = $adapter.LinkSpeed
    Addresses = $ipv4
    PrefixLengths = $prefixes
    DefaultGateway = $gateway
  }
}
$rows | ConvertTo-Json -Compress -Depth 4
""",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.stdout.strip():
                    parsed = json.loads(result.stdout)
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    for iface in parsed:
                        addresses = iface.get("Addresses") or []
                        if isinstance(addresses, str):
                            addresses = [addresses]
                        name = str(iface.get("Name", "")).strip()
                        description = str(iface.get("Description", "")).strip()
                        status = str(iface.get("Status", "")).strip().lower()
                        state = "up" if status == "up" else "down"
                        interfaces.append({
                            "name": name or description or "unknown",
                            "description": description,
                            "interface_index": iface.get("InterfaceIndex"),
                            "state": state,
                            "addresses": addresses,
                            "prefix_lengths": iface.get("PrefixLengths") or [],
                            "default_gateway": str(iface.get("DefaultGateway", "")).strip(),
                            "mac": str(iface.get("MacAddress", "")).strip(),
                            "link_speed": str(iface.get("LinkSpeed", "")).strip(),
                            "type": self._guess_iface_type(f"{name} {description}"),
                        })
        except Exception as e:
            return {"error": str(e), "interfaces": interfaces}

        return {"interfaces": interfaces, "count": len(interfaces)}

    def get_current_link_insights(self, resolve_hostnames: bool = False) -> dict:
        """Return the current WiFi link plus a safe local-neighbor inventory."""
        current = self.get_current_wifi()
        interfaces = self.get_interfaces()
        clients = self._list_local_clients(interfaces, resolve_hostnames=resolve_hostnames)
        active_iface = self._select_active_interface(interfaces, prefer_wifi=bool(current.get("connected")))
        active_ip = ""
        active_subnet = ""
        if active_iface:
            addresses = self._usable_ipv4_addresses(active_iface.get("addresses") or [])
            if addresses:
                active_ip = addresses[0]
            active_subnet = self._format_active_subnet(active_iface)

        return {
            "connected": bool(current.get("connected")),
            "current_wifi": current,
            "active_interface": active_iface.get("name", "") if active_iface else "",
            "active_ip": active_ip,
            "active_subnet": active_subnet,
            "local_ip": active_ip,
            "clients": clients,
            "client_count": len(clients),
            "note": "Device inventory is derived from local neighbor tables and is not a vulnerability assessment.",
        }

    def _list_local_clients(self, interfaces: dict, resolve_hostnames: bool = False) -> list[dict]:
        if self.system == "Windows":
            return self._list_local_clients_windows(interfaces, resolve_hostnames=resolve_hostnames)
        if self.system == "Linux":
            return self._list_local_clients_linux(resolve_hostnames=resolve_hostnames)
        if self.system == "Darwin":
            return self._list_local_clients_macos(resolve_hostnames=resolve_hostnames)
        return []

    def _list_local_clients_windows(self, interfaces: dict, resolve_hostnames: bool = False) -> list[dict]:
        active_ifaces = [
            iface
            for iface in interfaces.get("interfaces", [])
            if iface.get("type") in {"wifi", "ethernet"} and iface.get("state") == "up"
            and self._usable_ipv4_addresses(iface.get("addresses") or [])
        ]
        wifi_ifaces = [iface for iface in active_ifaces if iface.get("type") == "wifi"]
        preferred_ifaces = wifi_ifaces or active_ifaces
        preferred_addresses = {
            address
            for iface in preferred_ifaces
            for address in (iface.get("addresses") or [])
            if address and self._is_usable_ipv4(address)
        }
        preferred_indices = {
            int(iface.get("interface_index"))
            for iface in preferred_ifaces
            if str(iface.get("interface_index", "")).strip().isdigit()
        }
        gateways = {
            str(iface.get("default_gateway", "")).strip()
            for iface in preferred_ifaces
            if str(iface.get("default_gateway", "")).strip()
        }
        clients = self._windows_neighbor_clients(preferred_indices, gateways, resolve_hostnames=resolve_hostnames)
        clients.extend(
            self._windows_arp_clients(
                preferred_addresses,
                gateways,
                resolve_hostnames=resolve_hostnames,
            )
        )
        return self._dedupe_clients(clients)

    def _windows_neighbor_clients(
        self,
        preferred_indices: set[int],
        gateways: set[str],
        resolve_hostnames: bool = False,
    ) -> list[dict]:
        clients = []
        try:
            ps_cmd = r"""
Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Select-Object ifIndex, IPAddress, LinkLayerAddress, State, InterfaceAlias |
  ConvertTo-Json -Compress -Depth 4
"""
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=12,
            )
            if not result.stdout.strip():
                return []
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for entry in parsed:
                ip_address = str(entry.get("IPAddress", "")).strip()
                if not self._should_include_client_ip(ip_address):
                    continue
                state = str(entry.get("State", "")).strip().lower()
                if state in {"unreachable", "invalid", "incomplete"}:
                    continue
                if_index = entry.get("ifIndex")
                if preferred_indices and isinstance(if_index, int) and if_index not in preferred_indices:
                    continue
                clients.append(
                    {
                        "ip": ip_address,
                        "mac": str(entry.get("LinkLayerAddress", "")).strip().replace("-", ":").lower(),
                        "kind": self._normalize_neighbor_state(state),
                        "hostname": self._safe_reverse_lookup(ip_address) if resolve_hostnames else "",
                        "interface": str(entry.get("InterfaceAlias", "")).strip(),
                        "role": "gateway" if ip_address in gateways else "device",
                        "source": "net-neighbor",
                    }
                )
        except Exception:
            return []
        return clients

    def _windows_arp_clients(
        self,
        preferred_addresses: set[str],
        gateways: set[str],
        resolve_hostnames: bool = False,
    ) -> list[dict]:
        clients = []
        current_iface_ip = ""
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=8)
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.lower().startswith("interface:"):
                    match = re.search(r"Interface:\s+(\d{1,3}(?:\.\d{1,3}){3})", line, re.IGNORECASE)
                    current_iface_ip = match.group(1) if match else ""
                    continue
                if current_iface_ip and preferred_addresses and current_iface_ip not in preferred_addresses:
                    continue
                match = re.match(
                    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+(?P<mac>[0-9a-fA-F-]+)\s+(?P<kind>\w+)",
                    line,
                )
                if not match:
                    continue
                ip_address = match.group("ip")
                if not self._should_include_client_ip(ip_address):
                    continue
                clients.append(
                    {
                        "ip": ip_address,
                        "mac": match.group("mac").replace("-", ":").lower(),
                        "kind": match.group("kind").lower(),
                        "hostname": self._safe_reverse_lookup(ip_address) if resolve_hostnames else "",
                        "role": "gateway" if ip_address in gateways else "device",
                        "source": "arp",
                    }
                )
        except Exception:
            return []
        return clients

    def _list_local_clients_linux(self, resolve_hostnames: bool = False) -> list[dict]:
        clients = []
        try:
            result = subprocess.run(["ip", "neigh", "show"], capture_output=True, text=True, timeout=8)
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                match = re.match(
                    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+dev\s+(?P<dev>\S+).*?(?:lladdr\s+(?P<mac>[0-9a-f:]+))?\s+(?P<state>REACHABLE|STALE|DELAY|PROBE|FAILED|INCOMPLETE)",
                    line,
                    re.IGNORECASE,
                )
                if not match:
                    continue
                ip_address = match.group("ip")
                if not self._should_include_client_ip(ip_address):
                    continue
                clients.append(
                    {
                        "ip": ip_address,
                        "mac": (match.group("mac") or "").lower(),
                        "kind": match.group("state").lower(),
                        "hostname": self._safe_reverse_lookup(ip_address) if resolve_hostnames else "",
                    }
                )
        except Exception:
            return []
        return self._dedupe_clients(clients)

    def _list_local_clients_macos(self, resolve_hostnames: bool = False) -> list[dict]:
        clients = []
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=8)
            for raw_line in result.stdout.splitlines():
                match = re.search(
                    r"\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-f:]+|incomplete)",
                    raw_line,
                    re.IGNORECASE,
                )
                if not match:
                    continue
                ip_address = match.group("ip")
                if not self._should_include_client_ip(ip_address):
                    continue
                clients.append(
                    {
                        "ip": ip_address,
                        "mac": "" if match.group("mac").lower() == "incomplete" else match.group("mac").lower(),
                        "kind": "arp",
                        "hostname": self._safe_reverse_lookup(ip_address) if resolve_hostnames else "",
                    }
                )
        except Exception:
            return []
        return self._dedupe_clients(clients)

    def _safe_reverse_lookup(self, ip_address: str) -> str:
        cached = self._reverse_lookup_cache.get(ip_address)
        if cached is not None:
            return cached

        previous_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(0.15)
            host, _, _ = socket.gethostbyaddr(ip_address)
            self._reverse_lookup_cache[ip_address] = host
            return host
        except Exception:
            self._reverse_lookup_cache[ip_address] = ""
            return ""
        finally:
            socket.setdefaulttimeout(previous_timeout)

    def _dedupe_clients(self, clients: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        for client in clients:
            ip_address = client.get("ip") or ""
            if not self._should_include_client_ip(ip_address):
                continue
            existing = merged.setdefault(ip_address, {"ip": ip_address})
            for key, value in client.items():
                if key == "ip":
                    continue
                if key == "source":
                    existing_sources = {
                        part.strip()
                        for part in str(existing.get("source", "")).split(",")
                        if part.strip()
                    }
                    if value:
                        existing_sources.add(str(value))
                    existing["source"] = ", ".join(sorted(existing_sources))
                    continue
                if (not existing.get(key)) and value:
                    existing[key] = value
        deduped = list(merged.values())
        deduped.sort(key=lambda item: item.get("ip", ""))
        return deduped[:32]

    def _select_active_interface(self, interfaces: dict, prefer_wifi: bool = True) -> dict:
        candidates = [
            iface
            for iface in interfaces.get("interfaces", [])
            if iface.get("type") in {"wifi", "ethernet"} and iface.get("state") == "up"
        ]
        if not candidates:
            return {}
        if prefer_wifi:
            for iface in candidates:
                if iface.get("type") == "wifi" and self._usable_ipv4_addresses(iface.get("addresses") or []):
                    return iface
        for iface in candidates:
            if self._usable_ipv4_addresses(iface.get("addresses") or []):
                return iface
        return candidates[0]

    def _format_active_subnet(self, iface: dict) -> str:
        addresses = self._usable_ipv4_addresses(iface.get("addresses") or [])
        prefixes = iface.get("prefix_lengths") or []
        if not addresses:
            return ""
        prefix = prefixes[0] if prefixes else 24
        try:
            return str(ip_interface(f"{addresses[0]}/{prefix}").network)
        except Exception:
            return ""

    def _usable_ipv4_addresses(self, addresses: list[str]) -> list[str]:
        return [address for address in addresses if self._is_usable_ipv4(address)]

    def _is_usable_ipv4(self, address: str) -> bool:
        return bool(
            address
            and re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", address)
            and not address.startswith("169.254.")
            and address != "0.0.0.0"
        )

    def _should_include_client_ip(self, address: str) -> bool:
        if not self._is_usable_ipv4(address):
            return False
        try:
            candidate = ip_address(address)
        except ValueError:
            return False
        if candidate.is_loopback or candidate.is_multicast or candidate.is_unspecified or candidate.is_reserved:
            return False
        if str(candidate) == "255.255.255.255":
            return False
        octets = str(candidate).split(".")
        if len(octets) == 4 and octets[-1] == "255":
            return False
        return True

    def _normalize_neighbor_state(self, state: str) -> str:
        normalized = (state or "").strip().lower()
        if not normalized:
            return "neighbor"
        if normalized.isdigit():
            return f"state-{normalized}"
        return normalized

    # ─── Helpers ───

    def _get_wifi_interface(self) -> Optional[str]:
        """Find the WiFi interface name on Linux."""
        try:
            result = subprocess.run(["iw", "dev"], capture_output=True, text=True, timeout=5)
            match = re.search(r"Interface\s+(\S+)", result.stdout)
            return match.group(1) if match else None
        except Exception:
            return None

    def _guess_iface_type(self, name: str) -> str:
        """Guess interface type from name."""
        name_lower = name.lower()
        if any(token in name_lower for token in ("virtualbox", "hyper-v", "host-only", "vethernet", "loopback pseudo-interface")):
            return "virtual"
        if (
            name_lower.startswith(("wlan", "wifi", "wlp", "wl"))
            or "wi-fi" in name_lower
            or "wireless" in name_lower
        ):
            return "wifi"
        elif (
            name_lower.startswith(("eth", "en", "ethernet"))
            or "ethernet" in name_lower
            or "gigabit" in name_lower
        ):
            return "ethernet"
        elif name_lower.startswith(("lo",)):
            return "loopback"
        elif (
            name_lower.startswith(("bt", "bnep"))
            or "bluetooth" in name_lower
        ):
            return "bluetooth"
        elif name_lower.startswith(("docker", "br", "veth")):
            return "virtual"
        return "unknown"

    def _classify_bt_device_type(self, name: str, dev_class: str, device_id: str) -> str:
        lowered = " ".join([name.lower(), str(dev_class).lower(), str(device_id).lower()])
        if any(token in lowered for token in ("adapter", "radio", "controller", "wireless bluetooth")):
            return "adapter"
        if "bthle" in lowered or "gatt" in lowered:
            return "ble"
        return "paired"

    def _parse_netsh_wifi(self, output: str) -> dict:
        """Parse Windows netsh wlan output."""
        networks = []
        current = {}
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("SSID ") and "BSSID" not in line:
                if current.get("ssid"):
                    networks.append(current)
                ssid = line.split(":", 1)[1].strip() if ":" in line else ""
                current = {"ssid": ssid, "signal": 0, "security": ""}
            elif "Signal" in line and ":" in line:
                match = re.search(r"(\d+)", line.split(":", 1)[1])
                current["signal"] = int(match.group(1)) if match else 0
            elif "Authentication" in line and ":" in line:
                current["security"] = line.split(":", 1)[1].strip()
        if current.get("ssid"):
            networks.append(current)
        networks = [n for n in networks if n["ssid"]]
        networks.sort(key=lambda n: n["signal"], reverse=True)
        return {"available": True, "networks": networks, "count": len(networks)}

    def _parse_iwlist(self, output: str) -> dict:
        """Parse Linux iwlist output."""
        networks = []
        for cell in output.split("Cell "):
            ssid_match = re.search(r'ESSID:"([^"]*)"', cell)
            signal_match = re.search(r"Signal level[=:](-?\d+)", cell)
            if ssid_match and ssid_match.group(1):
                networks.append({
                    "ssid": ssid_match.group(1),
                    "signal": int(signal_match.group(1)) + 100 if signal_match else 0,
                })
        networks.sort(key=lambda n: n["signal"], reverse=True)
        return {"available": True, "networks": networks, "count": len(networks)}

    def _parse_airport(self, output: str) -> dict:
        """Parse macOS airport -s output."""
        networks = []
        for line in output.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 2:
                ssid = parts[0]
                signal = int(parts[1]) if parts[1].lstrip("-").isdigit() else 0
                networks.append({"ssid": ssid, "signal": abs(signal)})
        networks.sort(key=lambda n: n["signal"], reverse=True)
        return {"available": True, "networks": networks, "count": len(networks)}

    # ─── Summary ───

    def summarize(self) -> str:
        """Get a human-readable summary of nearby signals."""
        parts = []

        # WiFi
        wifi = self.get_current_wifi()
        if wifi.get("connected"):
            parts.append(f"Connected to WiFi: {wifi['ssid']} ({wifi.get('signal', '?')}%)")

        scan = self.scan_wifi()
        if scan.get("available"):
            parts.append(f"{scan['count']} WiFi networks nearby")

        # Bluetooth
        bt = self.scan_bluetooth()
        if bt.get("available") and bt.get("devices"):
            names = [d["name"] for d in bt["devices"][:5]]
            parts.append(f"Bluetooth: {', '.join(names)}")

        # Interfaces
        ifaces = self.get_interfaces()
        active = [i for i in ifaces.get("interfaces", []) if i.get("state") == "up" and i["type"] != "loopback"]
        if active:
            parts.append(f"{len(active)} active network interfaces")

        if not parts:
            return "No signal data available."

        return " | ".join(parts)
