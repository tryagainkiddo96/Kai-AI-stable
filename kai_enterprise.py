#!/usr/bin/env python3
"""
KAI ENTERPRISE - Production-Grade AI Assistant
Multi-LLM, plugins, vector memory, project management, monitoring
"""

import json
import os
import sys
import subprocess
import importlib
import logging
from pathlib import Path
from datetime import datetime
from urllib import error, request
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import sqlite3
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger("KAI-ENTERPRISE")


# ============================================================================
# LLM Provider Abstraction
# ============================================================================

class LLMProvider(ABC):
    """Base LLM provider interface"""
    
    @abstractmethod
    def chat(self, messages: List[Dict]) -> str:
        pass


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, host: str | None = None, model: str | None = None):
        self.base_url = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "sam860/dolphin3-llama3.2:3b")
        self.timeout = int(os.getenv("KAI_ENTERPRISE_OLLAMA_TIMEOUT", "45"))
    
    def chat(self, messages: List[Dict]) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
        }).encode("utf-8")
        
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        try:
            with request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
                return data.get("message", {}).get("content", "").strip()
        except error.URLError as e:
            return f"ERROR: Ollama unavailable: {e.reason}"
        except Exception as e:
            return f"ERROR: {e}"


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4")
        self.base_url = "https://api.openai.com/v1"
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
    
    def chat(self, messages: List[Dict]) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
        }).encode("utf-8")
        
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST",
        )
        
        try:
            with request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"ERROR: OpenAI error: {e}"


# ============================================================================
# Plugin System
# ============================================================================

class PluginInterface(ABC):
    """Base plugin interface"""
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        pass


class TerminalPlugin(PluginInterface):
    """Execute shell commands"""
    
    def execute(self, command: str, timeout: int = 60, **kwargs) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (result.stdout or result.stderr or "(no output)")[:2000]
        except subprocess.TimeoutExpired:
            return f"[ERROR] Command timed out after {timeout}s"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def get_name(self) -> str:
        return "terminal"
    
    def get_description(self) -> str:
        return "Execute shell commands and return output"


class FilePlugin(PluginInterface):
    """File operations"""
    
    def execute(self, operation: str, path: str, content: str = None, **kwargs) -> str:
        try:
            p = Path(path).expanduser()
            
            if operation == "read":
                if not p.exists():
                    return f"[ERROR] File not found: {path}"
                text = p.read_text()
                return f"[{len(text)} chars]\n{text[:3000]}"
            
            elif operation == "write":
                if not content:
                    return "[ERROR] No content provided"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                return f"[OK] Wrote {len(content)} chars to {path}"
            
            elif operation == "list":
                if not p.exists():
                    return f"[ERROR] Path not found: {path}"
                items = sorted(p.iterdir())
                return "\n".join([f"  {'[DIR]' if i.is_dir() else '[FILE]'} {i.name}" for i in items[:50]])
            
            else:
                return "[ERROR] Unknown operation"
        
        except Exception as e:
            return f"[ERROR] {e}"
    
    def get_name(self) -> str:
        return "file"
    
    def get_description(self) -> str:
        return "Read, write, and list files"


