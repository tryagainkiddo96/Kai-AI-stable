Release: Kai All-in-One Command Center (v1.0.0)

Overview
- First stable release of the all-in-one Kai control surface: a CLI-based panel with safe, one-click actions and a chat surface to interact with Kai. Includes cross-platform launchers for Windows, macOS, and Linux, plus a one-click desktop launcher for quick-starts.

What’s included in this release
- Kai Control Panel CLI (kai_control_panel.py) and wrapper (kai_control_panel_run.py)
- Cross-platform launchers:
  - Windows: launch_kai.ps1, batch launcher, and a one-click launcher to Desktop
  - macOS: command-based launcher (.command) plus Bash launcher
  - Linux: Bash launcher
- Desktop launcher: copy-to-desktop script for easy access
- Mac/Win launch wrappers to start Kai with default model/workspace
- Lightweight demo flows (safe, lab-style) including:
  - MCP-lite lab hunt (safe, parallel agents)
  - Chess companion (watch chess) via a safe, explainable interface
- New helper: kai_agent/mcp_lab with a minimal MCP orchestrator
- New helper: kai_agent/chess_companion for safe chess analysis and narration
- A tiny demo harnesses under demos/ for quick show-and-tell

Usage (quick start)
- Windows: use the desktop launcher or the PowerShell batch launcher
- macOS/Linux: use the provided .command or .sh launchers
- CLI: run python kai_control_panel.py or python -m kai_agent.assistant --model <model> --workspace <path>

Notes
- This release emphasizes safety: no destructive actions are exposed by default. Higher-risk capabilities can be enabled with explicit user confirmation and audit trails.
- If you need to revert, revert to the previous commit and tag v0.x.x as needed.
