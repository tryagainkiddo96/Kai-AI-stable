#!/usr/bin/env bash
set -euo pipefail

echo "[Kai-Kali] Starting Kai all-in-one CLI on Kali Linux..."
REPO="https://github.com/tryagainkiddo96/Kai-AI-stable.git"
DEST="$HOME/Kai-AI-stable"

if [ -d "$DEST/.git" ]; then
  echo "[Kai-Kali] Repo already present at $DEST, pulling latest..."
  git -C "$DEST" pull --ff-only || true
  cd "$DEST"
else
  echo "[Kai-Kali] Cloning repository to $DEST"
  git clone "$REPO" "$DEST"
  cd "$DEST"
fi

# Create/activate Python venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install python-chess requests

# Launch the CLI control panel
echo "[Kai-Kali] Launching Kai control panel..."
python kai_control_panel.py
## If you prefer the wrapper: python kai_agent/kai_control_panel_run.py