class PluginManager:
    """Manages plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """Register built-in plugins"""
        self.register("terminal", TerminalPlugin())
        self.register("file", FilePlugin())
    
    def register(self, name: str, plugin: PluginInterface):
        """Register a plugin"""
        self.plugins[name] = plugin
        logger.info(f"Registered plugin: {name}")
    
    def execute(self, plugin_name: str, **kwargs) -> str:
        """Execute a plugin"""
        if plugin_name not in self.plugins:
            return f"[ERROR] Plugin not found: {plugin_name}"
        
        try:
            return self.plugins[plugin_name].execute(**kwargs)
        except Exception as e:
            return f"[ERROR] Plugin execution failed: {e}"
    
    def list_plugins(self) -> str:
        """List all available plugins"""
        if not self.plugins:
            return "No plugins registered"
        
        lines = ["Available Plugins:"]
        for name, plugin in self.plugins.items():
            lines.append(f"  - {name}: {plugin.get_description()}")
        return "\n".join(lines)


# ============================================================================
# Vector Memory (SQLite-based)
# ============================================================================

class VectorMemory:
    """Simple vector memory using SQLite"""
    
    def __init__(self, db_path: str = ".kai/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    category TEXT,
                    content TEXT,
                    tags TEXT
                )
            """)
            conn.commit()
    
    def store(self, content: str, category: str = "general", tags: str = ""):
        """Store a memory"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (timestamp, category, content, tags) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), category, content, tags)
            )
            conn.commit()
        logger.info(f"Stored memory: {category}")
    
    def search(self, query: str, category: str = None, limit: int = 5) -> str:
        """Search memories"""
        with sqlite3.connect(self.db_path) as conn:
            sql = "SELECT content FROM memories WHERE content LIKE ?"
            params = [f"%{query}%"]
            
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            
            if not rows:
                return f"No memories found for: {query}"
            
            return "\n---\n".join([row[0] for row in rows])


# ============================================================================
# Project Manager
# ============================================================================

class ProjectManager:
    """Manage projects and contexts"""
    
    def __init__(self, base_dir: str = ".kai/projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_project = None
    
    def create_project(self, name: str) -> str:
        """Create a new project"""
        proj_dir = self.base_dir / name
        proj_dir.mkdir(exist_ok=True)
        
        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "files": [],
            "notes": []
        }
        
        config_file = proj_dir / "config.json"
        config_file.write_text(json.dumps(config, indent=2))
        
        self.current_project = name
        logger.info(f"Created project: {name}")
        return f"Project '{name}' created"
    
    def list_projects(self) -> str:
        """List all projects"""
        projects = list(self.base_dir.glob("*/config.json"))
        if not projects:
            return "No projects"
        return "\n".join([p.parent.name for p in projects])
    
    def switch_project(self, name: str) -> str:
        """Switch to a project"""
        proj_dir = self.base_dir / name
        if not proj_dir.exists():
            return f"Project not found: {name}"
        self.current_project = name
        return f"Switched to project: {name}"


# ============================================================================
# Main Kai Enterprise
# ============================================================================

class KaiEnterprise:
    """Enterprise-grade Kai assistant"""

    def __init__(self, llm_provider: str | None = None):
        logger.info("Initializing Kai Enterprise")
        
        # Initialize components
        self.plugin_manager = PluginManager()
        self.memory = VectorMemory()
        self.project_manager = ProjectManager()
        self.history: List[Dict] = []
        
        # Initialize LLM provider
        provider_name = (llm_provider or os.getenv("KAI_LLM_PROVIDER", "ollama")).lower()

        if provider_name == "openai":
            self.llm = OpenAIProvider()
        else:
            self.llm = OllamaProvider()
        
        # System prompt
        self.system_prompt = """You are Kai Enterprise, an advanced AI assistant.

Capabilities:
- Answer technical questions accurately
- Help with code, debugging, and architecture
- Manage projects and organize information
- Use available plugins for complex tasks
- Remember and learn from conversations
- Be direct, honest, and concise

When the user asks to use a tool/plugin, tell them to use:
  /plugin <name> <args>

