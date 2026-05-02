#!/usr/bin/env python3
"""
KAI DASHBOARD -- Beautiful Terminal UI
====================================
Cross-platform entry point for Kai AI dashboard.

This wrapper auto-detects the environment and imports from kai_agent package.

Usage:
    python kai_dashboard.py
    python kai_dashboard.py --model llama3.2:3b
    python kai_dashboard.py --provider deepseek --model deepseek-chat
    python kai_dashboard.py --provider ollama

Controls:
    /provider <name> [model]  Switch LLM provider
    /model <name>             Change model
    /menu                     Show interactive menu
    /clear                    Clear chat history
    /help                     Show commands
    /exit                     Quit
"""

import os
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Add parent directory to Python path (for kai_agent import)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Set workspace to the script's directory
WORKSPACE = SCRIPT_DIR

# Now import and run the actual dashboard from kai_agent
if __name__ == "__main__":
    # Check if we need to set up environment for WSL
    if os.path.exists("/mnt/c"):
        # We're in WSL, check if running via cmd.exe
        wsl_prefix = os.environ.get("WSL_DISTRO", "")
        if wsl_prefix:
            # Set PYTHONPATH for Windows Python interop
            win_path = "/mnt/c/Users/7nujy6xc/OneDrive/Desktop/Kai-AI"
            if os.path.exists(win_path):
                os.environ["PYTHONPATH"] = win_path

    # Run the actual dashboard from kai_agent
    from kai_agent.kai_dashboard import main
    main()
