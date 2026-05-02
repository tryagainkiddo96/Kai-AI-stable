#!/usr/bin/env python3
# kai_agent/config_manager.py
# Configuration management for Kai's multi-provider LLM support
# Adapted from KaliGPT's agent_configs.py
# Updated: 2026

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


# --- CONFIG FILE PATH ---
CONFIG_FILE = Path(__file__).resolve().parent / "data" / "kai_config.json"


DEFAULT_CONFIG = {
    "default_model": "qwen3:4b-q4_K_M",
    "default_provider": "ollama",
    "providers": {
        "ollama": {
            "api_key": "http://localhost:11434",
            "default_model": "qwen3:4b-q4_K_M",
            "models": [
                "qwen3:4b-q4_K_M",
                "llama3.2:3b",
                "mistral:latest",
                "llama2:latest"
            ]
        },
        "huggingface": {
            "api_key": os.environ.get("HF_API_KEY", ""),
            "default_model": "microsoft/Phi-3-mini-4k-instruct",
            "models": [
                "microsoft/Phi-3-mini-4k-instruct",
                "google/gemma-2b-it",
                "meta-llama/Llama-2-7b-chat-hf"
            ]
        },
        "deepseek": {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "default_model": "deepseek-chat",
            "models": [
                "deepseek-chat",
                "deepseek-reasoner",
                "deepseek-coder"
            ]
        },
        "groq": {
            "api_key": os.environ.get("GROQ_API_KEY", ""),
            "default_model": "llama-3.1-8b-instant",
            "models": [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ]
        },
        "codex": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "default_model": "gpt-4o",
            "models": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-3.5-turbo"
            ]
        }
    }
}


def _ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_config() -> Dict[str, Any]:
    """Load config from JSON file."""
    _ensure_config_dir()
    
    try:
        if not CONFIG_FILE.exists():
            _save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
            
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data
            
    except (FileNotFoundError, json.JSONDecodeError):
        _save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def _save_config(data: Dict[str, Any]) -> bool:
    """Save config to JSON file."""
    try:
        _ensure_config_dir()
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"[!] Error saving config: {e}")
        return False


# --- PROVIDER ACCESS ---

def get_default_model() -> str:
    """Get the global default model."""
    return _load_config().get("default_model", "qwen3:4b-q4_K_M")


def get_default_provider() -> str:
    """Get the global default provider."""
    return _load_config().get("default_provider", "ollama")


def update_default_model(model: str) -> bool:
    """Update the global default model."""
    data = _load_config()
    data["default_model"] = model
    return _save_config(data)


def update_default_provider(provider: str) -> bool:
    """Update the global default provider."""
    data = _load_config()
    data["default_provider"] = provider
    return _save_config(data)


def get_available_providers() -> List[str]:
    """Get all configured providers."""
    data = _load_config()
    return list(data.get("providers", {}).keys())


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    data = _load_config()
    return data.get("providers", {}).get(provider, {}).get("api_key")


def get_provider_default_model(provider: str) -> Optional[str]:
    """Get default model for a provider."""
    data = _load_config()
    return data.get("providers", {}).get(provider, {}).get("default_model")


def get_provider_models(provider: str) -> List[str]:
    """Get all models for a provider."""
    data = _load_config()
    return data.get("providers", {}).get(provider, {}).get("models", [])


def set_api_key(provider: str, api_key: str) -> bool:
    """Set API key for a provider."""
    data = _load_config()
    if provider in data.get("providers", {}):
        data["providers"][provider]["api_key"] = api_key
        return _save_config(data)
    return False


def set_provider_default_model(provider: str, model: str) -> bool:
    """Set default model for a provider."""
    data = _load_config()
    if provider in data.get("providers", {}):
        data["providers"][provider]["default_model"] = model
        return _save_config(data)
    return False


def add_provider(
    provider: str, 
    api_key: str, 
    default_model: str, 
    models: List[str]
) -> bool:
    """Add a new provider."""
    data = _load_config()
    data["providers"][provider] = {
        "api_key": api_key,
        "default_model": default_model,
        "models": models
    }
    return _save_config(data)


def remove_provider(provider: str) -> bool:
    """Remove a provider."""
    data = _load_config()
    if provider in data.get("providers", {}):
        del data["providers"][provider]
        return _save_config(data)
    return False


def get_config_summary() -> Dict[str, Any]:
    """Get a summary of the configuration."""
    data = _load_config()
    providers = data.get("providers", {})
    
    summary = {
        "default_provider": data.get("default_provider"),
        "default_model": data.get("default_model"),
        "providers": {}
    }
    
    for name, config in providers.items():
        summary["providers"][name] = {
            "default_model": config.get("default_model"),
            "models_count": len(config.get("models", [])),
            "has_api_key": bool(config.get("api_key"))
        }
    
    return summary


if __name__ == "__main__":
    print("--- Kai Config ---")
    print(json.dumps(get_config_summary(), indent=2))
