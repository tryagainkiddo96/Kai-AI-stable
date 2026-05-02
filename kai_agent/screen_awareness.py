"""
Kai Screen Awareness — Periodic screenshots + OCR for contextual understanding.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path


class ScreenAwareness:
    """Periodically captures screenshots of active window and extracts text via OCR."""

    def __init__(self, workspace, interval: float = 10.0, enabled: bool = False) -> None:
        self.workspace = Path(workspace)
        self.capture_dir = self.workspace / "screen_captures"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.interval = interval
        self.enabled = enabled
        self._thread: threading.Thread | None = None
        self._captures: list[dict] = []
        self._max_history = 20
        self._lock = threading.Lock()
        self._callbacks: list = []

    def add_callback(self, fn):
        self._callbacks.append(fn)

    def _notify(self, message):
        for cb in self._callbacks:
            try:
                cb(message)
            except Exception:
                pass

    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.enabled = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _screenshot(self):
        import pyautogui
        import tempfile
        try:
            path = self.capture_dir / f"capture_{int(time.time())}.png"
            screenshot = pyautogui.screenshot()
            screenshot.save(str(path))
            return str(path)
        except Exception as exc:
            return None

    def _ocr(self, image_path):
        import subprocess
        tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        try:
            result = subprocess.run(
                [tesseract, image_path, "stdout", "-l", "eng"],
                capture_output=True, text=True, timeout=15)
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_active_context(self):
        """Try to identify what app/window is active and what it contains."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$proc = Get-Process | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -Last 1; "
                 "$proc.MainWindowTitle + '|' + $proc.ProcessName + '|' + $proc.Id"],
                capture_output=True, text=True, timeout=2)
            parts = result.stdout.strip().split("|")
            return {"title": parts[0], "process": parts[1], "pid": parts[2]} if len(parts) == 3 else {}
        except Exception:
            return {}

    def _loop(self):
        while self.enabled:
            try:
                path = self._screenshot()
                if path:
                    ocr_text = self._ocr(path)
                    context = self._get_active_context()
                    entry = {
                        "timestamp": time.strftime("%H:%M:%S"),
                        "path": path,
                        "ocr_text": ocr_text[:2000],
                        "context": context,
                        "char_count": len(ocr_text),
                    }
                    with self._lock:
                        self._captures.append(entry)
                        self._captures = self._captures[-self._max_history:]

                    # Analyze for interesting content
                    if ocr_text:
                        lower = ocr_text.lower()
                        if any(kw in lower for kw in ["error", "traceback", "exception", "failed", "warning"]):
                            self._notify(f"⚠️ Screen shows errors/warnings. Want me to investigate?")
                        elif any(kw in lower for kw in ["terminal", "cmd", "powershell", "bash"]) and len(ocr_text) > 100:
                            self._notify(f"🖥️ Terminal detected. I can see what's running.")
                        elif any(kw in lower for kw in ["visual studio", "vscode", "pycharm", "cursor"]):
                            self._notify(f"💻 Code editor active. I can see your code.")

                # Clean old captures (keep last 10)
                files = sorted(self.capture_dir.glob("capture_*.png"))
                for f in files[:-10]:
                    try:
                        f.unlink()
                    except Exception:
                        pass

            except Exception:
                pass

            time.sleep(self.interval)

    def get_recent(self, count: int = 5):
        with self._lock:
            return self._captures[-count:]

    def get_context_summary(self):
        recent = self.get_recent(3)
        if not recent:
            return "No screen captures yet."
        titles = set()
        for cap in recent:
            ctx = cap.get("context", {})
            if ctx.get("title"):
                titles.add(ctx["title"])
        ocr_preview = recent[-1].get("ocr_text", "")[:500]
        return {
            "windows_seen": list(titles),
            "latest_ocr": ocr_preview,
            "captures_count": len(self._captures),
        }

    def status(self):
        return {
            "enabled": self.enabled,
            "interval": self.interval,
            "captures_count": len(self._captures),
            "thread_alive": self._thread.is_alive() if self._thread else False,
        }
