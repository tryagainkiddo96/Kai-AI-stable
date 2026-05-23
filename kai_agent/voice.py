"""Voice — Windows TTS output via PowerShell SAPI (zero pip)."""
from __future__ import annotations

import subprocess
import threading
import time


class Voice:
    """Speaks text aloud using Windows built-in SAPI speech synthesis."""

    def __init__(self, db=None):
        self.db = db
        self._enabled = False
        self._queue: list[str] = []
        self._queue_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def say(self, text: str, wait: bool = False):
        """Speak text immediately or enqueue."""
        with self._queue_lock:
            self._queue.append(text)
        if wait:
            self._drain()

    def _process_queue(self):
        while self._enabled:
            text = None
            with self._queue_lock:
                if self._queue:
                    text = self._queue.pop(0)
            if text:
                self._speak(text)
            else:
                time.sleep(0.5)

    def _drain(self):
        while True:
            with self._queue_lock:
                if not self._queue:
                    break
            time.sleep(0.3)

    def _speak(self, text: str):
        try:
            safe = text[:500].replace("'", "''").replace('"', '""')
            ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Speak('{safe}')
"""
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=30,
            )
            if self.db:
                self.db.journal_entry("voice", {"text": text[:100]},
                                      source="voice", importance=0)
        except Exception:
            pass

    def speak_async(self, text: str):
        """Non-blocking speak — returns immediately."""
        t = threading.Thread(target=self._speak, args=(text,), daemon=True)
        t.start()
