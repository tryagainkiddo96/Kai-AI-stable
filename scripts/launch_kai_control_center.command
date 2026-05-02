#!/usr/bin/env bash
## macOS Terminal app launcher for Kai CLI Control Panel
## Usage: double-click this file on macOS or run from Terminal
##       ./scripts/launch_kai_control_center.command

MODEL="sam860/dolphin3-llama3.2:3b"
WORKSPACE="$HOME/Kai-AI"
ROOT_DIR="$(cd "$(dirname "$BASH_SOURCE[0]")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"
echo "[Kai Launcher] Starting Kai CLI Control Panel"
python3 "$ROOT_DIR/kai_control_panel.py" --model "$MODEL" --workspace "$WORKSPACE"
