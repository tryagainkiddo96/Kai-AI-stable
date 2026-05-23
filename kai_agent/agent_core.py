"""Agent Core — Kai rebuilt as a tool-using agent, like I work.

Instead of hardcoded intent handlers, every capability is a registered Tool
with a name, description, parameter schema, and execution function.
The agent loop: reason → select tool → execute → evaluate → iterate/respond.

This mirrors how production coding agents reason about problems:
1. Understand the goal
2. Select the right tool(s)
3. Execute
4. Check result
5. If failed, re-think and try something else
6. Verify and report
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ── Tool definition ───────────────────────────────────────────────────────────

@dataclass
class Tool:
    """A single capability Kai can use, with schema for LLM selection."""
    name: str
    description: str
    parameters: dict[str, dict]  # {"param_name": {"type": "string", "description": "...", "default": None}}
    handler: Callable
    timeout: int = 60
    category: str = "general"

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                name: {k: v for k, v in schema.items() if k in ("type", "description")}
                for name, schema in self.parameters.items()
            },
            "timeout": self.timeout,
            "category": self.category,
        }


# ── Tool Registry ─────────────────────────────────────────────────────────────

class ToolRegistry:
    """Registry of all tools Kai can use. Tools are registered with schema + handler."""

    def __init__(self, kai):
        self._tools: dict[str, Tool] = {}
        self._register_all(kai)

    def _register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, category: str = "") -> list[dict]:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return [t.to_schema() for t in sorted(tools, key=lambda x: x.name)]

    def list_categories(self) -> list[str]:
        cats = set(t.category for t in self._tools.values())
        return sorted(cats)

    def _register_all(self, kai):
        # ── Web & search ──
        self._register(Tool(
            "web_search", "Search the web for real-time information",
            {"query": {"type": "string", "description": "Search query"}},
            lambda q: kai._handle_web_search(q) if q else "No query", 60, "web"
        ))
        self._register(Tool(
            "browser_open", "Open a URL in a browser (firefox, chrome, opera, edge)",
            {"url": {"type": "string", "description": "URL to open"},
             "browser": {"type": "string", "description": "Browser name", "default": "firefox"}},
            lambda url, browser="firefox": kai._handle_browser(f"open {url} in {browser}"), 30, "web"
        ))

        # ── Screen & vision ──
        self._register(Tool(
            "screen_ocr", "Read text from the screen via OCR",
            {}, lambda: kai._handle_screen("what's on my screen"), 60, "vision"
        ))
        self._register(Tool(
            "chess_analyze", "Analyze the chess board currently on screen",
            {}, lambda: kai._handle_chess("analyze this position"), 60, "vision"
        ))

        # ── Environment ──
        self._register(Tool(
            "scan_wifi", "Scan for nearby WiFi networks and their signal strength",
            {}, lambda: kai._scan_wifi(), 30, "environment"
        ))
        self._register(Tool(
            "scan_bluetooth", "List Bluetooth devices on this system",
            {}, lambda: kai._scan_bluetooth(), 30, "environment"
        ))
        self._register(Tool(
            "scan_network", "Scan LAN for connected devices, interfaces, IP addresses, and ARP table. Use this FIRST to discover other PCs before trying to connect.",
            {}, lambda: kai._scan_network(), 30, "environment"
        ))

        # ── System ──
        self._register(Tool(
            "system_info", "Get system information: CPU, memory, processes, OS",
            {"detail": {"type": "string", "description": "What to check: cpu, memory, processes, or all", "default": "all"}},
            lambda detail="all": kai._handle_execute(f"check {detail}"), 30, "system"
        ))
        self._register(Tool(
            "shell_execute", "Execute a shell command (PowerShell on Windows)",
            {"command": {"type": "string", "description": "Command to execute"}},
            lambda cmd: kai._handle_execute(cmd), 120, "system"
        ))
        self._register(Tool(
            "send_notification", "Show a desktop notification",
            {"message": {"type": "string", "description": "Notification text"}},
            lambda msg: kai._handle_execute(f"notification {msg}"), 15, "system"
        ))
        self._register(Tool(
            "launch_app", "Launch an application (notepad, calc, cmd, etc.)",
            {"app": {"type": "string", "description": "Application name"}},
            lambda app: kai._handle_execute(f"launch {app}"), 15, "system"
        ))
        self._register(Tool(
            "clipboard", "Read from or write to the clipboard",
            {"action": {"type": "string", "description": "read or write"},
             "value": {"type": "string", "description": "Text to copy (for write)", "default": ""}},
            lambda action, value="": kai._handle_execute(f"clipboard {action} {value}"), 15, "system"
        ))
        self._register(Tool(
            "calculator", "Evaluate a mathematical expression",
            {"expression": {"type": "string", "description": "Math expression to evaluate"}},
            lambda expr: kai._handle_execute(f"calculate {expr}"), 15, "system"
        ))

        # ── Memory & knowledge ──
        self._register(Tool(
            "memory_save", "Save something to long-term memory",
            {"key": {"type": "string", "description": "What to remember"}},
            lambda key: kai._handle_memory(f"remember {key}"), 15, "memory"
        ))
        self._register(Tool(
            "memory_recall", "Recall something from long-term memory",
            {"query": {"type": "string", "description": "What to remember"}},
            lambda q: kai._handle_memory(f"what did i say about {q}"), 15, "memory"
        ))
        self._register(Tool(
            "knowledge_search", "Search Kai's knowledge base for past interactions",
            {"query": {"type": "string", "description": "What to search for"}},
            lambda q: kai._kb.build_context(q) if kai._kb else "Knowledge base unavailable", 15, "memory"
        ))

        # ── Pentest ──
        self._register(Tool(
            "pentest_nmap", "Run an nmap scan against a target",
            {"target": {"type": "string", "description": "IP or hostname"}},
            lambda t: kai._handle_pentest(f"nmap {t}"), 300, "pentest"
        ))
        self._register(Tool(
            "pentest_web_recon", "Run web vulnerability recon against a URL",
            {"url": {"type": "string", "description": "Target URL"}},
            lambda u: kai._handle_pentest(f"web recon {u}"), 300, "pentest"
        ))
        self._register(Tool(
            "pentest_dir_bust", "Directory busting with gobuster",
            {"url": {"type": "string", "description": "Target URL"}},
            lambda u: kai._handle_pentest(f"dir bust {u}"), 300, "pentest"
        ))
        self._register(Tool(
            "pentest_engagement", "Create a full pentest engagement",
            {"name": {"type": "string", "description": "Engagement name"},
             "target": {"type": "string", "description": "Target IP or hostname"}},
            lambda n, t: kai._handle_pentest(f"start engagement {n} {t}"), 30, "pentest"
        ))

        # ── Ghost ──
        self._register(Tool(
            "ghost_activate", "Activate ghost mode — anonymous operations, identity rotation, trace cleaning",
            {}, lambda: kai._handle_execute("activate ghost"), 15, "stealth"
        ))
        self._register(Tool(
            "ghost_deactivate", "Deactivate ghost mode and clean traces",
            {}, lambda: kai._handle_execute("deactivate ghost"), 15, "stealth"
        ))

        # ── Remote ──
        self._register(Tool(
            "remote_scan", "Scan LAN for other computers by hostname or IP. Call with no args to discover all devices, or with a hostname/IP to check a specific target.",
            {"target": {"type": "string", "description": "Hostname or IP to scan for (leave empty to scan all)", "default": ""}},
            lambda t="": kai._handle_remote(f"scan for {t}") if t else kai._handle_remote("scan lan"), 30, "remote"
        ))
        self._register(Tool(
            "remote_connect", "Connect to a remote PC via RDP. Use a valid hostname like DESKTOP-ABC123 or IP like 192.168.1.50 from scan_network results.",
            {"target": {"type": "string", "description": "Computer hostname (e.g. DESKTOP-ABC123) or IP address (e.g. 192.168.1.50)"}},
            lambda t: kai._handle_remote(f"remote desktop to {t}"), 30, "remote"
        ))
        self._register(Tool(
            "remote_copy", "Copy a file from a remote PC using the hidden admin share. Requires a valid computer name or IP already known.",
            {"source": {"type": "string", "description": "Full UNC path like \\\\TARGET-PC\\C$\\path\\to\\file"},
             "target": {"type": "string", "description": "Computer name", "default": ""}},
            lambda s, t="": kai._handle_remote(f"copy {s} from {t}"), 60, "remote"
        ))

        # ── File System ──
        self._register(Tool(
            "read_file", "Read the contents of a file from the filesystem",
            {"path": {"type": "string", "description": "Path to the file"}},
            lambda p: kai._handle_filesystem(f"read {p}"), 30, "filesystem"
        ))
        self._register(Tool(
            "write_file", "Create or overwrite a file with text content",
            {"path": {"type": "string", "description": "File path to write"},
             "content": {"type": "string", "description": "Text content to write"}},
            lambda p, c: kai._handle_filesystem(f'write file {p} containing "{c}"'), 30, "filesystem"
        ))
        self._register(Tool(
            "edit_file", "Edit an existing file by replacing text. Use this to modify code.",
            {"path": {"type": "string", "description": "File path to edit"},
             "old_text": {"type": "string", "description": "The exact text to replace"},
             "new_text": {"type": "string", "description": "The replacement text"}},
            lambda p, o, n: kai._handle_filesystem(f'edit file {p} replace "{o}" with "{n}"'), 30, "filesystem"
        ))
        self._register(Tool(
            "glob_files", "Find files matching a glob pattern (e.g. '**/*.py' '*.txt' 'kai_agent/**/*.py')",
            {"pattern": {"type": "string", "description": "Glob pattern to search (e.g. **/*.py)"},
             "path": {"type": "string", "description": "Search path (optional)", "default": ""}},
            lambda pattern, path="": kai._handle_filesystem(f"glob {pattern} in {path}"), 30, "filesystem"
        ))
        self._register(Tool(
            "grep_files", "Search file contents for a regex pattern",
            {"pattern": {"type": "string", "description": "Regex pattern to search"},
             "path": {"type": "string", "description": "Search path (optional)", "default": ""},
             "file_pattern": {"type": "string", "description": "File name pattern (e.g. *.py), optional", "default": ""}},
            lambda pattern, path="", file_pattern="": kai._handle_filesystem(f"grep \"{pattern}\" in {path} files {file_pattern}"), 60, "filesystem"
        ))
        self._register(Tool(
            "list_files", "List files and directories in a folder",
            {"path": {"type": "string", "description": "Directory path", "default": "."}},
            lambda path=".": kai._handle_filesystem(f"list files {path}"), 15, "filesystem"
        ))

        # ── Web Fetch ──
        self._register(Tool(
            "web_fetch", "Fetch raw content from a URL. Use this to read web pages, APIs, or any URL directly.",
            {"url": {"type": "string", "description": "Full URL to fetch"}},
            lambda url: kai._handle_web_fetch(f"fetch {url}"), 30, "web"
        ))

        # ── Git ──
        self._register(Tool(
            "git_status", "Show git working tree status — staged, unstaged, untracked files",
            {}, lambda: kai._handle_git("git status"), 15, "git"
        ))
        self._register(Tool(
            "git_diff", "Show git diff (unstaged changes), or staged changes with 'staged' flag",
            {"staged": {"type": "string", "description": "Set to 'true' to show staged changes", "default": "false"}},
            lambda staged="false": kai._handle_git("git diff staged" if staged == "true" else "git diff"), 15, "git"
        ))
        self._register(Tool(
            "git_log", "Show recent git commit history",
            {"count": {"type": "string", "description": "Number of commits to show", "default": "20"}},
            lambda count="20": kai._handle_git("git log"), 15, "git"
        ))
        self._register(Tool(
            "git_branch", "List git branches",
            {}, lambda: kai._handle_git("git branch"), 15, "git"
        ))
        self._register(Tool(
            "git_commit", "Stage all changes and commit with a message",
            {"message": {"type": "string", "description": "Commit message"}},
            lambda msg: kai._handle_git(f'git commit message "{msg}"'), 30, "git"
        ))
        self._register(Tool(
            "git_diff_base", "Show changes since a base branch (for PR context)",
            {"base": {"type": "string", "description": "Base branch name (main, master, develop)", "default": "main"}},
            lambda base="main": kai._handle_git(f"git diff with {base}"), 30, "git"
        ))
        self._register(Tool(
            "git_create_pr", "Create a GitHub Pull Request from the current branch (requires gh CLI)",
            {"title": {"type": "string", "description": "PR title (optional)", "default": ""}},
            lambda title="": kai._handle_git(f"git create PR title '{title}'"), 60, "git"
        ))

        # ── HTTP Client ──
        self._register(Tool(
            "http_request", "Make an HTTP request to a REST API endpoint. Supports GET, POST, PUT, DELETE with JSON body and custom headers.",
            {"url": {"type": "string", "description": "Full URL or API endpoint"},
             "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE", "default": "GET"},
             "body": {"type": "string", "description": "JSON body for POST/PUT requests (optional)", "default": ""}},
            lambda url, method="GET", body="": kai._handle_http(f"{method} {url} with {body}" if body else f"{method} {url}"), 30, "web"
        ))

        # ── Mission ──
        self._register(Tool(
            "mission_plan", "Plan and execute a multi-step mission with verification",
            {"goal": {"type": "string", "description": "The mission goal in natural language"}},
            lambda g: kai._handle_mission(g), 300, "mission"
        ))

        # ── Package Management ──
        self._register(Tool(
            "install_package", "Install a package via pip, npm, cargo, choco, or winget",
            {"package": {"type": "string", "description": "Package name to install"},
             "manager": {"type": "string", "description": "Package manager: pip, npm, cargo, choco, winget", "default": "pip"}},
            lambda pkg, mgr="pip": kai._handle_package(f"{mgr} install {pkg}"), 120, "development"
        ))

        # ── Database ──
        self._register(Tool(
            "sql_query", "Execute a SQL query on a SQLite database",
            {"query": {"type": "string", "description": "SQL query (SELECT, INSERT, UPDATE, DELETE, CREATE)"},
             "db_path": {"type": "string", "description": "Path to SQLite database file (optional)", "default": ""}},
            lambda q, db="": kai._handle_database(f"query '{q}' on {db}" if db else f"query '{q}'"), 30, "database"
        ))
        self._register(Tool(
            "sql_tables", "List all tables in a SQLite database",
            {"db_path": {"type": "string", "description": "Path to SQLite database file (optional)", "default": ""}},
            lambda db="": kai._handle_database(f"list tables in {db}" if db else "list tables"), 15, "database"
        ))
        self._register(Tool(
            "sql_schema", "Show the schema (column definitions) of a table",
            {"table": {"type": "string", "description": "Table name"},
             "db_path": {"type": "string", "description": "Path to SQLite database file (optional)", "default": ""}},
            lambda t, db="": kai._handle_database(f"describe {t} in {db}" if db else f"describe {t}"), 15, "database"
        ))

        # ── Image Analysis ──
        self._register(Tool(
            "analyze_image", "Analyze an image file: dimensions, format, EXIF data, mode",
            {"path": {"type": "string", "description": "Path to the image file"}},
            lambda p: kai._handle_image(f"analyze image {p}"), 15, "vision"
        ))

        # ── Project Scaffolding ──
        self._register(Tool(
            "scaffold_project", "Create a new project from a template (python, node, react, html, rust, go)",
            {"name": {"type": "string", "description": "Project name"},
             "type": {"type": "string", "description": "Project type: python, node, react, html, rust, go", "default": "python"}},
            lambda n, t="python": kai._handle_scaffold(f"scaffold {n} {t} project"), 30, "development"
        ))

        # ── Shell ──
        self._register(Tool(
            "shell_run", "Run a native shell command (PowerShell on Windows, bash on Linux)",
            {"command": {"type": "string", "description": "Command to execute"}},
            lambda cmd: kai._handle_shell(f"run '{cmd}'"), 60, "shell"
        ))

        # ── Sub-agents ──
        self._register(Tool(
            "subagent_run", "Spawn parallel sub-agents to execute multiple tasks concurrently. Pass tasks as a list.",
            {"tasks": {"type": "string", "description": "Multiple tasks separated by 'and' or 'then'"}},
            lambda tasks: kai._handle_subagent(tasks), 120, "system"
        ))

        # ── Task persistence ──
        self._register(Tool(
            "task_start", "Start a long-running background task",
            {"task": {"type": "string", "description": "What to run in the background"}},
            lambda t: kai._handle_task(f"start {t}"), 15, "system"
        ))
        self._register(Tool(
            "task_list", "List all background tasks and their status",
            {}, lambda: kai._handle_task("list tasks"), 15, "system"
        ))
        self._register(Tool(
            "task_status", "Check the status of a specific task",
            {"task_id": {"type": "string", "description": "Task number to check"}},
            lambda tid: kai._handle_task(f"check task {tid}"), 15, "system"
        ))

        # ── Docker ──
        self._register(Tool(
            "docker_ps", "List Docker containers (all or running only)",
            {"all": {"type": "string", "description": "Set to 'true' to show all containers, 'false' for running only", "default": "true"}},
            lambda all="true": kai._handle_docker("docker ps" if all == "true" else "docker running"), 15, "docker"
        ))
        self._register(Tool(
            "docker_images", "List Docker images",
            {}, lambda: kai._handle_docker("docker images"), 15, "docker"
        ))
        self._register(Tool(
            "docker_pull", "Pull a Docker image from a registry",
            {"image": {"type": "string", "description": "Image name to pull (e.g. nginx, python:3.11)"}},
            lambda img: kai._handle_docker(f"docker pull {img}"), 120, "docker"
        ))
        self._register(Tool(
            "docker_run", "Run a Docker container",
            {"image": {"type": "string", "description": "Image name"},
             "name": {"type": "string", "description": "Container name (optional)", "default": ""},
             "ports": {"type": "string", "description": "Port mapping like 8080:80 (optional)", "default": ""}},
            lambda img, name="", ports="": kai._handle_docker(f"docker run {img} as {name} port {ports}".replace("  as ", "").replace(" port ", "")), 60, "docker"
        ))
        self._register(Tool(
            "docker_stop", "Stop a running Docker container",
            {"container": {"type": "string", "description": "Container ID or name"}},
            lambda c: kai._handle_docker(f"docker stop {c}"), 30, "docker"
        ))
        self._register(Tool(
            "docker_exec", "Execute a command inside a running Docker container",
            {"container": {"type": "string", "description": "Container ID or name"},
             "command": {"type": "string", "description": "Command to run"}},
            lambda c, cmd: kai._handle_docker(f"docker exec {c} {cmd}"), 30, "docker"
        ))
        self._register(Tool(
            "docker_compose", "Manage Docker Compose stack (up, down, ps)",
            {"action": {"type": "string", "description": "Action: up, down, ps", "default": "ps"}},
            lambda action="ps": kai._handle_docker(f"docker compose {action}"), 120, "docker"
        ))

        # ── Calculate ──
        self._register(Tool(
            "calculate", "Evaluate a math expression (e.g. 5 + 5, 2^10, 15% of 200)",
            {"expression": {"type": "string", "description": "Math expression to evaluate"}},
            lambda e: kai._handle_calculate(e), 15, "system"
        ))

        # ── Forex / Finance ──
        self._register(Tool(
            "forex_data", "Fetch live forex exchange rates. Use 'all' for all pairs or a specific pair like EUR/USD, GBP/JPY.",
            {"pairs": {"type": "string", "description": "Comma-separated pairs (e.g. EUR/USD,GBP/USD) or 'all' for all available", "default": "all"}},
            lambda pairs="all": kai._handle_forex(pairs), 30, "finance"
        ))

        # ── SMS / Communication ──
        self._register(Tool(
            "send_sms", "Send an SMS text message to a phone number using email-to-carrier gateway or ADB phone. Use this to send texts.",
            {"number": {"type": "string", "description": "Phone number (e.g. 5551234567)"},
             "message": {"type": "string", "description": "Text message content"}},
            lambda num, msg: kai._handle_sms(num, msg), 30, "communication"
        ))

        # ── ADB Phone Control ──
        self._register(Tool(
            "adb_connect", "Connect to an Android phone over WiFi via ADB. Requires phone IP and debugging enabled. Returns connection status.",
            {"ip": {"type": "string", "description": "Phone IP address on WiFi network (e.g. 192.168.1.100)"}},
            lambda ip: kai._handle_adb({"action": "connect", "ip": ip}), 30, "phone"
        ))
        self._register(Tool(
            "adb_sms", "Send an SMS through a connected ADB phone. Must call adb_connect first.",
            {"number": {"type": "string", "description": "Phone number"},
             "message": {"type": "string", "description": "Message text"}},
            lambda num, msg: kai._handle_adb({"action": "sms", "number": num, "message": msg}), 30, "phone"
        ))
        self._register(Tool(
            "adb_screencap", "Capture the connected phone's screen as a PNG and return OCR text. Use this to see what's on the phone.",
            {}, lambda: kai._handle_adb({"action": "screencap"}), 30, "phone"
        ))
        self._register(Tool(
            "adb_tap", "Tap at x,y coordinates on the connected ADB phone screen. Use after screencap + OCR to interact.",
            {"x": {"type": "string", "description": "X coordinate to tap"},
             "y": {"type": "string", "description": "Y coordinate to tap"}},
            lambda x, y: kai._handle_adb({"action": "tap", "x": int(x), "y": int(y)}), 15, "phone"
        ))
        self._register(Tool(
            "adb_type", "Type text on the connected ADB phone. Use to fill forms, compose messages, etc.",
            {"text": {"type": "string", "description": "Text to type"}},
            lambda text: kai._handle_adb({"action": "type", "text": text}), 15, "phone"
        ))

        # ── Screen Automation ──
        self._register(Tool(
            "screenshot", "Take a screenshot of this computer and extract visible text via OCR. Use this to see what's on screen.",
            {}, lambda: kai._handle_screen("what's on my screen"), 30, "vision"
        ))
        self._register(Tool(
            "grid_click", "Click at a percentage-based position on the screen (e.g. 50,50 is center). Use after screenshot to interact with UI elements.",
            {"x_pct": {"type": "string", "description": "X position as percentage of screen width (0-100)"},
             "y_pct": {"type": "string", "description": "Y position as percentage of screen height (0-100)"}},
            lambda x_pct, y_pct: kai._handle_grid_click(float(x_pct), float(y_pct)), 15, "vision"
        ))
        self._register(Tool(
            "type_text", "Type text using the keyboard on this computer. Use after grid_click to fill fields.",
            {"text": {"type": "string", "description": "Text to type"}},
            lambda text: kai._handle_type_text(text), 15, "vision"
        ))
        self._register(Tool(
            "wait", "Wait/pause for a number of seconds. Use between UI automation steps to let apps load.",
            {"seconds": {"type": "string", "description": "Seconds to wait (e.g. 2 or 0.5)"}},
            lambda seconds: kai._handle_wait(float(seconds)), 30, "system"
        ))

        # ── App Install ──
        self._register(Tool(
            "install_app", "Download and install an application via winget, choco, or direct download.",
            {"app_name": {"type": "string", "description": "Name of the app to install (e.g. discord, textnow, firefox)"}},
            lambda app_name: kai._handle_install_app(app_name), 120, "system"
        ))


# ── Agent Loop ────────────────────────────────────────────────────────────────

class AgentLoop:
    """Reasoning loop that selects tools, executes them, and self-corrects.

    How it works:
    1. LLM receives: user goal + list of available tools (name + description + parameters)
    2. LLM decides: which tool to call, with what parameters
    3. Tool executes → result goes back to LLM
    4. LLM evaluates result: goal achieved? → respond. Failed? → re-think and try again.
    5. Max 5 iterations to prevent infinite loops.
    """

    MAX_ITERATIONS = 10

    def __init__(self, registry: ToolRegistry, chat_fn: Callable):
        self.registry = registry
        self._chat = chat_fn

    def run(self, goal: str) -> str:
        """Execute goal through the tool-using agent loop."""
        tools = self.registry.list_tools()
        tools_str = json.dumps(tools, indent=2)

        history = [f"Goal: {goal}"]
        system_prompt = f"""You are Kai's autonomous reasoning engine. You have access to real tools that affect this computer and the internet.

