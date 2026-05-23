"""Ghost Protocol 2.0 — WiFi analysis, MAC randomization, log wipe, glitch wallpaper."""
from __future__ import annotations

import os
import random
import re
import subprocess
import time
import base64
from pathlib import Path
from typing import Optional


class GhostProtocol:
    """Enhanced ghost operations — environment analysis, cover, and cleanup."""

    def __init__(self):
        self._original_hostname = os.environ.get("COMPUTERNAME", "")
        self._original_mac: Optional[str] = None
        self._active = False

    # ── WiFi Environment Analysis ───────────────────────────────────────────────

    def analyze_wifi(self) -> dict:
        """Scan WiFi and find networks, signal strength, and security."""
        result = {"networks": [], "recommended": None}
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "netsh wlan show networks mode=Bssid 2>$null | Out-String"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if not r:
                return result
            current_ssid = ""
            current_bssid = ""
            current_signal = 0
            current_channel = ""
            current_auth = ""
            networks = []
            for line in r.split("\n"):
                line = line.strip()
                ssid_m = re.search(r'SSID\s*:\s*(.+)', line)
                if ssid_m:
                    if current_ssid and current_signal > 0:
                        networks.append({
                            "ssid": current_ssid, "bssid": current_bssid,
                            "signal": current_signal, "channel": current_channel,
                            "auth": current_auth, "secure": "WPA" in current_auth or "WEP" in current_auth,
                        })
                    current_ssid = ssid_m.group(1).strip()
                    current_bssid = ""
                    current_signal = 0
                    current_channel = ""
                    current_auth = ""
                    continue
                bssid_m = re.search(r'BSSID\s*:\s*(.+)', line)
                if bssid_m:
                    current_bssid = bssid_m.group(1).strip()
                    continue
                sig_m = re.search(r'Signal\s*:\s*(\d+)%', line)
                if sig_m:
                    current_signal = int(sig_m.group(1))
                    continue
                chan_m = re.search(r'Channel\s*:\s*(\d+)', line)
                if chan_m:
                    current_channel = chan_m.group(1)
                    continue
                auth_m = re.search(r'Authentication\s*:\s*(.+)', line)
                if auth_m:
                    current_auth = auth_m.group(1).strip()

            if current_ssid and current_signal > 0:
                networks.append({
                    "ssid": current_ssid, "bssid": current_bssid,
                    "signal": current_signal, "channel": current_channel,
                    "auth": current_auth, "secure": "WPA" in current_auth or "WEP" in current_auth,
                })

            # Sort by signal, recommend strongest that isn't suspicious
            networks.sort(key=lambda n: n["signal"], reverse=True)
            suspicious = ["fbi", "surveillance", "police", "nsa", "van", "gov", "trap", "honeypot", "stingray"]
            recommended = None
            for n in networks:
                ssid_lower = n["ssid"].lower()
                if not any(s in ssid_lower for s in suspicious) and n["secure"]:
                    recommended = n
                    break
            if not recommended and networks:
                recommended = networks[0]

            result["networks"] = networks
            result["recommended"] = recommended
            result["count"] = len(networks)
            return result
        except Exception as e:
            return {"error": str(e)}

    # ── Hostname Randomization ──────────────────────────────────────────────────

    def randomize_hostname(self) -> str:
        """Generate and apply a random innocuous hostname."""
        prefixes = ["DESKTOP", "LAPTOP", "WORKSTATION", "PC", "OFFICE", "HOME", "STUDIO", "LAB", "NODE"]
        suffixes = []
        for _ in range(3):
            suffixes.append(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ2345679"))
        new_name = f"{random.choice(prefixes)}-{''.join(suffixes)}"
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Rename-Computer -NewName '{new_name}' -Force 2>&1 | Out-String"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if "error" not in r.lower():
                self._active = True
                return f"Hostname randomized to {new_name}. Reboot required for full effect."
            return f"Hostname change attempted: {r[:200]}"
        except Exception as e:
            return f"Hostname change failed: {e}"

    # ── MAC Randomization ───────────────────────────────────────────────────────

    def randomize_mac(self) -> str:
        """Attempt to randomize MAC address on active WiFi adapter."""
        try:
            adapters = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetAdapter -Name '*WiFi*','*Wireless*','*WLAN*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name | Out-String"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip().split()
            if not adapters:
                return "No WiFi adapter found for MAC randomization."
            adapter = adapters[0]
            # Generate random MAC with a valid OUI (locally administered)
            new_mac = "02" + "".join(f"{random.randint(0,255):02x}" for _ in range(5))
            # Disable, set MAC, re-enable
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Disable-NetAdapter -Name '{adapter}' -Confirm:$false -ErrorAction SilentlyContinue"],
                           capture_output=True, timeout=5)
            time.sleep(1)
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Set-NetAdapter -Name '{adapter}' -MacAddress '{new_mac}' -ErrorAction SilentlyContinue 2>&1 | Out-String"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Enable-NetAdapter -Name '{adapter}' -Confirm:$false -ErrorAction SilentlyContinue"],
                           capture_output=True, timeout=5)
            if "error" not in r.lower():
                return f"MAC randomized on {adapter}: {new_mac}"
            return f"MAC change not supported by adapter: {r[:200]}"
        except Exception as e:
            return f"MAC randomization failed: {e}"

    # ── Event Log Wipe ──────────────────────────────────────────────────────────

    def wipe_event_logs(self) -> str:
        """Clear Windows event logs."""
        logs = ["Application", "System", "Security", "Setup", "PowerShell", "Windows PowerShell",
                "Microsoft-Windows-Sysmon/Operational", "Microsoft-Windows-TaskScheduler/Operational"]
        cleared = []
        failed = []
        for log in logs:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Clear-EventLog -LogName '{log}' -ErrorAction SilentlyContinue 2>&1 | Out-String"],
                    capture_output=True, text=True, timeout=10
                ).stdout.strip()
                if not r:
                    cleared.append(log)
                else:
                    failed.append(log)
            except Exception:
                failed.append(log)
        result = f"Cleared {len(cleared)} logs"
        if failed:
            result += f", {len(failed)} inaccessible (try admin)"
        return result

    # ── Glitch Wallpaper ────────────────────────────────────────────────────────

    def set_glitch_wallpaper(self) -> str:
        """Generate a glitch-art bitmap and set it as desktop wallpaper."""
        try:
            script = '''
            Add-Type -TypeDefinition @"
            using System;
            using System.Drawing;
            using System.Runtime.InteropServices;
            using System.Drawing.Imaging;
            public class Wallpaper {
                [DllImport("user32.dll", CharSet=CharSet.Auto)]
                public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
                public static void Set(string path) {
                    SystemParametersInfo(20, 0, path, 2);
                }
            }
"@
            $bmp = New-Object System.Drawing.Bitmap(1920, 1080)
            $rng = New-Object System.Random
            $rand = [System.Random]::new()
            for($y=0; $y -lt 1080; $y++) {
                for($x=0; $x -lt 1920; $x++) {
                    if($rand.Next(100) -lt 3) {
                        $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(0, $rand.Next(50,255), 0, $rand.Next(50,150)))
                    } elseif($rand.Next(200) -lt 1) {
                        $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 255, 255, 255))
                    } else {
                        $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 5, 5, 8))
                    }
                }
                if($y % 27 -eq 0) {
                    for($s=0; $s -lt $rand.Next(200,600); $s++) {
                        $sx = $rand.Next(0,1920)
                        $sy = $y + $rand.Next(-2,3)
                        if($sy -ge 0 -and $sy -lt 1080) {
                            $bmp.SetPixel($sx, $sy, [System.Drawing.Color]::FromArgb(255, 0, 180 + $rand.Next(0,75), 50 + $rand.Next(0,100)))
                        }
                    }
                }
            }
            $path = "$env:TEMP\\glitch.png"
            $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
            $bmp.Dispose()
            [Wallpaper]::Set($path)
            Write-Output "ok"
'''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=30
            ).stdout.strip()
            if "ok" in r:
                return "Glitch wallpaper deployed."
            return f"Wallpaper failed: {r[:200]}"
        except Exception as e:
            return f"Wallpaper failed: {e}"

    # ── Full Ghost Protocol ─────────────────────────────────────────────────────

    def execute_full(self) -> str:
        """Run the complete Ghost Protocol sequence."""
        lines = ["══ Ghost Protocol 2.0 ══"]
        wifi = self.analyze_wifi()
        if wifi.get("recommended"):
            lines.append(f"WiFi: {wifi['recommended']['ssid']} ({wifi['recommended']['signal']}%) — clean")
        elif wifi.get("networks"):
            lines.append(f"WiFi: {len(wifi['networks'])} networks found")
        else:
            lines.append("WiFi: no networks found")

        hostname_result = self.randomize_hostname()
        lines.append(f"Hostname: {hostname_result[:60]}")

        mac_result = self.randomize_mac()
        lines.append(f"MAC: {mac_result[:60]}")

        log_result = self.wipe_event_logs()
        lines.append(f"Logs: {log_result}")

        wall_result = self.set_glitch_wallpaper()
        lines.append(f"Wallpaper: {wall_result}")

        self._active = True
        lines.append("══ Ghost Protocol complete ══")
        return "\n".join(lines)

    def status(self) -> str:
        if self._active:
            return f"Ghost Protocol active. Original hostname: {self._original_hostname}"
        return "Ghost Protocol inactive."

    def deactivate(self):
        self._active = False
