#!/usr/bin/env bash
set -euo pipefail

# Minimal cross-platform launcher for Kai WebUI MVP path (CLI will work too).
# Usage:
#   ./scripts/launch_kai.sh "$MODEL" "$WORKSPACE"
MODEL="${1:-sam860/dolphin3-llama3.2:3b}"
WORKSPACE="${2:-$(pwd)/Kai-AI}"

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

echo "[Kai Launcher] Starting Kai with model=$MODEL workspace=$WORKSPACE"
python -m kai_agent.assistant --model "$MODEL" --workspace "$WORKSPACE"
