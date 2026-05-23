"""ADB Phone Controller — control an Android phone over WiFi via ADB.

Usage:
  controller = AdbController()
  controller.connect("192.168.1.100")   # Connect to phone over WiFi
  controller.send_sms("5551234", "hello")  # Send SMS via phone
  text = controller.screencap_ocr()     # Screenshot + OCR
  controller.tap(500, 1000)             # Tap at coordinates
  controller.type_text("hello world")   # Type text on phone

All methods return status strings for LLM consumption.
"""

from __future__ import annotations

import subprocess
import tempfile
import os
import time
from pathlib import Path


class AdbController:
    """Controls an Android phone over ADB WiFi."""

    ADB_TIMEOUT = 15
    OCR_TIMEOUT = 30

    def __init__(self):
        self._adb_path = self._find_adb()
        self._device = None  # serial of connected device
        self._connected = False

    def _find_adb(self) -> str:
        """Locate adb.exe on the system."""
        candidates = [
            "adb",
            "adb.exe",
            str(Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb.exe"),
            str(Path(os.environ.get("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb.exe"),
            r"C:\Program Files\Android\Android Studio\platform-tools\adb.exe",
            r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
            str(Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"),
        ]
        for c in candidates:
            try:
                r = subprocess.run([c, "version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    return c
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                continue
        return "adb"

    def _run(self, args: list[str], timeout: int = None) -> tuple[int, str, str]:
        """Run an ADB command."""
        cmd = [self._adb_path] + args
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout or self.ADB_TIMEOUT)
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except FileNotFoundError:
            return -1, "", "ADB not found. Install Android SDK platform-tools or add adb to PATH."
        except subprocess.TimeoutExpired:
            return -1, "", f"ADB command timed out after {timeout or self.ADB_TIMEOUT}s"
        except Exception as e:
            return -1, "", str(e)

    def connect(self, ip: str) -> str:
        """Connect to a phone over WiFi: adb connect IP:5555."""
        if not ip:
            return "ERROR: No IP address provided."
        # Kill existing connections on wrong IP
        self._run(["kill-server"], timeout=5)
        code, out, err = self._run(["connect", f"{ip}:5555"], timeout=10)
        if "connected" in out.lower() or code == 0:
            self._device = f"{ip}:5555"
            self._connected = True
            return f"Connected to phone at {ip}:5555. Device: {out}"
        else:
            self._connected = False
            hint = ""
            if "cannot connect" in err or "connection refused" in err:
                hint = " Make sure USB debugging is enabled on the phone and it's connected to WiFi. " \
                       "Also try: enable 'Debug over WiFi' in Developer Options, or connect via USB first then run 'adb tcpip 5555'."
            return f"Failed to connect to {ip}:5555. {err or out}{hint}"

    def disconnect(self) -> str:
        """Disconnect from the phone."""
        if self._device:
            self._run(["disconnect", self._device])
        self._device = None
        self._connected = False
        return "Disconnected."

    def send_sms(self, number: str, message: str) -> str:
        """Send SMS through connected phone."""
        if not self._connected or not self._device:
            return "ERROR: No ADB device connected. Call connect(ip) first."
        # Android 5+: service call isms 7 (varies by OEM/Android version)
        # Also try: am start -a android.intent.action.SENDTO -d sms:number --es sms_body message
        number = number.strip().replace(" ", "").replace("-", "")
        message_escaped = message.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        # Method 1: Direct SMS via service call (Android 5-11)
        sms_hex = self._text_to_hex(number)
        msg_hex = self._text_to_hex(message)
        code, out, err = self._run([
            "-s", self._device, "shell", "service", "call", "isms", "7",
            "i32", "0", "s16", "com.android.mms", "s16", number, "s16", "", "s16", message
        ], timeout=10)
        if code == 0 and "error" not in out.lower():
            return f"SMS sent to {number} via ADB service call."
        # Method 2: Intent-based SMS
        code2, out2, err2 = self._run([
            "-s", self._device, "shell", "am", "start", "-a",
            "android.intent.action.SENDTO", "-d", f"smsto:{number}",
            "--es", "sms_body", message,
            "--ez", "exit_on_sent", "true"
        ], timeout=10)
        if code2 == 0:
            # Press back and home to clean up after intent
            self._run(["-s", self._device, "shell", "input", "keyevent", "4"], timeout=3)
            self._run(["-s", self._device, "shell", "input", "keyevent", "3"], timeout=3)
            return f"SMS intent launched for {number}. SMS may have been sent through messaging app."
        # Method 3: Try adb shell input + sms app (last resort)
        return f"ADB SMS failed (service call: {err[:100]}, intent: {err2[:100]}). " \
               f"Try using send_sms tool (email gateway) instead, or open the messaging app manually."

    def screencap_ocr(self) -> str:
        """Take phone screenshot and return OCR text."""
        if not self._connected or not self._device:
            return "ERROR: No ADB device connected."
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            code, out, err = self._run([
                "-s", self._device, "exec-out", "screencap", "-p"
            ], timeout=self.OCR_TIMEOUT)
            if code != 0 or not out:
                return f"Screenshot failed: {err[:200]}"
            with open(tmp_path, "wb") as f:
                f.write(out.encode("latin-1") if isinstance(out, str) else out)
            # OCR via pytesseract if available
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(tmp_path)
                text = pytesseract.image_to_string(img)
                text = text.strip()
                if text:
                    return f"[PHONE SCREEN OCR]\n{text[:3000]}"
                return "Phone screen captured but no text detected."
            except ImportError:
                return f"Phone screenshot saved to {tmp_path}. Install pytesseract for OCR."
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as e:
            return f"Screencap error: {e}"

    def tap(self, x: int, y: int) -> str:
        """Tap at screen coordinates on the phone."""
        if not self._connected or not self._device:
            return "ERROR: No ADB device connected."
        code, out, err = self._run([
            "-s", self._device, "shell", "input", "tap", str(x), str(y)
        ], timeout=5)
        if code == 0:
            return f"Tapped at ({x}, {y})."
        return f"Tap failed: {err[:200]}"

    def type_text(self, text: str) -> str:
        """Type text on the phone."""
        if not self._connected or not self._device:
            return "ERROR: No ADB device connected."
        # Escape special characters for ADB shell
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        escaped = escaped.replace("(", "").replace(")", "").replace("&", "")
        code, out, err = self._run([
            "-s", self._device, "shell", "input", "text", escaped
        ], timeout=10)
        if code == 0:
            return f"Typed '{text[:50]}' on phone."
        return f"Type text failed: {err[:200]}"

    def keyevent(self, keycode: int) -> str:
        """Send a keyevent to the phone (4=back, 3=home, 26=power, 66=enter)."""
        if not self._connected or not self._device:
            return "ERROR: No ADB device connected."
        self._run(["-s", self._device, "shell", "input", "keyevent", str(keycode)], timeout=3)
        return f"Keyevent {keycode} sent."

    def status(self) -> str:
        """Return connection status."""
        if not self._connected:
            return "ADB: Not connected."
        code, out, err = self._run(["devices"], timeout=5)
        if self._device and self._device in out:
            return f"ADB: Connected to {self._device}"
        else:
            self._connected = False
            self._device = None
            return "ADB: Device disconnected."

    def _text_to_hex(self, text: str) -> str:
        """Convert text to hex bytes for ADB service call."""
        return "".join(f"{ord(c):04x}" for c in text)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def device(self) -> str | None:
        return self._device