CORE RULES:
1. You MUST use tools to accomplish real tasks — do NOT just talk about what you would do, actually DO it.
2. If the user asks for data (forex, stocks, news, etc.), fetch it live — don't guess.
3. If the user asks you to DO something (send a text, install an app, read a file, etc.), use the appropriate tool.
4. After each tool call, check the result. If it failed, try a different tool or approach.
5. Only respond to the user when the goal is fully completed.

TOOL FORMAT:
TOOL: tool_name
PARAMS: {{"param1": "value1", "param2": "value2"}}

After receiving the tool result, either:
- Call another tool (continue working)
- Respond directly to the user with the final result

You have up to {self.MAX_ITERATIONS} iterations. Be thorough but efficient.

Available tools:
{tools_str}"""

        iteration = 0
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            context = "\n".join(history[-6:])
            prompt = f"{system_prompt}\n\nHistory:\n{context}\n\nWhat do you do next?"

            response = self._chat(prompt, goal)

            # Check if LLM wants to use a tool
            tool_match = re.search(r'TOOL:\s*(\w+)', response)
            params_match = re.search(r'PARAMS:\s*(\{.*?\})', response, re.DOTALL)

            if tool_match:
                tool_name = tool_match.group(1)
                params = {}
                if params_match:
                    try:
                        params = json.loads(params_match.group(1))
                    except:
                        params = {}
                tool = self.registry.get(tool_name)
                if not tool:
                    history.append(f"TOOL: {tool_name} → ERROR: Unknown tool")
                    continue
                try:
                    result = tool.handler(**params)
                    result_str = str(result)[:1500]
                    history.append(f"TOOL: {tool_name}({json.dumps(params)}) → OK")
                    history.append(f"RESULT: {result_str}")
                except Exception as e:
                    err_str = str(e)[:1500]
                    history.append(f"TOOL: {tool_name}({json.dumps(params)}) → FAILED: {err_str}")
                    history.append(f"RETRY: Try a different approach or tool")
            else:
                # LLM responded directly — this is the final answer
                return response

        return f"I tried {self.MAX_ITERATIONS} approaches but couldn't fully resolve this. Here's what I found:\n" + "\n".join(history[-4:])
