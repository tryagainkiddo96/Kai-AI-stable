#!/usr/bin/env python3
"""Kali-friendly launcher for Kai (Python-first path).

Clones/pulls Kai-AI-stable, sets up a Python venv, installs deps, and launches the CLI panel.
No bash required beyond Python. Safe for Kali Linux environments.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/tryagainkiddo96/Kai-AI-stable.git"
DEST = Path.home() / "Kai-AI-stable"

def ensure_repo():
    if not DEST.exists():
        subprocess.run([sys.executable, "-m", "git", "clone", REPO, str(DEST)], check=True)
    else:
        subprocess.run(["git", "-C", str(DEST), "pull", "--ff-only"], check=True)

def ensure_venv():
    venv = DEST / "venv"
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    return venv

def get_python_exe(venv: Path) -> Path:
    if (venv / "bin" / "python3").exists():
        return venv / "bin" / "python3"
    return venv / "bin" / "python"

def main():
    print("[Kai-Kali] Setting up Kai on Kali Linux (Python-first path)")
    ensure_repo()
    venv = ensure_venv()
    py = get_python_exe(venv)
    # Install deps
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-r", str(DEST / "requirements.txt")], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "python-chess"], check=True)
    # Run panel
    panel = DEST / "kai_control_panel.py"
    print(f"[Kai-Kali] Launching panel at {panel}")
    subprocess.run([str(py), str(panel)], check=False)

if __name__ == "__main__":
    main()
