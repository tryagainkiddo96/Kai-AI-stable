#!/usr/bin/env python3
"""Lightweight CLI Control Panel for Kai (All-in-One UX).
Provides a chat surface and a handful of quick actions that map to Kai's core capabilities.
Safe, non-destructive by default. For demonstration and testing in a local environment.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

try:
    from kai_agent.assistant import KaiAssistant
except Exception as e:
    print(f"[ERR] Failed to import Kai assistant: {e}")
    sys.exit(1)


def display_help():
    print("""Commands:
- Type any natural language to chat with Kai (eg. 'What can you do?')
- hunt lab_topology        -> Run the safe MCP hunt (in background if available)
- watch chess              -> Start Chess Buddy flow
- /ready                   -> Check readiness of components
- demo                    -> Run a quick demo sequence
- memory                  -> View memory notes
- provider <name> <model> -> Switch LLM/provider on the fly
- autonomy <tick|on|off>  -> Control autonomy
- help                    -> Show this help
- exit                    -> Quit


def render_status(cli: KaiAssistant) -> None:
    ollama = "ready" if getattr(cli, "_ollama_ready", False) else "not ready"
    mcp = "ready" if getattr(cli, "_mcp_ready", True) else "not ready"
    chess = "ready" if getattr(cli, "_chess_ready", False) else "not ready"
    print(f"[Status] Ollama: {ollama} | Kai: ready | MCP: {mcp} | Chess: {chess}")


def display_menu():
    print("""Commands:
1) Hunt Demo
2) Watch Chess
3) Ready Check
4) Demo Sequence
5) Memory View
6) Provider Switch
7) Autonomy Tick
0) Chat
q) Quit
""")


def main():
    workspace = Path(os.environ.get("KAI_WORKSPACE", str(Path('.').resolve())))
    model = os.environ.get("KAI_MODEL", "sam860/dolphin3-llama3.2:3b")
    cli = KaiAssistant(model=model, workspace=workspace)

    print("[Kai Control Panel] Ready. Type 'help' for commands. Type '/exit' to quit.")
    while True:
        render_status(cli)
        display_menu()
        choice = input("Choice> ").strip()
        if not choice:
            continue
        if choice.lower() in {"q", "exit"}:
            break
        if choice == "0":
            chat_text = input("Chat> ").strip()
            if chat_text:
                resp = asyncio.run(cli.ask(chat_text))
                print(resp)
            continue
        if choice == "1":
            resp = asyncio.run(cli.ask("hunt lab_topology")); print(resp); continue
        if choice == "2":
            resp = asyncio.run(cli.ask("watch chess")); print(resp); continue
        if choice == "3":
            resp = asyncio.run(cli.ask("/ready")); print(resp); continue
        if choice == "4":
            resp = asyncio.run(cli.ask("demo")); print(resp); continue
        if choice == "5":
            resp = asyncio.run(cli.ask("memory")); print(resp); continue
        if choice == "6":
            resp = asyncio.run(cli.ask("/provider ollama llama3.2:3b")); print(resp); continue
        if choice == "7":
            resp = asyncio.run(cli.ask("/autonomy tick")); print(resp); continue
        # Fallback: treat as a chat prompt
        resp = asyncio.run(cli.ask(choice))
        print(resp)

    print("[Kai Control Panel] Exiting.")


if __name__ == "__main__":
    main()
