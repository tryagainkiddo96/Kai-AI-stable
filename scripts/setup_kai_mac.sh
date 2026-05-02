#!/usr/bin/env bash
set -euo pipefail

echo "[Kai-Mac-Setup] Preparing Kai on macOS..."

# Determine repo root (assuming script located under scripts/ in repo root)
REPO_ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "[Kai-Mac-Setup] Repo root: $REPO_ROOT_DIR"

# Ensure Python3 is available
if ! command -v python3 >/dev/null 2>&1; then
  echo "[Kai-Mac-Setup] Python3 not found. Please install Python3 first (https://www.python.org)."
  exit 1
fi

# Install dependencies
echo "[Kai-Mac-Setup] Installing Python dependencies..."
python3 -m pip install --upgrade pip
if [ -f "$REPO_ROOT_DIR/requirements.txt" ]; then
  python3 -m pip install -r "$REPO_ROOT_DIR/requirements.txt"
fi

# Optional: install Barrier for cross-device mouse/keyboard sharing
if command -v brew >/dev/null 2>&1; then
  if ! command -v barrier >/dev/null 2>&1; then
    echo "[Kai-Mac-Setup] Installing Barrier for cross-device control (optional)…"
    brew install --cask barrier || true
  fi
else
  echo "[Kai-Mac-Setup] Homebrew not detected. Barrier installation skipped. You can install Barrier manually later for cross-device control."
fi

echo "[Kai-Mac-Setup] Starting Kai CLI control panel..."
python3 "$REPO_ROOT_DIR/kai_control_panel.py" --model sam860/dolphin3-llama3.2:3b --workspace "$REPO_ROOT_DIR"
