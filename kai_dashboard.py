#!/usr/bin/env python3
"""
KAI DASHBOARD -- Beautiful Terminal UI
======================================
Rich-based interactive dashboard for Kai AI.

Usage:
    python kai_dashboard.py
    python kai_dashboard.py --model llama3.2:3b
    python kai_dashboard.py --provider deepseek --model deepseek-chat

Controls:
    /provider <name> [model]  Switch LLM provider
    /model <name>             Change model
    /menu                     Show interactive menu
    /clear                    Clear chat history
    /help                     Show commands
    /exit                     Quit
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# Kai imports
try:
    from kai_agent.assistant import KaiAssistant
except ImportError as exc:
    print(f"Error importing KaiAssistant: {exc}")
    print("Make sure you're running from the Kai-AI directory.")
    sys.exit(1)

console = Console()

# Color palette
ACCENT = "#E8733A"
TEXT = "#F5E6D0"
TEXT_DIM = "#8B7355"
WARN = "#E8C547"
SUCCESS = "#7CB342"
ERROR = "#E53935"
INFO = "#42A5F5"
USER_COLOR = "#42A5F5"
KAI_COLOR = "#E8733A"
SYS_COLOR = "#E8C547"


def print_banner(assistant=None):
    """Print the Kai dashboard banner."""
    banner = Text()
    banner.append("    /\\_/\\  ", style=f"bold {ACCENT}")
    banner.append("KAI DASHBOARD\n", style=f"bold {TEXT}")
    banner.append("   ( o.o )  ", style=f"bold {ACCENT}")
    if assistant:
        banner.append(f"Provider: ", style=TEXT_DIM)
        banner.append(f"{assistant.client.provider}", style=f"bold {ACCENT}")
        banner.append("  Model: ", style=TEXT_DIM)
        banner.append(f"{assistant.client.model}\n", style=f"bold {WARN}")
    else:
        banner.append("\n", style=TEXT)
    banner.append("   /  >  \\\n", style=f"bold {ACCENT}")
    banner.append("  Shiba Inu Companion AI", style=TEXT_DIM)
    console.print(Panel(banner, border_style=ACCENT, padding=(1, 2)))


def print_menu(assistant):
    """Print the interactive menu."""
    grid = Table.grid(padding=(0, 4))
    grid.add_column(style=f"bold {ACCENT}")
    grid.add_column(style=TEXT)
    grid.add_column(style=TEXT_DIM)

    grid.add_row("P", "Provider", "Switch LLM provider (ollama, deepseek, hf, codex)")
    grid.add_row("M", "Model", "Change model")
    grid.add_row("C", "Clear", "Clear chat history")
    grid.add_row("H", "Help", "Show all commands")
    grid.add_row("Q", "Quit", "Exit dashboard")
    grid.add_row("", "", "")
    grid.add_row("/provider <name>", "", "Switch provider inline")
    grid.add_row("/model <name>", "", "Change model inline")
    grid.add_row("/clear", "", "Clear chat")
    grid.add_row("/memory <query>", "", "Search memory")
    grid.add_row("/mood", "", "Check Kai's mood")
    grid.add_row("/skills", "", "List skills")
    grid.add_row("/learn", "", "Learning stats")
    grid.add_row("/web", "", "Web automation")
    grid.add_row("/hardware", "", "Hardware status")
    grid.add_row("/kali", "", "Kali status")

    console.print(Panel(grid, title="[bold]Menu[/bold]", border_style=WARN, padding=(1, 2)))


def print_help():
    """Print help text."""
    help_text = Text()
    help_text.append("Chat Commands\n", style=f"bold underline {ACCENT}")
    help_text.append("/provider <name> [model]  ", style=f"bold {TEXT}")
    help_text.append("Switch LLM provider\n", style=TEXT_DIM)
    help_text.append("/model <name>             ", style=f"bold {TEXT}")
    help_text.append("Change model\n", style=TEXT_DIM)
    help_text.append("/clear                    ", style=f"bold {TEXT}")
    help_text.append("Clear conversation\n", style=TEXT_DIM)
    help_text.append("/history                  ", style=f"bold {TEXT}")
    help_text.append("Show recent history\n", style=TEXT_DIM)
    help_text.append("/exit                     ", style=f"bold {TEXT}")
    help_text.append("Quit dashboard\n\n", style=TEXT_DIM)

    help_text.append("Kai Functions\n", style=f"bold underline {ACCENT}")
    help_text.append("/memory <query>  ", style=f"bold {TEXT}")
    help_text.append("Search memory\n", style=TEXT_DIM)
    help_text.append("/mood            ", style=f"bold {TEXT}")
    help_text.append("Check emotional state\n", style=TEXT_DIM)
    help_text.append("/remember <text> ", style=f"bold {TEXT}")
    help_text.append("Add to relationship memory\n", style=TEXT_DIM)
    help_text.append("/skills          ", style=f"bold {TEXT}")
    help_text.append("List learned skills\n", style=TEXT_DIM)
    help_text.append("/learn           ", style=f"bold {TEXT}")
    help_text.append("Learning system stats\n\n", style=TEXT_DIM)

    help_text.append("Tool Commands\n", style=f"bold underline {ACCENT}")
    help_text.append("/web start        ", style=f"bold {TEXT}")
    help_text.append("Start browser\n", style=TEXT_DIM)
    help_text.append("/web goto <url>   ", style=f"bold {TEXT}")
    help_text.append("Navigate to URL\n", style=TEXT_DIM)
    help_text.append("/hardware status  ", style=f"bold {TEXT}")
    help_text.append("Hardware capabilities\n", style=TEXT_DIM)
    help_text.append("/kali status      ", style=f"bold {TEXT}")
    help_text.append("Kali integration status\n", style=TEXT_DIM)

    console.print(Panel(help_text, title="[bold]Help[/bold]", border_style=INFO, padding=(1, 2)))


def print_message(role, content, timestamp=None):
    """Print a chat message with styling."""
    if role == "user":
        prefix = Text("YOU  ", style=f"bold {USER_COLOR}")
        border = USER_COLOR
    elif role == "kai":
        prefix = Text("KAI  ", style=f"bold {KAI_COLOR}")
        border = KAI_COLOR
    else:
        prefix = Text("SYS  ", style=f"bold {SYS_COLOR}")
        border = SYS_COLOR

    if timestamp:
        prefix.append(f"{timestamp}  ", style=TEXT_DIM)

    body = Text(content, style=TEXT)

    panel_content = Text()
    panel_content.append(prefix)
    panel_content.append(body)

    console.print(Panel(panel_content, border_style=border, padding=(0, 1)))


def handle_command(cmd, assistant, messages):
    """Handle slash commands. Returns (should_continue, response_text)."""
    parts = cmd[1:].strip().split(None, 1)
    action = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if action in ("exit", "quit", "q"):
        print_message("system", "Goodbye! Kai will be here when you return.")
        return False, ""

    if action == "clear":
        messages.clear()
        console.clear()
        print_banner(assistant)
        print_message("system", "Chat history cleared.")
        return True, ""

    if action == "help":
        print_help()
        return True, ""

    if action == "menu":
        print_menu(assistant)
        return True, ""

    if action == "provider":
        if not arg:
            print_message("system", f"Current provider: {assistant.client.provider} | Model: {assistant.client.model}")
            print_message("system", "Usage: /provider <ollama|deepseek|hf|codex> [model]")
            return True, ""
        provider_parts = arg.split(None, 1)
        provider_name = provider_parts[0].lower()
        model_name = provider_parts[1] if len(provider_parts) > 1 else None
        result = assistant.client.set_provider(provider_name, model_name)
        print_message("system", f"Provider switch: {result}")
        return True, ""

    if action == "model":
        if not arg:
            print_message("system", f"Current model: {assistant.client.model}")
            print_message("system", "Usage: /model <model_name>")
            return True, ""
        result = assistant.client.set_model(arg)
        print_message("system", f"Model switch: {result}")
        return True, ""

    if action == "memory":
        if not arg:
            print_message("system", "Usage: /memory <search query>")
            return True, ""
        try:
            results = assistant.memory.search(arg)
            return True, f"Memory search for '{arg}':\n{results}"
        except Exception as exc:
            return True, f"Memory error: {exc}"

    if action == "mood":
        try:
            mood = assistant.emotions.get_summary()
            return True, f"My current state:\n{mood}"
        except Exception as exc:
            return True, f"Mood check error: {exc}"

    if action == "skills":
        try:
            skills = assistant.skills.list_skills()
            return True, f"Skills:\n{skills}"
        except Exception as exc:
            return True, f"Skills error: {exc}"

    if action == "learn":
        try:
            stats = assistant.learning.get_stats()
            return True, f"Learning stats:\n{stats}"
        except Exception as exc:
            return True, f"Learning error: {exc}"

    if action == "web":
        if not arg:
            # Show interactive web menu with actual numbered options
            console.print(Panel(
                "[bold]Web Automation Menu[/bold]\n\n"
                "[1] Start browser\n"
                "[2] Navigate to URL\n"
                "[3] Search the web\n"
                "[4] Take screenshot\n"
                "[5] Show page links\n"
                "[6] Close browser\n"
                "[7] Browser status\n"
                "[0] Back to chat",
                title="Web", border_style=INFO, padding=(1, 2)
            ))
            choice = Prompt.ask(
                "Select option",
                choices=["1", "2", "3", "4", "5", "6", "7", "0"],
                default="0",
                show_choices=False,
            )
            if choice == "1":
                try:
                    result = assistant.tools.browse("")
                    return True, f"Browser started:\n{result}"
                except Exception as exc:
                    return True, f"Browser start failed: {exc}"
            elif choice == "2":
                url = Prompt.ask("Enter URL", default="https://example.com")
                try:
                    result = assistant.tools.browse(url)
                    return True, f"Navigated to {url}:\n{result}"
                except Exception as exc:
                    return True, f"Navigation failed: {exc}"
            elif choice == "3":
                query = Prompt.ask("Search query")
                try:
                    result = assistant.tools.search_browser(query)
                    return True, f"Search results for '{query}':\n{result}"
                except Exception as exc:
                    return True, f"Search failed: {exc}"
            elif choice == "4":
                try:
                    result = assistant.tools.screenshot()
                    return True, f"Screenshot:\n{result}"
                except Exception as exc:
                    return True, f"Screenshot failed: {exc}"
            elif choice == "5":
                try:
                    result = assistant.tools.get_page_links()
                    return True, f"Page links:\n{result}"
                except Exception as exc:
                    return True, f"Links failed: {exc}"
            elif choice == "6":
                try:
                    assistant.tools.browser.close()
                    return True, "Browser closed."
                except Exception as exc:
                    return True, f"Close failed: {exc}"
            elif choice == "7":
                try:
                    result = assistant.tools.get_page_content()
                    return True, f"Browser status:\n{result}"
                except Exception as exc:
                    return True, f"Status failed: {exc}"
            return True, ""

        # Handle direct /web <subcommand> usage
        sub = arg.lower().strip()
        if sub == "start":
            try:
                result = assistant.tools.browse("")
                return True, f"Browser started:\n{result}"
            except Exception as exc:
                return True, f"Browser start failed: {exc}"
        elif sub.startswith("goto "):
            url = sub[5:].strip()
            try:
                result = assistant.tools.browse(url)
                return True, f"Navigated to {url}:\n{result}"
            except Exception as exc:
                return True, f"Navigation failed: {exc}"
        elif sub.startswith("search "):
            query = sub[7:].strip()
            try:
                result = assistant.tools.search_browser(query)
                return True, f"Search results for '{query}':\n{result}"
            except Exception as exc:
                return True, f"Search failed: {exc}"
        elif sub == "screenshot":
            try:
                result = assistant.tools.screenshot()
                return True, f"Screenshot:\n{result}"
            except Exception as exc:
                return True, f"Screenshot failed: {exc}"
        elif sub == "links":
            try:
                result = assistant.tools.get_page_links()
                return True, f"Page links:\n{result}"
            except Exception as exc:
                return True, f"Links failed: {exc}"
        elif sub == "close":
            try:
                assistant.tools.browser.close()
                return True, "Browser closed."
            except Exception as exc:
                return True, f"Close failed: {exc}"
        else:
            return True, (
                "Unknown /web command. Available:\n"
                "  /web start           -- Start browser\n"
                "  /web goto <url>      -- Navigate to URL\n"
                "  /web search <query>  -- Search the web\n"
                "  /web screenshot      -- Take screenshot\n"
                "  /web links           -- Show page links\n"
                "  /web close           -- Close browser\n"
                "  /web                 -- Interactive menu"
            )

    if action == "hardware":
        try:
            hw = assistant.hardware.get_status()
            return True, f"Hardware status:\n{hw}"
        except Exception as exc:
            return True, f"Hardware error: {exc}"

    if action == "kali":
        try:
            status = assistant.tools.kali_status()
            return True, f"Kali status:\n{status}"
        except Exception as exc:
            return True, f"Kali error: {exc}"

    print_message("system", f"Unknown command: /{action}. Type /help for available commands.")
    return True, ""


def interactive_menu(assistant, messages):
    """Show interactive menu and handle selection."""
    print_menu(assistant)
    choice = Prompt.ask(
        "Select",
        choices=["p", "m", "c", "h", "q", ""],
        default="",
        show_choices=False,
    ).lower()

    if choice == "p":
        provider = Prompt.ask("Provider (ollama/deepseek/hf/codex)", default=assistant.client.provider)
        model = Prompt.ask("Model (optional)", default="")
        result = assistant.client.set_provider(provider, model or None)
        print_message("system", f"Switched: {result}")

    elif choice == "m":
        model = Prompt.ask("Model name", default=assistant.client.model)
        result = assistant.client.set_model(model)
        print_message("system", f"Switched: {result}")

    elif choice == "c":
        messages.clear()
        console.clear()
        print_banner(assistant)
        print_message("system", "Chat history cleared.")

    elif choice == "h":
        print_help()

    elif choice == "q":
        print_message("system", "Goodbye!")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Kai Dashboard")
    parser.add_argument("--model", default=os.environ.get("KAI_MODEL", "llama3.2:3b"))
    parser.add_argument("--provider", default=None)
    parser.add_argument("--workspace", default=str(Path(".").resolve()))
    args = parser.parse_args()

    console.clear()
    print_banner()

    # Init assistant
    try:
        assistant = KaiAssistant(model=args.model, workspace=Path(args.workspace))
        if args.provider:
            assistant.client.set_provider(args.provider)
    except Exception as exc:
        console.print(Panel(
            f"Failed to initialize Kai: {exc}\n\n"
            "Some features may be limited. Check your Ollama/API setup.",
            title="Warning",
            border_style=WARN,
        ))
        assistant = None

    console.clear()
    print_banner(assistant)
    print_message("system", "Kai is ready! Type a message or /menu for options.")

    messages = []
    running = True

    while running:
        try:
            user_input = Prompt.ask(Text("YOU", style=f"bold {USER_COLOR}"))
        except (EOFError, KeyboardInterrupt):
            print_message("system", "Goodbye!")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Check for menu trigger
        if user_input.lower() == "/menu":
            running = interactive_menu(assistant, messages)
            continue

        # Check for commands
        if user_input.startswith("/"):
            running, response = handle_command(user_input, assistant, messages)
            if response:
                print_message("kai", response)
            continue

        # Regular chat
        messages.append({"role": "user", "content": user_input, "time": time.strftime("%H:%M:%S")})
        print_message("user", user_input)

        if not assistant:
            print_message("system", "Kai is not initialized. Cannot process messages.")
            continue

        # Thinking indicator
        with console.status("[bold orange3]Kai is thinking...", spinner="dots"):
            try:
                reply = asyncio.run(assistant.ask(user_input))
            except Exception as exc:
                reply = f"Sorry, I encountered an error: {exc}"

        messages.append({"role": "kai", "content": reply, "time": time.strftime("%H:%M:%S")})
        print_message("kai", reply)


if __name__ == "__main__":
    main()

