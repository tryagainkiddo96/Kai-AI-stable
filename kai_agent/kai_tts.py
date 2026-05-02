"""
Kai TTS — natural-sounding text-to-speech optimized for conversational use.

Priority: edge-tts (neural voices) > Windows SAPI > espeak > none
Uses Microsoft's neural voices which sound nearly human.
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import importlib.util


class KaiTTS:
    def __init__(self, enabled: bool = True, rate: int = 155, voice: str = "", style: str = ""):
        env_style = os.environ.get("KAI_VOICE_STYLE", style).strip().lower()
        env_voice = os.environ.get("KAI_TTS_VOICE", voice).strip()
        env_rate = os.environ.get("KAI_TTS_RATE", "").strip()
        if env_rate.isdigit():
            rate = int(env_rate)

        self.style = env_style or "natural"
        style_rate_bonus = {
            "default": 0, "natural": 0, "hyperbot": 22,
            "companion": 8, "sales": -5,
        }.get(self.style, 0)

        self.enabled = enabled
        self.base_rate = rate + style_rate_bonus
        self.rate = self.base_rate

        # Default to the most natural-sounding neural voice
        if self.style == "sales":
            self.voice = env_voice or "en-US-GuyNeural"
            self.base_rate = 150
            self.rate = self.base_rate
        else:
            self.voice = env_voice or "en-US-ChristopherNeural"

        self._backend = self._detect_backend()
        self._speaking = False
        self._current_mood = "neutral"
        self._pitch_mod = 0
        self._amp_mod = 0

        # Sales-specific settings
        self._sales_mode = self.style == "sales"
        self._warmth = 0  # -10 to +10, adjusts pitch for warmth

    def set_mood(self, mood: str) -> None:
        """Adjust voice parameters based on emotional mood."""
        self._current_mood = mood
        mood_profiles = {
            "happy":     {"rate_mod": 10,  "pitch_mod": 3,  "amplitude_mod": 8},
            "excited":   {"rate_mod": 18,  "pitch_mod": 6,  "amplitude_mod": 12},
            "sad":       {"rate_mod": -18, "pitch_mod": -4, "amplitude_mod": -8},
            "worried":   {"rate_mod": -5,  "pitch_mod": 0,  "amplitude_mod": 0},
            "tired":     {"rate_mod": -22, "pitch_mod": -6, "amplitude_mod": -12},
            "sleepy":    {"rate_mod": -28, "pitch_mod": -8, "amplitude_mod": -18},
            "curious":   {"rate_mod": 8,   "pitch_mod": 2,  "amplitude_mod": 4},
            "proud":     {"rate_mod": 3,   "pitch_mod": 1,  "amplitude_mod": 8},
            "anxious":   {"rate_mod": 12,  "pitch_mod": 4,  "amplitude_mod": 4},
            "neutral":   {"rate_mod": 0,   "pitch_mod": 0,  "amplitude_mod": 0},
            "confident": {"rate_mod": -3,  "pitch_mod": -1, "amplitude_mod": 5},
            "friendly":  {"rate_mod": 5,   "pitch_mod": 2,  "amplitude_mod": 6},
            "empathetic":{"rate_mod": -10, "pitch_mod": -2, "amplitude_mod": -3},
            "urgent":    {"rate_mod": 20,  "pitch_mod": 5,  "amplitude_mod": 10},
        }
        profile = mood_profiles.get(mood, mood_profiles["neutral"])
        self.rate = max(80, min(250, self.base_rate + profile["rate_mod"]))
        self._pitch_mod = profile["pitch_mod"]
        self._amp_mod = profile["amplitude_mod"]
        if self.style == "hyperbot":
            self.rate = max(90, min(260, self.rate + 10))
            self._pitch_mod = min(20, self._pitch_mod + 8)
            self._amp_mod = min(25, self._amp_mod + 8)
        if self._sales_mode:
            self.rate = max(130, min(170, self.rate))
            self._pitch_mod = max(-3, min(3, self._pitch_mod))
            self._amp_mod = max(0, min(15, self._amp_mod + 3))

    def _detect_backend(self) -> str:
        """Detect available TTS backend. Prefer edge-tts (neural)."""
        system = platform.system()
        preferred = os.environ.get("KAI_TTS_BACKEND", "").strip().lower()

        # Always prefer edge-tts if available — it's the most natural
        if importlib.util.find_spec("edge_tts"):
            return "edge-tts"

        if preferred == "edge-tts":
            return "edge-tts"

        if system == "Windows":
            return "sapi"

        if shutil.which("espeak-ng"):
            return "espeak-ng"
        if shutil.which("espeak"):
            return "espeak"
        if system == "Darwin" and shutil.which("say"):
            return "say"

        return "none"

    @property
    def available(self) -> bool:
        return self._backend != "none" and self.enabled

    def speak(self, text: str, blocking: bool = False) -> bool:
        """Speak text. Returns True if TTS was started."""
        if not self.available or not text.strip():
            return False

        clean = self._clean_for_tts(text)
        if not clean.strip():
            return False

        if blocking:
            return self._run_tts(clean)
        else:
            thread = threading.Thread(target=self._run_tts, args=(clean,), daemon=True)
            thread.start()
            return True

    def _run_tts(self, text: str) -> bool:
        """Run the TTS command."""
        if self._speaking:
            return False
        self._speaking = True
        try:
            if self._backend == "edge-tts":
                return self._run_edge_tts(text)
            elif self._backend == "sapi":
                return self._run_sapi(text)
            elif self._backend in ("espeak-ng", "espeak"):
                return self._run_espeak(text)
            elif self._backend == "say":
                return self._run_say(text)
            return False
        except Exception:
            return False
        finally:
            self._speaking = False

    def _run_edge_tts(self, text: str) -> bool:
        """Use edge-tts neural voices — the most natural sounding."""
        temp_mp3 = os.path.join(
            tempfile.gettempdir(),
            f"kai_tts_{os.getpid()}_{threading.get_ident()}.mp3",
        )
        voice_name = self.voice or "en-US-ChristopherNeural"
        rate_str = f"+{self.rate - 150}Hz" if self.rate > 150 else f"{self.rate - 150}Hz"
        pitch_str = f"+{self._pitch_mod * 2}Hz" if self._pitch_mod > 0 else f"{self._pitch_mod * 2}Hz"

        try:
            synth_cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice_name,
                "--text", text,
                "--rate", rate_str,
                "--pitch", pitch_str,
                "--write-media", temp_mp3,
            ]
            synth = subprocess.run(synth_cmd, timeout=45, capture_output=True, text=True)
            if synth.returncode != 0 or not os.path.exists(temp_mp3):
                return False

            if platform.system() == "Windows":
                media_path = temp_mp3.replace("\\", "\\\\")
                play_cmd = [
                    "powershell", "-Command",
                    "Add-Type -AssemblyName presentationCore; "
                    f"$player = New-Object System.Windows.Media.MediaPlayer; "
                    f"$player.Open([Uri]'file:///{media_path}'); "
                    "while (-not $player.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 100 }; "
                    "$player.Volume = 1.0; "
                    "$player.Play(); "
                    "$duration = [Math]::Min(18000, [Math]::Max(1200, [int]$player.NaturalDuration.TimeSpan.TotalMilliseconds + 250)); "
                    "Start-Sleep -Milliseconds $duration; "
                    "$player.Stop(); "
                    "$player.Close();"
                ]
                subprocess.run(play_cmd, timeout=30, capture_output=True)
                return True
            return False
        except Exception:
            return False

    def _run_sapi(self, text: str) -> bool:
        """Windows SAPI via PowerShell."""
        escaped = text.replace("'", "''")
        voice_block = ""
        if self.voice:
            voice_escaped = self.voice.replace("'", "''")
            voice_block = (
                f"$voice = $synth.GetInstalledVoices() | "
                f"ForEach-Object {{ $_.VoiceInfo.Name }} | "
                f"Where-Object {{ $_ -like '*{voice_escaped}*' }} | "
                f"Select-Object -First 1; "
                f"if ($voice) {{ $synth.SelectVoice($voice) }}; "
            )
        cmd = [
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$synth.Rate = {self._rate_sapi()}; "
            f"{voice_block}"
            f"$synth.Speak('{escaped}')"
        ]
        subprocess.run(cmd, timeout=30, capture_output=True)
        return True

    def _run_espeak(self, text: str) -> bool:
        """espeak/espeak-ng synthesis."""
        pitch = 50 + getattr(self, '_pitch_mod', 0)
        amp = 120 + getattr(self, '_amp_mod', 0)
        cmd = [self._backend, "-s", str(self.rate), "-p", str(pitch), "-a", str(amp), text]
        subprocess.run(cmd, timeout=30, capture_output=True)
        return True

    def _run_say(self, text: str) -> bool:
        """macOS say command."""
        cmd = ["say", "-r", str(self.rate), text]
        subprocess.run(cmd, timeout=30, capture_output=True)
        return True

    def _rate_sapi(self) -> int:
        """Convert WPM to SAPI rate (-10 to 10)."""
        return max(-10, min(10, (self.rate - 150) // 15))

    def _clean_for_tts(self, text: str) -> str:
        """Remove markdown, code, and formatting for clean speech."""
        import re

        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'---\n', '', text)
        text = re.sub(r'[🦊🐾💬🎤✋🔊🔇]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # For sales mode, keep it conversational — speak the first 3-4 sentences
        if self._sales_mode:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) > 4:
                text = ' '.join(sentences[:4])
            if len(text) > 300:
                text = text[:297] + '...'
        else:
            sentences = text.split('. ')
            if len(sentences) > 2:
                text = '. '.join(sentences[:2]) + '.'
            if len(text) > 200:
                text = text[:197] + '...'

        return text

    def stop(self):
        """Stop current speech (best effort)."""
        self._speaking = False

    def toggle(self) -> bool:
        """Toggle TTS on/off. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled

    def set_voice(self, voice_name: str) -> str:
        """Set the voice to use. Returns the voice that was set."""
        self.voice = voice_name
        return voice_name

    def list_available_voices(self) -> list[str]:
        """List available edge-tts neural voices."""
        if self._backend != "edge-tts":
            return ["edge-tts not installed — run: pip install edge-tts"]

        try:
            result = subprocess.run(
                [sys.executable, "-m", "edge_tts", "--list-voices"],
                capture_output=True, text=True, timeout=15,
            )
            voices = []
            for line in result.stdout.splitlines():
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                    if name.startswith("en-"):
                        voices.append(name)
            return voices[:30] if voices else ["No English voices found"]
        except Exception:
            return ["Failed to list voices"]

    def set_sales_mode(self, enabled: bool) -> None:
        """Enable sales-optimized voice settings."""
        self._sales_mode = enabled
        if enabled:
            self.base_rate = 150
            self.rate = 150
            if not self.voice or "Guy" not in self.voice:
                self.voice = "en-US-GuyNeural"
        else:
            self.base_rate = 155
            self.rate = 155
