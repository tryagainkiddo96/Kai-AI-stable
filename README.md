Kai All-in-One Command Center (CLI Panel)

Overview
- A lightweight, all-in-one control surface for Kai: chat with Kai and trigger a safe set of actions (demo, hunt, chess buddy, memory, provider switch, autonomy) from a single UI.
- Cross-platform launchers for Windows, macOS, and Linux. A one-click desktop launcher is available for quick access.
- This README provides quick-start steps to clone, install, and run the CLI panel on your OS.

What’s included
- kai_control_panel.py: CLI control panel (live chat + quick actions)
- kai_control_panel_run.py: wrapper to simplify local runs
- Cross-platform launchers (Windows, macOS, Linux)
- Desktop one-click launcher (Windows batch, macOS command, Bash launcher)
- kai_agent/mcp_lab: minimal MCP demonstration (safe)
- kai_agent/chess_companion: safe Chess Buddy flow
- Demos and helper scripts

Prerequisites
- Python 3.x
- Dependencies: python-chess, requests
- Optional: Ollama (for local LLMs) if you want to use the Ollama path; the panel also works with cloud providers

1) Clone
```
git clone https://github.com/tryagainkiddo96/Kai-AI-stable.git
cd Kai-AI-stable
```

2) Install dependencies
```
pip install --upgrade pip
pip install python-chess requests
```

3) Run the CLI panel (CLI MVP)
- From repo root:
```
python kai_control_panel.py
```
- Or use the wrapper to run from inside kai_agent:
```
python kai_agent/kai_control_panel_run.py
```

4) Quick-launchers (optional)
- Windows: use the one-click launcher at Desktop (Kai_Control_Center.bat) or the PowerShell launcher in scripts/launch_kai.ps1
- macOS: use the macOS .command launcher scripts (scripts/launch_kai_control_center.command) or run the Bash launcher in scripts/launch_kai_control_center.sh
- Linux: run the Bash launcher at scripts/launch_kai_control_center.sh

5) Interacting with Kai
- Use the in-panel chat to ask questions or instruct Kai.
- Use the quick-action commands (1 Hunt Demo, 2 Watch Chess, 3 Ready Check, 4 Demo, 5 Memory, 6 Provider, 7 Autonomy) or type natural language in the chat surface.

6) Optional: Web UI later
- If you want a richer UI, we can port to a lightweight web UI (FastAPI + frontend) in a follow-up step.

Troubleshooting
- If you get ModuleNotFoundError: ensure you run from repo root or set PYTHONPATH to the repo root.
- If Ollama is configured but not running, Kai can auto-start it in the background; ensure Ollama is installed and on PATH if you want auto-start.
- Check dependencies: Python 3.x and pip installed, env vars set as needed.

Contributing
- This is a lean MVP. If you want to extend with more widgets, panels, or actions, follow the existing file structure and add adapters that map to Kai’s existing entry points.
