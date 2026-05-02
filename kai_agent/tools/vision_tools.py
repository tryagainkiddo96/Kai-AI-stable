"""Vision Tools — screen capture and OCR."""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path


def _resolve_tesseract(config_tesseract_path: str = "") -> Path:
    if config_tesseract_path:
        return Path(config_tesseract_path)
    if platform.system() == "Windows":
        return Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    t = Path("/usr/bin/tesseract")
    if not t.exists():
        t = Path("/usr/local/bin/tesseract")
    return t


TESSERACT_PATH = None


class VisionTools:
    def __init__(self, workspace: Path, tesseract_path: Path | None = None) -> None:
        self.workspace = workspace
        self.tmp_dir = workspace / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.tesseract = tesseract_path or _resolve_tesseract()
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"

    def _run_native(self, args: list[str], timeout: int = 120) -> dict:
        try:
            completed = subprocess.run(args, cwd=str(self.workspace), capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace")
            return {"returncode": completed.returncode, "stdout": completed.stdout.strip()[:12000], "stderr": completed.stderr.strip()[:6000]}
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"}
        except Exception as exc:
            return {"returncode": -1, "stdout": "", "stderr": f"Failed: {exc}"}

    def _ocr_image(self, image_path: Path) -> str:
        if not self.tesseract.exists():
            return json.dumps({"action": "ocr", "ok": False, "error": f"Tesseract not found at {self.tesseract}"}, indent=2)
        try:
            result = subprocess.run([str(self.tesseract), str(image_path), "stdout", "-l", "eng"], capture_output=True, text=True, timeout=30)
            return json.dumps({"action": "ocr", "ok": True, "text": result.stdout.strip()}, indent=2)
        except Exception as exc:
            return json.dumps({"action": "ocr", "ok": False, "error": str(exc)}, indent=2)

    def capture_screen_ocr(self) -> str:
        screenshot_path = self.tmp_dir / "screenshot.png"
        if self.is_windows:
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height); "
                "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
                "$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size); "
                f"$bitmap.Save('{screenshot_path}'); "
                "$graphics.Dispose(); $bitmap.Dispose()"
            )
            result = self._run_native(["powershell", "-NoProfile", "-Command", ps_script], timeout=30)
        else:
            return json.dumps({"action": "capture_screen_ocr", "ok": False, "error": "Linux screenshot not implemented."}, indent=2)
        if result["returncode"] == 0 and screenshot_path.exists():
            return self._ocr_image(screenshot_path)
        return json.dumps({"action": "capture_screen_ocr", "ok": False, "error": result.get("stderr", "Screenshot failed")}, indent=2)
