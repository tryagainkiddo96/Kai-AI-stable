"""
Kai LSP Client — Protocol-level integration with Language Servers.
Provides IDE-grade code intelligence: go-to-definition, find-references, rename, diagnostics, symbol search.
Supports Python (pyright), JS/TS (typescript-language-server), Rust (rust-analyzer), Go (gopls).
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class Location:
    """A position in a source file."""
    uri: str
    line: int  # 0-indexed
    character: int  # 0-indexed
    file_path: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file_path or Path(self.uri).name if "file://" in self.uri else self.uri,
            "line": self.line + 1,  # Convert to 1-indexed for display
            "column": self.character + 1,
        }


@dataclass
class Symbol:
    """A code symbol (function, class, variable, etc.)."""
    name: str
    kind: str
    location: Location
    detail: str = ""
    range_start: Location = None
    range_end: Location = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "location": self.location.to_dict() if self.location else {},
            "detail": self.detail,
        }


@dataclass
class Diagnostic:
    """A diagnostic issue (error, warning, info)."""
    severity: str  # error, warning, info, hint
    message: str
    line: int
    character: int
    end_line: int
    end_character: int
    source: str = ""
    code: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "message": self.message,
            "line": self.line + 1,
            "column": self.character + 1,
            "source": self.source,
            "code": self.code,
        }


# Language server configurations
LANGUAGE_SERVERS = {
    "python": {
        "command": ["pyright-langserver", "--stdio"],
        "fallback_command": ["pylsp", "--stdio"],
        "file_extensions": [".py"],
        "root_markers": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"],
    },
    "javascript": {
        "command": ["typescript-language-server", "--stdio"],
        "fallback_command": [],
        "file_extensions": [".js", ".jsx"],
        "root_markers": ["package.json", "tsconfig.json"],
    },
    "typescript": {
        "command": ["typescript-language-server", "--stdio"],
        "fallback_command": [],
        "file_extensions": [".ts", ".tsx"],
        "root_markers": ["package.json", "tsconfig.json"],
    },
    "rust": {
        "command": ["rust-analyzer"],
        "fallback_command": [],
        "file_extensions": [".rs"],
        "root_markers": ["Cargo.toml"],
    },
    "go": {
        "command": ["gopls"],
        "fallback_command": [],
        "file_extensions": [".go"],
        "root_markers": ["go.mod"],
    },
}

# LSP Symbol Kind mapping
SYMBOL_KINDS = {
    1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class",
    6: "Method", 7: "Property", 8: "Field", 9: "Constructor", 10: "Enum",
    11: "Interface", 12: "Function", 13: "Variable", 14: "Constant",
    15: "String", 16: "Number", 17: "Boolean", 18: "Array", 19: "Object",
    20: "Key", 21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
    25: "Operator", 26: "TypeParameter",
}

# LSP Diagnostic Severity mapping
DIAG_SEVERITY = {1: "error", 2: "warning", 3: "info", 4: "hint"}


class LSPClient:
    """A single LSP client connected to one language server."""

    def __init__(self, language: str, root_path: str) -> None:
        self.language = language
        self.root_path = str(Path(root_path).resolve())
        self.root_uri = f"file://{self.root_path}"
        self.server_config = LANGUAGE_SERVERS.get(language, {})
        self.process: subprocess.Popen | None = None
        self.request_id = 0
        self._lock = threading.Lock()
        self._initialized = False
        self._response_handlers: dict[int, threading.Event] = {}
        self._responses: dict[int, dict] = {}
        self._diagnostics: dict[str, list[Diagnostic]] = {}
        self._reader_thread: threading.Thread | None = None
        self._running = False

        # LSP capabilities (populated after initialize)
        self.capabilities: dict = {}

    def start(self) -> bool:
        """Start the language server process."""
        cmd = self.server_config.get("command", [])
        fallback = self.server_config.get("fallback_command", [])

        # Try primary command
        if not self._try_start(cmd):
            if fallback:
                if not self._try_start(fallback):
                    return False
            else:
                return False

        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # Send initialize request
        result = self._send_request("initialize", self._init_params())
        if result and "capabilities" in result:
            self.capabilities = result["capabilities"]
            self._initialized = True
            self._send_notification("initialized", {})
            return True

        return False

    def _try_start(self, cmd: list[str]) -> bool:
        """Try to start a language server with given command."""
        try:
            # Check if first command exists
            if not self._command_exists(cmd[0]):
                return False

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.root_path,
            )
            return True
        except (FileNotFoundError, OSError):
            return False

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command is available on PATH."""
        try:
            if os.name == "nt":
                subprocess.run(["where", cmd], capture_output=True, check=True)
            else:
                subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def stop(self) -> None:
        """Shutdown the language server."""
        if self._initialized:
            try:
                self._send_request("shutdown", {})
                self._send_notification("exit", {})
            except Exception:
                pass

        self._running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def _init_params(self) -> dict:
        """Build initialize request parameters."""
        return {
            "processId": os.getpid(),
            "clientInfo": {"name": "Kai", "version": "1.0"},
            "rootUri": self.root_uri,
            "rootPath": self.root_path,
            "capabilities": {
                "textDocument": {
                    "synchronization": {"didSave": True, "didChange": True},
                    "completion": {"completionItem": {"snippetSupport": False}},
                    "definition": {"linkSupport": True},
                    "references": {},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "rename": {"prepareSupport": True},
                    "diagnostics": {"relatedInformation": True},
                    "hover": {"contentFormat": ["plaintext"]},
                    "signatureHelp": {"signatureInformation": {"documentationFormat": ["plaintext"]}},
                },
                "workspace": {
                    "workspaceFolders": True,
                    "didChangeConfiguration": {},
                },
            },
            "workspaceFolders": [{"uri": self.root_uri, "name": Path(self.root_path).name}],
            "initializationOptions": {},
        }

    def _send_request(self, method: str, params: dict) -> dict | None:
        """Send an LSP request and wait for response."""
        with self._lock:
            self.request_id += 1
            req_id = self.request_id

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

        event = threading.Event()
        self._response_handlers[req_id] = event

        self._write_message(request)

        # Wait for response (timeout 30s)
        if event.wait(timeout=30):
            response = self._responses.pop(req_id, None)
            self._response_handlers.pop(req_id, None)
            if response and "result" in response:
                return response["result"]
            elif response and "error" in response:
                return None
        return None

    def _send_notification(self, method: str, params: dict) -> None:
        """Send an LSP notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self._write_message(notification)

    def _write_message(self, message: dict) -> None:
        """Write a JSON-RPC message to the server's stdin."""
        if not self.process or not self.process.stdin:
            return

        body = json.dumps(message, ensure_ascii=False)
        content = body.encode("utf-8")
        header = f"Content-Length: {len(content)}\r\n\r\n"

        try:
            self.process.stdin.write(header.encode("utf-8"))
            self.process.stdin.write(content)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def _read_loop(self) -> None:
        """Read responses from the server's stdout."""
        if not self.process or not self.process.stdout:
            return

        buffer = b""
        while self._running:
            try:
                chunk = self.process.stdout.read(4096)
                if not chunk:
                    break
                buffer += chunk

                # Process complete messages
                while b"\r\n\r\n" in buffer:
                    header_end = buffer.index(b"\r\n\r\n")
                    header_part = buffer[:header_end].decode("utf-8", errors="replace")

                    # Parse Content-Length
                    content_length = 0
                    for line in header_part.split("\r\n"):
                        if line.startswith("Content-Length:"):
                            content_length = int(line.split(":")[1].strip())
                            break

                    message_start = header_end + 4
                    if len(buffer) < message_start + content_length:
                        break  # Wait for more data

                    body = buffer[message_start:message_start + content_length]
                    buffer = buffer[message_start + content_length:]

                    try:
                        response = json.loads(body.decode("utf-8"))
                        self._handle_response(response)
                    except json.JSONDecodeError:
                        pass

            except (ValueError, OSError):
                break

    def _handle_response(self, response: dict) -> None:
        """Handle an incoming JSON-RPC message."""
        if "id" in response:
            req_id = response["id"]
            self._responses[req_id] = response
            event = self._response_handlers.get(req_id)
            if event:
                event.set()
        elif response.get("method") == "textDocument/publishDiagnostics":
            self._handle_diagnostics(response.get("params", {}))

    def _handle_diagnostics(self, params: dict) -> None:
        """Handle diagnostic notifications."""
        uri = params.get("uri", "")
        diagnostics = []
        for d in params.get("diagnostics", []):
            range_data = d.get("range", {})
            diag = Diagnostic(
                severity=DIAG_SEVERITY.get(d.get("severity", 0), "info"),
                message=d.get("message", ""),
                line=range_data.get("start", {}).get("line", 0),
                character=range_data.get("start", {}).get("character", 0),
                end_line=range_data.get("end", {}).get("line", 0),
                end_character=range_data.get("end", {}).get("character", 0),
                source=d.get("source", ""),
                code=str(d.get("code", "")),
            )
            diagnostics.append(diag)
        self._diagnostics[uri] = diagnostics

    # === LSP METHODS ===

    def open_file(self, file_path: str) -> None:
        """Notify the server that a file is opened."""
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception:
            content = ""

        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": self.language,
                "version": 1,
                "text": content,
            }
        })

    def close_file(self, file_path: str) -> None:
        """Notify the server that a file is closed."""
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"
        self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })

    def go_to_definition(self, file_path: str, line: int, column: int) -> list[Location]:
        """Go to definition of symbol at position."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": column - 1},  # Convert to 0-indexed
        })

        return self._parse_locations(result)

    def find_references(self, file_path: str, line: int, column: int) -> list[Location]:
        """Find all references to symbol at position."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": column - 1},
            "context": {"includeDeclaration": True},
        })

        return self._parse_locations(result)

    def get_symbols(self, file_path: str) -> list[Symbol]:
        """Get all symbols in a document."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri},
        })

        return self._parse_symbols(result, file_path)

    def get_workspace_symbols(self, query: str) -> list[Symbol]:
        """Search for symbols across the entire workspace."""
        result = self._send_request("workspace/symbol", {
            "query": query,
        })

        return self._parse_workspace_symbols(result)

    def rename(self, file_path: str, line: int, column: int, new_name: str) -> dict:
        """Rename symbol at position."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/rename", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": column - 1},
            "newName": new_name,
        })

        return self._parse_workspace_edit(result)

    def get_hover(self, file_path: str, line: int, column: int) -> dict:
        """Get hover information for symbol at position."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": column - 1},
        })

        if not result:
            return {}

        contents = result.get("contents", {})
        if isinstance(contents, dict):
            text = contents.get("value", "")
        elif isinstance(contents, list):
            text = " ".join(str(c) for c in contents)
        else:
            text = str(contents)

        return {
            "content": text[:2000],
            "range": result.get("range"),
        }

    def get_diagnostics(self, file_path: str) -> list[Diagnostic]:
        """Get diagnostics for a file."""
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"
        return self._diagnostics.get(uri, [])

    def get_completions(self, file_path: str, line: int, column: int) -> list[dict]:
        """Get code completions at position."""
        self.open_file(file_path)
        path = str(Path(file_path).resolve())
        uri = f"file://{path}"

        result = self._send_request("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": column - 1},
            "context": {"triggerKind": 1},
        })

        if not result:
            return []

        items = result if isinstance(result, list) else result.get("items", [])
        completions = []
        for item in items[:50]:  # Limit to 50
            completions.append({
                "label": item.get("label", ""),
                "kind": SYMBOL_KINDS.get(item.get("kind", 0), "Unknown"),
                "detail": item.get("detail", ""),
                "documentation": item.get("documentation", ""),
            })
        return completions

    # === PARSERS ===

    def _parse_locations(self, result: Any) -> list[Location]:
        """Parse LSP location result."""
        locations = []
        if not result:
            return locations

        if isinstance(result, dict):
            result = [result]
        elif not isinstance(result, list):
            return locations

        for loc in result:
            # Handle LocationLink format
            if "targetUri" in loc:
                uri = loc.get("targetUri", "")
                range_data = loc.get("targetRange", loc.get("targetSelectionRange", {}))
            else:
                uri = loc.get("uri", "")
                range_data = loc.get("range", {})

            start = range_data.get("start", {})
            file_path = uri.replace("file://", "")

            locations.append(Location(
                uri=uri,
                line=start.get("line", 0),
                character=start.get("character", 0),
                file_path=file_path,
            ))
        return locations

    def _parse_symbols(self, result: Any, default_file: str) -> list[Symbol]:
        """Parse document symbols."""
        symbols = []
        if not result:
            return symbols

        def _process(sym_data: dict, parent: str = ""):
            name = sym_data.get("name", "")
            kind = SYMBOL_KINDS.get(sym_data.get("kind", 0), "Unknown")
            detail = sym_data.get("detail", "")
            range_data = sym_data.get("range", sym_data.get("location", {}).get("range", {}))
            start = range_data.get("start", {})

            full_name = f"{parent}.{name}" if parent else name

            symbols.append(Symbol(
                name=full_name,
                kind=kind,
                detail=detail,
                location=Location(
                    uri=f"file://{default_file}",
                    line=start.get("line", 0),
                    character=start.get("character", 0),
                    file_path=default_file,
                ),
            ))

            # Process children
            for child in sym_data.get("children", []):
                _process(child, full_name)

        for item in result:
            _process(item)

        return symbols

    def _parse_workspace_symbols(self, result: Any) -> list[Symbol]:
        """Parse workspace symbols."""
        symbols = []
        if not result:
            return symbols

        for item in result[:100]:
            name = item.get("name", "")
            kind = SYMBOL_KINDS.get(item.get("kind", 0), "Unknown")
            container = item.get("containerName", "")
            location_data = item.get("location", {})
            uri = location_data.get("uri", "")
            range_data = location_data.get("range", {})
            start = range_data.get("start", {})
            file_path = uri.replace("file://", "")

            full_name = f"{container}.{name}" if container else name

            symbols.append(Symbol(
                name=full_name,
                kind=kind,
                detail=container,
                location=Location(
                    uri=uri,
                    line=start.get("line", 0),
                    character=start.get("character", 0),
                    file_path=file_path,
                ),
            ))

        return symbols

    def _parse_workspace_edit(self, result: Any) -> dict:
        """Parse workspace edit (for rename)."""
        if not result:
            return {"changes": [], "documentChanges": []}

        changes = []
        for uri, edits in result.get("changes", {}).items():
            file_path = uri.replace("file://", "")
            for edit in edits:
                range_data = edit.get("range", {})
                changes.append({
                    "file": file_path,
                    "start_line": range_data.get("start", {}).get("line", 0) + 1,
                    "start_char": range_data.get("start", {}).get("character", 0) + 1,
                    "end_line": range_data.get("end", {}).get("line", 0) + 1,
                    "end_char": range_data.get("end", {}).get("character", 0) + 1,
                    "newText": edit.get("newText", ""),
                })

        return {"changes": changes}


class LSPManager:
    """Manages multiple LSP clients for a project."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.clients: dict[str, LSPClient] = {}
        self._lock = threading.Lock()

    def get_client(self, language: str) -> LSPClient | None:
        """Get or create an LSP client for a language."""
        with self._lock:
            if language in self.clients:
                return self.clients[language]

            client = LSPClient(language, str(self.workspace))
            if client.start():
                self.clients[language] = client
                return client
            return None

    def detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        for lang, config in LANGUAGE_SERVERS.items():
            if ext in config.get("file_extensions", []):
                return lang
        return "unknown"

    def find_language_for_file(self, file_path: str) -> LSPClient | None:
        """Find the appropriate LSP client for a file."""
        lang = self.detect_language(file_path)
        if lang == "unknown":
            return None
        return self.get_client(lang)

    def shutdown_all(self) -> None:
        """Shutdown all LSP clients."""
        with self._lock:
            for client in self.clients.values():
                client.stop()
            self.clients.clear()

    def status(self) -> dict:
        """Get LSP manager status."""
        return {
            "active_clients": {
                lang: {
                    "initialized": client._initialized,
                    "capabilities": list(client.capabilities.keys())[:5],
                }
                for lang, client in self.clients.items()
            },
            "supported_languages": list(LANGUAGE_SERVERS.keys()),
        }
