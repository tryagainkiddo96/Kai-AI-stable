#!/usr/bin/env bash
set -euo pipefail

# Cross-platform Bash launcher for Kai CLI Control Panel (Windows users can use WSL)
# Usage:
#   scripts/launch_kai_control_center.sh [MODEL] [WORKSPACE]
#
# Examples:
#   scripts/launch_kai_control_center.sh sam860/dolphin3-llama3.2:3b \
#     "$HOME/Kai-AI"
#   scripts/launch_kai_control_center.sh \
#     sam860/dolphin3-llama3.2:3b \
#     "/c/Users/you/Desktop/Kai-AI"

MODEL="${1:-sam860/dolphin3-llama3.2:3b}"
WORKSPACE="${2:-$(pwd)/Kai-AI}"

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export KAI_MODEL="$MODEL"
export KAI_WORKSPACE="$WORKSPACE"
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

echo "[Kai Launcher] Starting Kai CLI Control Panel"
echo "  Model:    $MODEL"
echo "  Workspace: $WORKSPACE"

python3 "$ROOT_DIR/kai_agent/kai_control_panel_run.py"
