"""Troll Mode — remote wallpaper chaos on LAN machines with admin shares."""
from __future__ import annotations

import base64
import io
import random
import subprocess
import threading
import time


class TrollMode:
    """Deploy cursed wallpapers to remote machines via admin shares."""

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False

    def start(self):
        pass

    def add_target(self, ip: str, hostname: str = ""):
        self.db.upsert_troll_target(ip, hostname)

    def _generate_glitch(self) -> bytes:
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", """
$bmp = New-Object System.Drawing.Bitmap 1920,1080
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.FillRectangle([System.Drawing.Brushes]::Black, 0, 0, 1920, 1080)
$r = New-Object System.Random
for($i=0;$i -lt 200;$i++){
    $x=$r.Next(0,1920);$y=$r.Next(0,1080);$w=$r.Next(20,300);$h=$r.Next(2,20)
    $c=[System.Drawing.Color]::FromArgb($r.Next(100,255),$r.Next(0,80),$r.Next(0,30),$r.Next(200,255))
    $g.FillRectangle([System.Drawing.SolidBrush][System.Drawing.Brush]$c, $x,$y,$w,$h)
}
for($i=0;$i -lt 40;$i++){
    $x=$r.Next(0,1920)
    $g.DrawLine([System.Drawing.Pens]::Lime, $x,0,$x,1080)
}
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg)
[Convert]::ToBase64String($ms.ToArray())
"""], capture_output=True, text=True, timeout=10)
            if r.stdout.strip():
                return base64.b64decode(r.stdout.strip())
        except Exception:
            pass
        return b""

    def _deploy_wallpaper(self, ip: str, image_bytes: bytes) -> bool:
        try:
            remote_path = f"\\\\{ip}\\C$\\Windows\\Temp\\glitch.jpg"
            local_temp = f"C:\\Windows\\Temp\\troll_{int(time.time())}.jpg"
            with open(local_temp, "wb") as f:
                f.write(image_bytes)
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Copy-Item '{local_temp}' -Destination '{remote_path}' -Force"],
                           capture_output=True, timeout=10)
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"""
$reg = [Microsoft.Win32.RegistryKey]::OpenRemoteBaseKey('CurrentUser', '{ip}')
$key = $reg.OpenSubKey('Control Panel\\Desktop', $true)
$key.SetValue('Wallpaper', '{remote_path}')
$key.SetValue('WallpaperStyle', '10')
rundll32.exe user32.dll,UpdatePerUserSystemParameters
"""], capture_output=True, timeout=15)
            try:
                import os as _os
                _os.remove(local_temp)
            except Exception:
                pass
            self.db.log_troll(ip, "glitch")
            return True
        except Exception:
            return False

    def troll_all(self) -> list[dict]:
        targets = self.db.get_troll_targets()
        results = []
        for t in targets:
            img = self._generate_glitch()
            if img:
                ok = self._deploy_wallpaper(t["ip"], img)
                results.append({"ip": t["ip"], "success": ok})
        return results

    def list_targets(self) -> list[dict]:
        return self.db.get_troll_targets()

    def remove_target(self, ip: str):
        self.db.delete_troll_target(ip)
