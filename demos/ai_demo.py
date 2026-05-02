#!/usr/bin/env python3
"""Educational, safe demo runner for MCP Hunt + Chess Companion flows.
Runs a safe lab hunt and a chess buddy session and dumps outputs for filming.
"""
from __future__ import annotations

import sys
import textwrap

try:
    from kai_agent.mcp_lab.orchestrator import run_demo_hunt
    from kai_agent.chess_companion import ChessCompanion
except Exception as e:
    print(f"Error importing demo modules: {e}")
    sys.exit(1)

def main() -> int:
    print("[Demo] Starting MCP Hunt demonstration (lab_topology)…")
    try:
        report = run_demo_hunt("lab_topology")
        print("[Demo] MCP Hunt Report:\n" + report)
    except Exception as e:
        print(f"[Demo] MCP Hunt failed: {e}")
        report = str(e)

    print("\n[Demo] Starting Chess Companion demonstration…")
    try:
        cc = ChessCompanion()
        chess_out = cc.watch_board()
        print("[Demo] Chess Companion Output:\n" + chess_out)
    except Exception as e:
        print(f"[Demo] Chess Companion failed: {e}")
        chess_out = str(e)

    # Persist a short, shareable log for the video
    out_path = Path("demo_output.txt")
    try:
        from pathlib import Path
        Path(".").mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("Demo MCP Hunt:\n" + report + "\n\nChess Companion:\n" + chess_out)
        print(f"[Demo] Output saved to {out_path}")
    except Exception:
        pass

    return 0

if __name__ == "__main__":
    sys.exit(main())
