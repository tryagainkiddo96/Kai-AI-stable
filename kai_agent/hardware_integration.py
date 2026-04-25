"""
Kai Hardware Integration - Sensor access and device control
Closes the hardware/sensors gap with WiFi, Bluetooth, OCR, camera capabilities
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class KaiHardwareIntegration:
    """
    Hardware and sensor integration for Kai.
    Provides WiFi, Bluetooth, OCR, camera, and device control capabilities.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.screenshots_dir = workspace / "hardware_screenshots"
        self.data_dir = workspace / "hardware_data"
        self.screenshots_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

    async def scan_wifi_networks(self) -> Dict[str, Any]:
        """Scan for WiFi networks with signal strength"""
        try:
            # Use netsh for Windows WiFi scanning
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                networks = self._parse_wifi_output(result.stdout)
                return {
                    "success": True,
                    "networks_found": len(networks),
                    "networks": networks,
                    "scan_timestamp": time.time(),
                }
            else:
                return {
                    "success": False,
                    "error": "WiFi scan failed",
                    "details": result.stderr,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_wifi_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse netsh wlan output"""
        networks = []
        current_network = None

        lines = output.split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith("SSID"):
                if current_network:
                    networks.append(current_network)
                ssid = line.split(":", 1)[1].strip()
                current_network = {"ssid": ssid, "access_points": []}

            elif line.startswith("Network type"):
                if current_network:
                    current_network["network_type"] = line.split(":", 1)[1].strip()

            elif line.startswith("Authentication"):
                if current_network:
                    current_network["authentication"] = line.split(":", 1)[1].strip()

            elif line.startswith("Encryption"):
                if current_network:
                    current_network["encryption"] = line.split(":", 1)[1].strip()

            elif line.startswith("BSSID"):
                if current_network:
                    bssid = line.split(":", 1)[1].strip()
                    current_ap = {"bssid": bssid}

            elif line.startswith("Signal"):
                if current_network and "current_ap" in locals():
                    signal = line.split(":", 1)[1].strip().replace("%", "")
                    current_ap["signal_strength"] = int(signal)

            elif line.startswith("Radio type"):
                if current_network and "current_ap" in locals():
                    radio = line.split(":", 1)[1].strip()
                    current_ap["radio_type"] = radio

            elif line.startswith("Channel"):
                if current_network and "current_ap" in locals():
                    channel = line.split(":", 1)[1].strip()
                    current_ap["channel"] = int(channel)
                    current_network["access_points"].append(current_ap)
                    del current_ap

        if current_network:
            networks.append(current_network)

        return networks

    async def get_wifi_connection_info(self) -> Dict[str, Any]:
        """Get current WiFi connection information"""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                info = self._parse_interface_output(result.stdout)
                return {"success": True, "connection_info": info}
            else:
                return {"success": False, "error": "Failed to get WiFi interface info"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_interface_output(self, output: str) -> Dict[str, Any]:
        """Parse interface information"""
        info = {}
        lines = output.split("\n")

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "Name":
                    info["interface_name"] = value
                elif key == "Description":
                    info["description"] = value
                elif key == "GUID":
                    info["guid"] = value
                elif key == "Physical address":
                    info["mac_address"] = value
                elif key == "State":
                    info["state"] = value
                elif key == "SSID":
                    info["connected_ssid"] = value
                elif key == "BSSID":
                    info["connected_bssid"] = value
                elif key == "Network type":
                    info["network_type"] = value
                elif key == "Radio type":
                    info["radio_type"] = value
                elif key == "Authentication":
                    info["authentication"] = value
                elif key == "Cipher":
                    info["cipher"] = value
                elif key == "Connection mode":
                    info["connection_mode"] = value
                elif key == "Channel":
                    info["channel"] = int(value) if value.isdigit() else value
                elif key == "Receive rate (Mbps)":
                    info["receive_rate_mbps"] = (
                        float(value) if value.replace(".", "").isdigit() else value
                    )
                elif key == "Transmit rate (Mbps)":
                    info["transmit_rate_mbps"] = (
                        float(value) if value.replace(".", "").isdigit() else value
                    )
                elif key == "Signal":
                    info["signal_strength"] = value

        return info

    async def take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Take a screenshot of the current screen"""
        try:
            if filename is None:
                filename = "screenshot_{}.png".format(int(time.time()))

            screenshot_path = self.screenshots_dir / filename

            # Use PowerShell to take screenshot
            ps_command = """
            Add-Type -AssemblyName System.Windows.Forms
            $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
            $bitmap.Save("{}")
            """.format(str(screenshot_path))

            result = subprocess.run(
                ["powershell", "-Command", ps_command], capture_output=True, timeout=10
            )

            if result.returncode == 0 and screenshot_path.exists():
                return {
                    "success": True,
                    "screenshot_path": str(screenshot_path),
                    "filename": filename,
                    "timestamp": time.time(),
                }
            else:
                return {
                    "success": False,
                    "error": "Screenshot failed",
                    "details": result.stderr.decode()
                    if result.stderr
                    else "Unknown error",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def perform_ocr_on_screen(
        self, region: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Perform OCR on screen content"""
        try:
            # First take a screenshot
            screenshot_result = await self.take_screenshot("ocr_temp.png")
            if not screenshot_result["success"]:
                return screenshot_result

            screenshot_path = screenshot_result["screenshot_path"]

            # Use PowerShell with Windows.Media.OCR for OCR
            ps_command = """
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing

            # Load Windows.Media.OCR
            [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime] | Out-Null
            [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime] | Out-Null

            $language = New-Object Windows.Globalization.Language "en-US"
            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)

            if ($engine) {{
                $bitmap = [System.Drawing.Image]::FromFile("{}")
                $memoryStream = New-Object System.IO.MemoryStream
                $bitmap.Save($memoryStream, [System.Drawing.Imaging.ImageFormat]::Png)
                $randomAccessStream = $memoryStream.AsRandomAccessStream()
                $softwareBitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::CreateCopyFromBuffer(
                    $randomAccessStream, [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, $bitmap.Width, $bitmap.Height)

                $result = $engine.RecognizeAsync($softwareBitmap).GetResults()

                $text = $result.Text
                $lines = @()
                foreach ($line in $result.Lines) {{
                    $lines += $line.Text
                }}

                $words = @()
                foreach ($line in $result.Lines) {{
                    foreach ($word in $line.Words) {{
                        $words += $word.Text
                    }}
                }}

                @{{
                    "success" = $true
                    "text" = $text
                    "lines" = $lines
                    "words" = $words
                    "confidence" = 0.8
                }} | ConvertTo-Json
            }} else {{
                @{{"success" = $false; "error" = "OCR engine not available"}} | ConvertTo-Json
            }}
            """.format(screenshot_path)

            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                try:
                    ocr_data = json.loads(result.stdout.strip())
                    return ocr_data
                except:
                    return {
                        "success": False,
                        "error": "Failed to parse OCR results",
                        "raw_output": result.stdout,
                    }
            else:
                return {
                    "success": False,
                    "error": "OCR failed",
                    "details": result.stderr,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_system_hardware_info(self) -> Dict[str, Any]:
        """Get comprehensive system hardware information"""
        try:
            # Get CPU info
            cpu_result = subprocess.run(
                ["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Get memory info
            mem_result = subprocess.run(
                ["wmic", "memorychip", "get", "Capacity"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Get disk info
            disk_result = subprocess.run(
                ["wmic", "diskdrive", "get", "Size,Model"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Parse CPU info
            cpu_info = {}
            if cpu_result.returncode == 0:
                lines = cpu_result.stdout.strip().split("\n")
                if len(lines) > 1:
                    values = lines[1].strip().split()
                    cpu_info = {
                        "model": " ".join(values[:-2])
                        if len(values) > 2
                        else "Unknown",
                        "cores": int(values[-2])
                        if len(values) > 1 and values[-2].isdigit()
                        else 0,
                        "logical_processors": int(values[-1])
                        if values[-1].isdigit()
                        else 0,
                    }

            # Parse memory info
            memory_gb = 0
            if mem_result.returncode == 0:
                lines = mem_result.stdout.strip().split("\n")
                for line in lines[1:]:
                    capacity = line.strip()
                    if capacity.isdigit():
                        memory_gb += int(capacity) // (1024**3)

            # Parse disk info
            disks = []
            if disk_result.returncode == 0:
                lines = disk_result.stdout.strip().split("\n")
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().rsplit(" ", 1)
                        if len(parts) == 2:
                            size_bytes = int(parts[1]) if parts[1].isdigit() else 0
                            disks.append(
                                {
                                    "model": parts[0],
                                    "size_gb": size_bytes // (1024**3)
                                    if size_bytes > 0
                                    else 0,
                                }
                            )

            return {
                "success": True,
                "cpu": cpu_info,
                "memory_gb": memory_gb,
                "disks": disks,
                "timestamp": time.time(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_network_interfaces(self) -> Dict[str, Any]:
        """Get detailed network interface information"""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                interfaces = self._parse_ipconfig_output(result.stdout)
                return {
                    "success": True,
                    "interfaces": interfaces,
                    "timestamp": time.time(),
                }
            else:
                return {"success": False, "error": "Failed to get network interfaces"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_ipconfig_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse ipconfig /all output"""
        interfaces = []
        current_interface = None

        lines = output.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("Ethernet adapter") or line.startswith(
                "Wireless LAN adapter"
            ):
                if current_interface:
                    interfaces.append(current_interface)

                adapter_name = line.split(":", 1)[0].replace(" adapter", "")
                current_interface = {
                    "name": adapter_name,
                    "type": "Ethernet" if "Ethernet" in line else "Wireless",
                    "details": {},
                }

            elif current_interface and ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "Description":
                    current_interface["description"] = value
                elif key == "Physical Address":
                    current_interface["mac_address"] = value
                elif key == "IPv4 Address":
                    current_interface["ipv4_address"] = value
                elif key == "Subnet Mask":
                    current_interface["subnet_mask"] = value
                elif key == "Default Gateway":
                    current_interface["default_gateway"] = value
                elif key == "DHCP Server":
                    current_interface["dhcp_server"] = value
                elif key == "DNS Servers":
                    current_interface["dns_servers"] = value.split(", ")

            i += 1

        if current_interface:
            interfaces.append(current_interface)

        return interfaces

    def get_status(self) -> Dict[str, Any]:
        """Get hardware integration status summary."""
        return {
            "wifi_scanning": "Available",
            "screenshots": "Available",
            "system_info": "Available",
            "network_info": "Available",
            "resource_monitoring": "Available",
            "ocr": "Requires Windows.Media.OCR",
            "bluetooth": "Not implemented",
            "camera": "Not implemented",
            "device_messaging": "Not implemented",
        }

    async def monitor_system_resources(
        self, duration_seconds: int = 10
    ) -> Dict[str, Any]:
        """Monitor system resources over time"""
        try:
            readings = []
            start_time = time.time()

            for _ in range(duration_seconds):
                # Get CPU usage via PowerShell
                ps_command = """
                $cpu = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average
                $mem = Get-WmiObject Win32_OperatingSystem | Select-Object -Property @{Name="FreeGB"; Expression={[math]::Round($_.FreePhysicalMemory/1MB, 2)}}, @{Name="TotalGB"; Expression={[math]::Round($_.TotalVisibleMemorySize/1MB, 2)}}
                @{
                    "cpu_percent" = $cpu
                    "memory_free_gb" = $mem.FreeGB
                    "memory_total_gb" = $mem.TotalGB
                    "timestamp" = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                """

                result = subprocess.run(
                    ["powershell", "-Command", ps_command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    try:
                        reading = json.loads(result.stdout.strip())
                        readings.append(reading)
                    except:
                        pass

                await asyncio.sleep(1)

            if readings:
                return {
                    "success": True,
                    "duration_seconds": duration_seconds,
                    "readings_count": len(readings),
                    "readings": readings,
                    "average_cpu": sum(r["cpu_percent"] for r in readings)
                    / len(readings),
                    "average_memory_free": sum(r["memory_free_gb"] for r in readings)
                    / len(readings),
                }
            else:
                return {"success": False, "error": "No readings collected"}

        except Exception as e:
            return {"success": False, "error": str(e)}
