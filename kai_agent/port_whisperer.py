"""Port Whisperer — USB/Serial/Bluetooth device detection and logging."""
from __future__ import annotations

import subprocess
import threading
import time


class PortWhisperer:
    """Detects USB insertions, serial ports, Bluetooth devices."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._known_devices: set[str] = set()

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _loop(self):
        while self._enabled:
            try:
                devices = self._get_serial_ports() + self._get_usb_devices() + self._get_bluetooth_devices()
                for d in devices:
                    key = d.get("serial", d.get("name", ""))
                    if key and key not in self._known_devices:
                        self._known_devices.add(key)
                        self.db.log_hardware(d["name"], d["type"], serial=d.get("serial", ""), action="detected")
            except Exception:
                pass
            time.sleep(15)

    def _get_serial_ports(self) -> list[dict]:
        result = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-WmiObject Win32_SerialPort -ErrorAction SilentlyContinue | Select-Object Name, DeviceID, Description | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    result.append({"name": item.get("Name", ""), "type": "serial", "serial": item.get("DeviceID", "")})
        except Exception:
            pass
        return result

    def _get_usb_devices(self) -> list[dict]:
        result = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-PnpDevice -Class Ports -ErrorAction SilentlyContinue | Select-Object FriendlyName, DeviceID, Status | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    status = item.get("Status", "")
                    if status == "OK":
                        result.append({"name": item.get("FriendlyName", ""), "type": "usb", "serial": item.get("DeviceID", "")})
        except Exception:
            pass
        return result

    def _get_bluetooth_devices(self) -> list[dict]:
        result = []
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Select-Object FriendlyName, DeviceID, Status | ConvertTo-Json -Compress"],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    status = item.get("Status", "")
                    if status == "OK":
                        result.append({"name": item.get("FriendlyName", ""), "type": "bluetooth", "serial": item.get("DeviceID", "")})
        except Exception:
            pass
        return result

    def _get_usb_hid_events(self) -> list[dict]:
        """Read Windows Event Log for recent USB HID (keyboard/mouse) activity."""
        result = []
        try:
            cmd = ("Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-USB-USBHUB/Operational';ID=1003,1004} "
                   "-MaxEvents 10 -ErrorAction SilentlyContinue | Select-Object TimeCreated,Id,Message | ConvertTo-Json -Compress")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                               capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                import json as j
                data = j.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    result.append({
                        "name": f"USB Event {item.get('Id','')}",
                        "type": "usb_hid",
                        "serial": item.get("Message", "")[:80],
                    })
        except Exception:
            pass
        return result

    def get_hid_activity(self, minutes: int = 5) -> list[dict]:
        """Check recent keyboard/mouse HID activity via raw input API."""
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", """
$signatures = @'
[DllImport("user32.dll")] public static extern int GetLastInputInfo(ref uint plii);
[StructLayout(LayoutKind.Sequential)] public struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
'@
Add-Type -MemberDefinition $signatures -Name NativeMethods -Namespace Win32
$li = New-Object Win32.NativeMethods+LASTINPUTINFO
$li.cbSize = [System.Runtime.InteropServices.Marshal]::SizeOf($li)
[Win32.NativeMethods]::GetLastInputInfo([ref]$li)
$ticks = [Environment]::TickCount
$idle = [Math]::Floor(($ticks - $li.dwTime) / 1000)
Write-Output $idle
"""], capture_output=True, text=True, timeout=5)
            idle_secs = int(r.stdout.strip()) if r.stdout.strip() else 0
            return [{"type": "hid_idle", "seconds": idle_secs}]
        except Exception:
            return []

    def get_ports(self) -> list[dict]:
        return self.db.query_hardware(limit=50)

    def get_by_type(self, dtype: str) -> list[dict]:
        return self.db.query_hardware(device_type=dtype, limit=50)