Available plugins: terminal, file"""

    def _fast_local_reply(self, user_input: str) -> str:
        lowered = user_input.strip().lower()

        if any(token in lowered for token in ("hi", "hello", "hey")):
            return "Kai Enterprise is here."

        if any(token in lowered for token in ("who are you", "what are you")):
            return "I'm Kai Enterprise: the API/server runtime for Kai with plugins, memory, projects, and local LLM support."

        if any(token in lowered for token in ("help", "what can you do", "capabilities")):
            return "Core live paths: chat, plugins, memory search/store, project management, history, and WebSocket chat."

        if any(token in lowered for token in ("status", "health", "are you up", "are you working")):
            return (
                f"Kai Enterprise is up. Provider: {self.llm.__class__.__name__}. "
                f"Plugins: {', '.join(sorted(self.plugin_manager.plugins.keys()))}."
            )

        if "plugin" in lowered or lowered == "/plugins":
            return self.plugin_manager.list_plugins()

        if "project" in lowered and lowered != "/projects":
            return f"Current project: {self.project_manager.current_project or 'none'}."

        return ""
    
    def ask(self, user_input: str) -> str:
        """Ask a question"""
        command_result = self.process_command(user_input)
        if command_result:
            return command_result

        local_reply = self._fast_local_reply(user_input)
        if local_reply:
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": local_reply})
            return local_reply

        self.history.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": self.system_prompt}] + self.history[-15:]
        
        response = self.llm.chat(messages)
        if response.startswith("ERROR:"):
            response = f"Kai Enterprise hit a local model issue: {response[6:].strip()}"
        self.history.append({"role": "assistant", "content": response})
        
        return response

    def ask_stateless(self, user_input: str) -> str:
        """API-safe ask path that avoids mutating shared conversation history."""
        command_result = self.process_command(user_input)
        if command_result:
            return command_result

        local_reply = self._fast_local_reply(user_input)
        if local_reply:
            return local_reply

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        response = self.llm.chat(messages)
        if response.startswith("ERROR:"):
            response = f"Kai Enterprise hit a local model issue: {response[6:].strip()}"
        return response
    
    def process_command(self, user_input: str) -> str:
        """Process special commands"""
        if user_input.startswith("/plugin "):
            parts = user_input[8:].split(maxsplit=1)
            if not parts:
                return "Usage: /plugin <name> [args]"
            plugin_name = parts[0]
            args_str = parts[1] if len(parts) > 1 else ""
            
            # Simple arg parsing (name=value pairs)
            kwargs = {}
            for pair in args_str.split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
            
            return self.plugin_manager.execute(plugin_name, **kwargs)
        
        elif user_input == "/plugins":
            return self.plugin_manager.list_plugins()
        
        elif user_input == "/projects":
            return self.project_manager.list_projects()
        
        elif user_input.startswith("/project "):
            name = user_input[9:].strip()
            return self.project_manager.create_project(name)
        
        elif user_input.startswith("/memory "):
            query = user_input[8:].strip()
            return self.memory.search(query)
        
        elif user_input == "/history":
            lines = ["Recent history:"]
            for msg in self.history[-10:]:
                role = msg["role"].upper()
                content = msg["content"][:100]
                lines.append(f"[{role}] {content}...")
            return "\n".join(lines)
        
        elif user_input == "/clear":
            self.history = []
            return "History cleared"
        
        elif user_input.startswith("/save "):
            content = user_input[6:].strip()
            self.memory.store(content)
            return "Saved to memory"
        
        return None


def main():
    """Main REPL"""
    kai = KaiEnterprise()
    
    print("\n" + "="*70)
    print("  KAI ENTERPRISE - Production-Grade AI Assistant")
    print("="*70)
    print("\n  Multi-LLM | Plugins | Vector Memory | Project Management")
    print("  Type /help for commands\n")
    
    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKai: Goodbye!")
            break
        
        if not user_input:
            continue
        
        if user_input == "/help":
            print("""
Commands:
  /plugin <name> [args]     Execute a plugin
  /plugins                  List available plugins
  /projects                 List projects
  /project <name>           Create/switch project
  /memory <query>           Search memory
  /save <content>           Save to memory
  /history                  Show recent history
  /clear                    Clear conversation
  /exit                     Exit
  
Or just ask a question!
            """)
            continue
        
        if user_input == "/exit":
            break
        
        # Try special commands first
        result = kai.process_command(user_input)
        if result:
            print(f"Kai: {result}\n")
            continue
        
        # Otherwise, ask the LLM
        print("Kai: ", end="", flush=True)
        response = kai.ask(user_input)
        print(response + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
