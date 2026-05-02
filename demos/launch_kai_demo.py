#!/usr/bin/env python3
"""Launch Kai with updated MCP Hunt + Chess Buddy flows safely.
Ensures Ollama is running, starts Kai, runs a quick lab demo:
- lab_topology MCP hunt (parallel simulated agents)
- watch chess (board-aware buddy)

This is for quick, repeatable demos and does not touch real targets.
"""
from __future__ import annotations

import os
import time
import shutil
import subprocess
from pathlib import Path

def ensure_ollama_running() -> bool:
    # Simple check: try to reach Ollama API, if not running, try to start it
    import urllib.request
    client_ready = False
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        client_ready = True
    except Exception:
        client_ready = False
    if client_ready:
        return True
    # Try to start Ollama
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        print("[Launcher] Ollama not found on PATH; cannot auto-start.")
        return False
    try:
        subprocess.Popen([ollama_path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[Launcher] Starting Ollama in background...")
        # Wait briefly for Ollama to come up
        for _ in range(20):
            time.sleep(1)
            try:
                urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
                return True
            except Exception:
                continue
        print("[Launcher] Ollama start timeout.")
        return False
    except Exception as e:
        print(f"[Launcher] Failed to start Ollama: {e}")
        return False

def run_demo():
    # Lazy imports to keep startup fast
    from kai_agent.mcp_lab.orchestrator import run_demo_hunt
    from kai_agent.chess_companion import ChessCompanion
    import json

    report = run_demo_hunt("lab_topology")
    print("[Demo] MCP Hunt Report:\n" + report)
    cc = ChessCompanion()
    chess_out = cc.watch_board()
    print("[Demo] Chess Companion Output:\n" + chess_out)

    out_path = Path("demo_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("MCP Hunt Report:\n" + report + "\n\nChess Companion Output:\n" + chess_out)
    print(f"[Demo] Output saved to {out_path}")

def main():
    ensure_ollama_running()
    run_demo()

if __name__ == "__main__":
    main()
