#!/usr/bin/env bash
set -euo pipefail

echo "[Kai-Mac-PostClone] Starting post-clone setup."

REPO_ROOT_DIR=$(pwd)
if [[ ! -d "$REPO_ROOT_DIR/.git" ]]; then
  echo "[Kai-Mac-PostClone] Not inside a git repo. Please cd into your Kai-AI repo before running this script."
  exit 1
fi

if command -v brew >/dev/null 2>&1; then
  echo "[Kai-Mac-PostClone] Homebrew detected. Proceeding with mac setup."
  bash ./scripts/setup_kai_mac.sh
else
  echo "[Kai-Mac-PostClone] Homebrew not found. Please install dependencies manually via the mac setup script."
  bash ./scripts/setup_kai_mac.sh
fi

echo "[Kai-Mac-PostClone] Post-clone setup complete. You can start the CLI panel with:"
echo "  - Double-click scripts/launch_kai_control_center.command"
echo "  - Or run: python kai_control_panel.py --model sam860/dolphin3-llama3.2:3b --workspace \"$REPO_ROOT_DIR\""
