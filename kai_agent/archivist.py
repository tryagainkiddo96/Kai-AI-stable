"""Archivist — automated file organization and desktop cleaning."""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path


class Archivist:
    """Scans watched folders and auto-categorizes files by extension."""

    RULES = {
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff"},
        "Documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".md", ".csv"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp", ".rs", ".go", ".rb", ".php", ".swift", ".kt", ".scala"},
        "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage"},
        "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
        "Video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"},
        "Config": {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env"},
    }

    def __init__(self, db):
        self.db = db
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._watched_dirs: list[Path] = []
        self._organized = 0

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        from os import environ
        desktop = Path(environ.get("USERPROFILE", "")) / "Desktop"
        downloads = Path(environ.get("USERPROFILE", "")) / "Downloads"
        self._watched_dirs = [d for d in [desktop, downloads] if d.exists()]
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _loop(self):
        while self._enabled:
            try:
                for folder in self._watched_dirs:
                    self._organize_folder(folder)
            except Exception:
                pass
            time.sleep(3600)

    def _organize_folder(self, folder: Path):
        for item in list(folder.iterdir()):
            if not item.is_file():
                continue
            if item.name.startswith("."):
                continue
            cat = self._classify(item.suffix.lower())
            if not cat:
                continue
            target_dir = folder / cat
            target_dir.mkdir(exist_ok=True)
            dest = target_dir / item.name
            if dest.exists():
                dest = target_dir / f"{item.stem}_{int(time.time())}{item.suffix}"
            try:
                shutil.move(str(item), str(dest))
                self._organized += 1
                if self.db:
                    self.db.journal_entry("file_organized",
                                          {"from": str(item), "to": str(dest), "category": cat},
                                          source="archivist", importance=0)
            except Exception:
                pass

    def _classify(self, suffix: str) -> str | None:
        for cat, exts in self.RULES.items():
            if suffix in exts:
                return cat
        return None

    def organize_now(self, path: str = "") -> str:
        """Immediate organization run. Returns summary."""
        if path:
            target = Path(path)
            if target.exists():
                self._organize_folder(target if target.is_dir() else target.parent)
                return f"Organized {path}."
        for folder in self._watched_dirs:
            self._organize_folder(folder)
        return f"Organized {self._organized} files total."

    def stats(self) -> dict:
        return {"organized": self._organized, "watched_dirs": [str(d) for d in self._watched_dirs]}
