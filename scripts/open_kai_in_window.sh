#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-sam860/dolphin3-llama3.2:3b}"
WORKSPACE="${2:-$HOME/Kai-AI}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "$(uname)" in
  Darwin)
    # macOS: open a new Terminal window and run Kai
    osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT_DIR'; python3 kai_control_panel.py --model '$MODEL' --workspace '$WORKSPACE'\""
    ;;
  Linux)
    if command -v gnome-terminal >/dev/null 2>&1; then
      gnome-terminal -- bash -lc "cd '$ROOT_DIR'; python3 kai_control_panel.py --model '$MODEL' --workspace '$WORKSPACE'; exec bash"
    elif command -v xterm >/dev/null 2>&1; then
      xterm -hold -e "bash -lc 'cd '$ROOT_DIR'; python3 kai_control_panel.py --model '$MODEL' --workspace '$WORKSPACE''" \\
      || true
    else
      echo "[Kai] No supported terminal found (gnome-terminal/xterm). Running in current terminal...";
      cd "$ROOT_DIR"; python3 kai_control_panel.py --model "$MODEL" --workspace "$WORKSPACE"
    fi
    ;;
  *)
    echo "Unsupported OS for this launcher. Run manually: cd '$ROOT_DIR' && python3 kai_control_panel.py --model '$MODEL' --workspace '$WORKSPACE'"
    ;;
esac
