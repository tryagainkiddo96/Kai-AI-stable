"""Kai Config — unified configuration system."""
from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULTS = {
    "provider": "ollama",
    "model": "llama3.2:3b",
    "ollama_base_url": "http://127.0.0.1:11434",
    "primary_timeout": 45,
    "fallback_timeout": 25,
    "fallback_models": "sam860/dolphin3-llama3.2:3b,qwen3:4b-q4_K_M,llama2:latest,mistral:latest",
    "max_history": 12,
    "summary_turn_window": 8,
    "summary_char_limit": 1200,
    "temperature": 0.7,
    "repeat_penalty": 1.15,
    "num_predict": 512,
    "num_ctx": 4096,
    "tts_enabled": False,
    "codex_reasoning_effort": "low",
    "codex_sandbox": "read-only",
    "deepseek_api_key": "",
    "groq_api_key": "",
    "hf_api_key": "",
    "tavily_api_key": "",
    "tesseract_path": "",
    "bridge_url": "ws://127.0.0.1:8765",
    "bridge_token": "",
    "policy_mode": "power-user",
}


class KaiConfig:
    """Unified configuration loaded from env > config file > defaults."""

    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = workspace or Path(".")
        self.config_path = self.workspace / "kai_config.json"
        self._values = dict(DEFAULTS)
        self._load_config_file()
        self._load_env_vars()

    def _load_config_file(self) -> None:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                for key in data:
                    mapped = self._map_key(key)
                    if mapped in self._values:
                        self._values[mapped] = data[key]
            except Exception:
                pass

    def _load_env_vars(self) -> None:
        env_map = {
            "KAI_PROVIDER": "provider",
            "KAI_MODEL": "model",
            "OLLAMA_HOST": "ollama_base_url",
            "KAI_PRIMARY_MODEL_TIMEOUT": "primary_timeout",
            "KAI_FALLBACK_MODEL_TIMEOUT": "fallback_timeout",
            "KAI_FALLBACK_MODELS": "fallback_models",
            "KAI_MAX_HISTORY": "max_history",
            "KAI_SUMMARY_TURN_WINDOW": "summary_turn_window",
            "KAI_SUMMARY_CHAR_LIMIT": "summary_char_limit",
            "KAI_TEMPERATURE": "temperature",
            "KAI_REPEAT_PENALTY": "repeat_penalty",
            "KAI_NUM_PREDICT": "num_predict",
            "KAI_NUM_CTX": "num_ctx",
            "KAI_TTS": "tts_enabled",
            "KAI_CODEX_REASONING_EFFORT": "codex_reasoning_effort",
            "KAI_CODEX_SANDBOX": "codex_sandbox",
            "DEEPSEEK_API_KEY": "deepseek_api_key",
            "DS_API_KEY": "deepseek_api_key",
            "GROQ_API_KEY": "groq_api_key",
            "HF_API_KEY": "hf_api_key",
            "HUGGINGFACE_API_KEY": "hf_api_key",
            "TAVILY_API_KEY": "tavily_api_key",
            "KAI_BRIDGE_URL": "bridge_url",
            "KAI_BRIDGE_TOKEN": "bridge_token",
        }
        for env_key, config_key in env_map.items():
            val = os.environ.get(env_key, "").strip()
            if val:
                if config_key in {"tts_enabled"}:
                    self._values[config_key] = val.lower() in ("1", "true", "yes")
                elif config_key in {"primary_timeout", "fallback_timeout", "max_history", "summary_turn_window", "summary_char_limit", "num_predict", "num_ctx"}:
                    try:
                        self._values[config_key] = int(val)
                    except ValueError:
                        pass
                elif config_key in {"temperature", "repeat_penalty"}:
                    try:
                        self._values[config_key] = float(val)
                    except ValueError:
                        pass
                else:
                    self._values[config_key] = val

    def _map_key(self, key: str) -> str:
        mapping = {
            "tesseract_path": "tesseract_path",
            "deepseek_api_key": "deepseek_api_key",
            "groq_api_key": "groq_api_key",
            "hf_api_key": "hf_api_key",
            "tavily_api_key": "tavily_api_key",
        }
        return mapping.get(key, key)

    def get(self, key: str, default=None):
        return self._values.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        val = self._values.get(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self._values.get(key, default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self._values.get(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("1", "true", "yes")

    def get_str(self, key: str, default: str = "") -> str:
        val = self._values.get(key, default)
        return str(val) if val else default

    def set(self, key: str, value) -> None:
        self._values[key] = value

    def save(self) -> None:
        serializable = {}
        for k, v in self._values.items():
            if k.endswith("_api_key"):
                serializable[k] = v
            elif k == "tesseract_path":
                serializable[k] = v
            else:
                serializable[k] = v
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    def summary(self) -> str:
        lines = ["Kai Configuration:"]
        for key, val in sorted(self._values.items()):
            if key.endswith("_api_key") and val:
                val = val[:4] + "..." + val[-4:]
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)
