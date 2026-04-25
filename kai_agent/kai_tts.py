"""
Kai TTS — lightweight text-to-speech for the companion.

Uses platform-native TTS:
- Windows: PowerShell SAPI (built-in)
- Linux/macOS: espeak-ng (install with apt/brew)
- Fallback: silent (no crash)

Usage:
    from kai_agent.kai_tts import KaiTTS
    tts = KaiTTS()
    tts.speak("Hello, I'm Kai.")
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
    def __init__(self, enabled: bool = True, rate: int = 160, voice: str = ""):
        env_style = os.environ.get("KAI_VOICE_STYLE", "").strip().lower()
        env_voice = os.environ.get("KAI_TTS_VOICE", "").strip()
        env_rate = os.environ.get("KAI_TTS_RATE", "").strip()
        if env_rate.isdigit():
            rate = int(env_rate)
        self.style = env_style or "default"
        style_rate_bonus = {"default": 0, "hyperbot": 22, "companion": 8}.get(self.style, 0)
        self.enabled = enabled
        self.base_rate = rate + style_rate_bonus
        self.rate = self.base_rate
        self.voice = voice or env_voice
        self._backend = self._detect_backend()
        self._speaking = False
        self._current_mood = "neutral"
        self._pitch_mod = 0
        self._amp_mod = 0

    def set_mood(self, mood: str) -> None:
        """Adjust voice parameters based on emotional mood."""
        self._current_mood = mood
        mood_profiles = {
            "happy":     {"rate_mod": 15,  "pitch_mod": 5,  "amplitude_mod": 10},
            "excited":   {"rate_mod": 25,  "pitch_mod": 10, "amplitude_mod": 15},
            "sad":       {"rate_mod": -20, "pitch_mod": -5, "amplitude_mod": -10},
            "worried":   {"rate_mod": -5,  "pitch_mod": 0,  "amplitude_mod": 0},
            "tired":     {"rate_mod": -25, "pitch_mod": -8, "amplitude_mod": -15},
            "sleepy":    {"rate_mod": -30, "pitch_mod": -10,"amplitude_mod": -20},
            "curious":   {"rate_mod": 10,  "pitch_mod": 3,  "amplitude_mod": 5},
            "proud":     {"rate_mod": 5,   "pitch_mod": 2,  "amplitude_mod": 10},
            "anxious":   {"rate_mod": 15,  "pitch_mod": 5,  "amplitude_mod": 5},
            "neutral":   {"rate_mod": 0,   "pitch_mod": 0,  "amplitude_mod": 0},
        }
        profile = mood_profiles.get(mood, mood_profiles["neutral"])
        self.rate = max(80, min(250, self.base_rate + profile["rate_mod"]))
        self._pitch_mod = profile["pitch_mod"]
        self._amp_mod = profile["amplitude_mod"]
        if self.style == "hyperbot":
            self.rate = max(90, min(260, self.rate + 10))
            self._pitch_mod = min(20, self._pitch_mod + 8)
            self._amp_mod = min(25, self._amp_mod + 8)

    def _detect_backend(self) -> str:
        """Detect available TTS backend."""
        system = platform.system()
        preferred = os.environ.get("KAI_TTS_BACKEND", "").strip().lower()

        if preferred == "edge-tts" and importlib.util.find_spec("edge_tts"):
            return "edge-tts"

        if importlib.util.find_spec("edge_tts"):
            return "edge-tts"

        if system == "Windows":
            return "sapi"

        # Linux/macOS — check for espeak-ng or espeak
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

        # Clean text for TTS (remove markdown, code blocks, emoji)
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
            if self._backend == "sapi":
                # Windows SAPI via PowerShell
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
            elif self._backend == "edge-tts":
                temp_mp3 = os.path.join(tempfile.gettempdir(), f"kai_tts_{os.getpid()}_{threading.get_ident()}.mp3")
                voice_name = self.voice or os.environ.get("KAI_TTS_VOICE", "en-US-GuyNeural")
                synth_cmd = [
                    sys.executable,
                    "-m",
                    "edge_tts",
                    "--voice",
                    voice_name,
                    "--text",
                    text,
                    "--write-media",
                    temp_mp3,
                ]
                synth = subprocess.run(synth_cmd, timeout=45, capture_output=True, text=True)
                if synth.returncode != 0 or not os.path.exists(temp_mp3):
                    return False
                if platform.system() == "Windows":
                    media_path = temp_mp3.replace("\\", "\\\\")
                    play_cmd = [
                        "powershell",
                        "-Command",
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
                else:
                    return False
            elif self._backend in ("espeak-ng", "espeak"):
                pitch = 50 + getattr(self, '_pitch_mod', 0)
                amp = 120 + getattr(self, '_amp_mod', 0)
                cmd = [self._backend, "-s", str(self.rate), "-p", str(pitch), "-a", str(amp), text]
            elif self._backend == "say":
                cmd = ["say", "-r", str(self.rate), text]
            else:
                return False

            subprocess.run(cmd, timeout=30, capture_output=True)
            return True
        except Exception:
            return False
        finally:
            self._speaking = False

    def _rate_sapi(self) -> int:
        """Convert WPM to SAPI rate (-10 to 10)."""
        # SAPI default is ~150 WPM, range -10 to 10
        return max(-10, min(10, (self.rate - 150) // 15))

    def _clean_for_tts(self, text: str) -> str:
        """Remove markdown formatting and code blocks for clean TTS output."""
        import re

        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', 'code block omitted', text)
        # Remove inline code
        text = re.sub(r'`[^`]+`', '', text)
        # Remove markdown headers
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        # Remove bold/italic markers
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove emoji (common ones)
        text = re.sub(r'[🦊🐾💬🎤✋🔊🔇]', '', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Limit length for TTS (first 2 sentences or 200 chars)
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
