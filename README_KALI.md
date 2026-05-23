# Kali Linux Quick Start for Kai All-in-One Control Center

- This guide shows a straightforward path to clone and run Kai on Kali Linux.
- It uses a minimal, safe environment and a Python virtualenv.

- Copy-paste into your terminal:

bash
set -euo pipefail
REPO="https://github.com/tryagainkiddo96/Kai-AI-stable.git"
DEST="$HOME/Kai-AI-stable"
git clone "$REPO" "$DEST"
cd "$DEST"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install python-chess requests
python kai_control_panel.py

- If you want a one-shot launcher, run:
- bash scripts/start_kai_kali.sh
