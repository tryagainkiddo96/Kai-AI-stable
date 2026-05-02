#!/usr/bin/env python3
"""Launcher for Kai Control Panel from within kai_agent directory.
This wrapper sets up import paths so kai_control_panel.py (in repo root)
can be executed from this subdirectory without modifying user envs.
"""
from __future__ import annotations

import sys
from pathlib import Path

def main():
    # Compute repo root (assumes this script lives under <repo>/kai_agent)
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    try:
        import kai_control_panel  # noqa: F401
        # Call main() from the module we added at repo root
        kai_control_panel.main()
    except Exception as e:
        print(f"[Kai Control Panel Launcher] Failed to start: {e}")
        raise

if __name__ == "__main__":
    main()
