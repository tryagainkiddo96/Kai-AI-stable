Kai All-in-One Command Center for macOS

Overview
- This guide helps you bootstrap Kai on macOS and boot the CLI control center quickly.
- It uses a small post-clone setup script to install dependencies and start Kai’s CLI panel.

Prereqs
- macOS with Homebrew installed (optional if you want Barrier support later)
- Python 3.x
- Internet access for package installs

Getting started
1) Clone the repository on your Mac
- git clone https://github.com/tryagainkiddo96/Kai-AI-stable.git
- cd Kai-AI-stable

2) Run post-clone setup (macOS)
- bash scripts/post_clone_setup_mac.sh
- This will install Python dependencies and launch Kai’s CLI panel. It also tries to install Barrier if Homebrew is present (optional for cross-device control later).

3) (Optional) Prepare cross-device setup
- If you plan to work with Barrier for multi-device control, install Barrier and follow its setup steps as described in its docs.

4) Launch Kai CLI panel manually (if not auto-launched)
- python kai_control_panel.py
- Or via the wrapper: python kai_agent/kai_control_panel_run.py

5) Quick tips
- Default model/workspace are defined in the script. You can override by editing the script or passing flags in the CLI.
- Use the CLI panel to chat with Kai and trigger quick actions (hunt, chess, etc.).

Notes
- This is a development-friendly bootstrap. For production deployments, consider adding a proper service wrapper, logging, and authentication.
