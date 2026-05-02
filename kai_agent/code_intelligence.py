"""
Kai Code Intelligence
Code analysis, generation, and understanding for Kai.
Ports the best of kai_capabilities.py into the kaikai ecosystem.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kai_agent.lsp_client import LSPManager


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CodeAnalysis:
    """Result of analyzing a piece of code."""
    language: str
    lines: int
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    complexity: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "lines": self.lines,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "complexity": self.complexity,
            "issues": self.issues,
        }

    def summary(self) -> str:
        parts = [f"{self.language} · {self.lines} lines · complexity {self.complexity}"]
        if self.functions:
            parts.append(f"functions: {', '.join(self.functions[:8])}{'…' if len(self.functions) > 8 else ''}")
        if self.classes:
            parts.append(f"classes: {', '.join(self.classes[:5])}")
        if self.imports:
            parts.append(f"imports: {', '.join(self.imports[:6])}{'…' if len(self.imports) > 6 else ''}")
        if self.issues:
            parts.append(f"issues: {'; '.join(self.issues[:3])}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".sh": "bash",
    ".ps1": "powershell",
    ".md": "markdown",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".lua": "lua",
    ".r": "r",
    ".dart": "dart",
}


def detect_language(path: str | Path) -> str:
    """Detect language from file extension."""
    return _EXT_MAP.get(Path(path).suffix.lower(), "unknown")


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------

def _analyze_python(code: str) -> CodeAnalysis:
    lines = code.split("\n")
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    issues: list[str] = []
    complexity = 1

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
    except SyntaxError as exc:
        issues.append(f"Syntax error: {exc}")

    if len(lines) > 500:
        issues.append("File is very long (>500 lines). Consider splitting.")
    long_lines = [i + 1 for i, ln in enumerate(lines) if len(ln) > 120]
    if long_lines:
        issues.append(f"Lines > 120 chars: {long_lines[:5]}{'…' if len(long_lines) > 5 else ''}")

    return CodeAnalysis("python", len(lines), functions, classes, imports, complexity, issues)


def _analyze_javascript(code: str, language: str = "javascript") -> CodeAnalysis:
    lines = code.split("\n")
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    issues: list[str] = []
    complexity = 1

    func_re = re.compile(
        r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))"
    )
    class_re = re.compile(r"class\s+(\w+)")
    import_re = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""")

    for line in lines:
        m = func_re.search(line)
        if m:
            functions.append(m.group(1) or m.group(2))
        m = class_re.search(line)
        if m:
            classes.append(m.group(1))
        m = import_re.search(line)
        if m:
            imports.append(m.group(1))

    kw = {"if", "else", "for", "while", "switch", "case", "catch", "&&", "||"}
    for line in lines:
        for k in kw:
            if k in line:
                complexity += 1
                break

    if len(lines) > 500:
        issues.append("File is very long (>500 lines). Consider splitting.")

    return CodeAnalysis(language, len(lines), functions, classes, imports, complexity, issues)


def analyze_code(code: str, language: str = "python") -> CodeAnalysis:
    """Analyze code in the given language."""
    if language == "python":
        return _analyze_python(code)
    elif language in ("javascript", "typescript"):
        return _analyze_javascript(code, language)
    else:
        return CodeAnalysis(language, len(code.split("\n")))


def analyze_file(path: str | Path) -> CodeAnalysis:
    """Analyze a file by path."""
    p = Path(path)
    if not p.exists():
        return CodeAnalysis("unknown", 0, issues=[f"File not found: {path}"])
    code = p.read_text(encoding="utf-8", errors="replace")
    lang = detect_language(p)
    return analyze_code(code, lang)


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def generate_function(
    name: str,
    params: list[str] | None = None,
    return_type: str = "None",
    docstring: str = "",
    language: str = "python",
) -> str:
    """Generate a function template."""
    params = params or []
    if language == "python":
        params_str = ", ".join(params)
        body = f'    """{docstring}"""' if docstring else "    pass"
        return f"def {name}({params_str}) -> {return_type}:\n{body}\n"
    elif language in ("javascript", "typescript"):
        params_str = ", ".join(params)
        return f"function {name}({params_str}) {{\n    // {docstring or 'TODO: Implement'}\n}}\n"
    return f"// Cannot generate {language} function\n"


def generate_class(
    name: str,
    methods: list[str] | None = None,
    parent: str | None = None,
    language: str = "python",
) -> str:
    """Generate a class template."""
    methods = methods or []
    if language == "python":
        inherits = f"({parent})" if parent else ""
        body = "\n".join(f"    def {m}(self):\n        pass" for m in methods)
        return f"class {name}{inherits}:\n    def __init__(self):\n        pass\n\n{body}\n"
    elif language in ("javascript", "typescript"):
        extends = f" extends {parent}" if parent else ""
        body = "\n".join(f"    {m}() {{\n        // TODO: Implement\n    }}" for m in methods)
        return f"class {name}{extends} {{\n    constructor() {{\n        // TODO: Initialize\n    }}\n\n{body}\n}}\n"
    return f"// Cannot generate {language} class\n"


def generate_test(
    function_name: str,
    test_cases: list[dict[str, Any]] | None = None,
    language: str = "python",
) -> str:
    """Generate unit test stubs."""
    if language != "python":
        return f"// Cannot generate {language} tests\n"
    test_cases = test_cases or [{"input": [], "expected": None}]
    tests: list[str] = []
    for i, case in enumerate(test_cases):
        inputs = ", ".join(repr(v) for v in case.get("input", []))
        expected = repr(case.get("expected"))
        tests.append(
            f"    def test_{function_name}_{i + 1}(self):\n"
            f"        result = {function_name}({inputs})\n"
            f"        self.assertEqual(result, {expected})"
        )
    tests_body = "\n\n".join(tests)
    return (
        f"import unittest\n\n"
        f"class Test{function_name.title()}(unittest.TestCase):\n"
        f"{tests_body}\n\n"
        f"if __name__ == '__main__':\n"
        f"    unittest.main()\n"
    )


# ---------------------------------------------------------------------------
# Project scanner
# ---------------------------------------------------------------------------

def scan_project(root: str | Path | None = None) -> dict[str, Any]:
    """Scan a project directory and return structure summary."""
    root = Path(root) if root else Path.cwd()

    def _normalize(relative_path: Path) -> str:
        return relative_path.as_posix()

    structure: dict[str, Any] = {
        "root": str(root),
        "directories": [],
        "files": [],
        "languages": {},
        "total_lines": 0,
    }
    try:
        for item in root.rglob("*"):
            if item.is_file():
                rel = _normalize(item.relative_to(root))
                structure["files"].append(rel)
                ext = item.suffix.lower()
                if ext in _EXT_MAP:
                    lang = _EXT_MAP[ext]
                    structure["languages"][lang] = structure["languages"].get(lang, 0) + 1
                try:
                    with open(item, "r", encoding="utf-8", errors="replace") as f:
                        structure["total_lines"] += sum(1 for _ in f)
                except (PermissionError, UnicodeDecodeError):
                    pass
            elif item.is_dir():
                structure["directories"].append(_normalize(item.relative_to(root)))
    except Exception as exc:
        structure["error"] = str(exc)

    structure["directories"].sort()
    structure["files"].sort()
    return structure


# ---------------------------------------------------------------------------
# Tool registry (extensible plugin system)
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Lightweight registry for Kai's callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._categories: dict[str, list[str]] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        handler: Any,
        params: dict[str, type] | None = None,
    ) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "category": category,
            "handler": handler,
            "params": params or {},
        }
        self._categories.setdefault(category, []).append(name)

    def get(self, name: str) -> dict[str, Any] | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            return [self._tools[n] for n in self._categories.get(category, []) if n in self._tools]
        return [
            {k: v for k, v in t.items() if k != "handler"}
            for t in self._tools.values()
        ]

    def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool not found: {name}"}
        try:
            return tool["handler"](**kwargs)
        except Exception as exc:
            return {"error": f"Tool execution failed: {exc}"}


# ---------------------------------------------------------------------------
# Facade — ties everything together for the assistant
# ---------------------------------------------------------------------------

class CodeIntelligence:
    """
    High-level API for Kai's code smarts.

    Usage from assistant:
        ci = CodeIntelligence()
        result = ci.analyze("def foo(): pass", "python")
        print(result.summary())
    """

    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = workspace
        self.registry = ToolRegistry()
        self._register_builtin_tools()

        # Lazy-load SecurityEngine
        self._security_engine = None
        if workspace:
            self._init_security_engine()

        # Lazy-load DependencyScanner
        self._dependency_scanner = None
        if workspace:
            self._init_dependency_scanner()

        # LSP Manager
        self.lsp = LSPManager(workspace) if workspace else None

    def _init_security_engine(self) -> None:
        try:
            from kai_agent.security_engine import SecurityEngine
            self._security_engine = SecurityEngine(self.workspace)
        except Exception:
            pass

    def _init_dependency_scanner(self) -> None:
        try:
            from kai_agent.dependency_scanner import DependencyScanner
            self._dependency_scanner = DependencyScanner(self.workspace)
        except Exception:
            pass

    @property
    def security_engine(self):
        if self._security_engine is None and self.workspace:
            self._init_security_engine()
        return self._security_engine

    @property
    def dependency_scanner(self):
        if self._dependency_scanner is None and self.workspace:
            self._init_dependency_scanner()
        return self._dependency_scanner

    # -- analysis --
    def analyze(self, code: str, language: str = "python") -> CodeAnalysis:
        return analyze_code(code, language)

    def analyze_file(self, path: str | Path) -> CodeAnalysis:
        return analyze_file(path)

    # -- generation --
    def gen_function(self, name: str, params: list[str] | None = None,
                     return_type: str = "None", docstring: str = "",
                     language: str = "python") -> str:
        return generate_function(name, params, return_type, docstring, language)

    def gen_class(self, name: str, methods: list[str] | None = None,
                  parent: str | None = None, language: str = "python") -> str:
        return generate_class(name, methods, parent, language)

    def gen_test(self, function_name: str,
                 test_cases: list[dict[str, Any]] | None = None,
                 language: str = "python") -> str:
        return generate_test(function_name, test_cases, language)

    # -- project --
    def scan(self, root: str | Path | None = None) -> dict[str, Any]:
        return scan_project(root)

    # -- tool registry helpers --
    def list_tools(self, category: str | None = None) -> list[dict[str, Any]]:
        return self.registry.list_tools(category)

    def execute_tool(self, name: str, **kwargs: Any) -> Any:
        return self.registry.execute(name, **kwargs)

    def _register_builtin_tools(self) -> None:
        self.registry.register(
            "analyze_code", "Analyze code structure, complexity, and issues",
            "code", self.analyze, {"code": str, "language": str},
        )
        self.registry.register(
            "analyze_file", "Analyze a file for structure, complexity, and issues",
            "code", self.analyze_file, {"path": str},
        )
        self.registry.register(
            "generate_function", "Generate a function template",
            "code", self.gen_function,
            {"name": str, "params": list, "return_type": str, "docstring": str, "language": str},
        )
        self.registry.register(
            "generate_class", "Generate a class template",
            "code", self.gen_class,
            {"name": str, "methods": list, "parent": str, "language": str},
        )
        self.registry.register(
            "generate_test", "Generate unit tests for a function",
            "code", self.gen_test,
            {"function_name": str, "test_cases": list, "language": str},
        )
        self.registry.register(
            "scan_project", "Scan project structure and stats",
            "project", self.scan, {},
        )

    # -- security --
    def scan_security(self, code: str, language: str = "python") -> list[dict]:
        """Scan code for security vulnerabilities."""
        if self.security_engine:
            findings = self.security_engine.scan_code_for_vulns(code, language)
            return [f.to_dict() for f in findings]
        return []

    def scan_file_security(self, path: str | Path) -> list[dict]:
        """Scan a file for security vulnerabilities."""
        if self.security_engine:
            findings = self.security_engine.scan_file_for_vulns(path)
            return [f.to_dict() for f in findings]
        return []

    def scan_project_security(self, root: str | Path | None = None) -> dict:
        """Scan entire project for security vulnerabilities."""
        if self.security_engine:
            target = Path(root) if root else self.workspace
            findings = self.security_engine.scan_project_for_vulns(target)
            report = self.security_engine.build_report(findings, target=str(target))
            return report
        return {"error": "Security engine not available"}

    def search_vulns(self, query: str) -> list[dict]:
        """Search vulnerability knowledge base."""
        if self.security_engine:
            return self.security_engine.search_vulns(query)
        return []

    def search_exploits(self, query: str) -> list[dict]:
        """Search exploit templates."""
        if self.security_engine:
            return self.security_engine.search_exploits(query)
        return []

    def get_exploit(self, exploit_id: str) -> dict | None:
        """Get exploit template by ID."""
        if self.security_engine:
            return self.security_engine.get_exploit_by_id(exploit_id)
        return None

    def get_security_status(self) -> dict:
        """Get security engine status."""
        if self.security_engine:
            return self.security_engine.status()
        return {"error": "Security engine not available"}

    # -- dependency scanning (SCA) --
    def scan_dependencies(self, project_path: str | Path | None = None) -> dict:
        """Scan project dependencies for known CVEs."""
        if self.dependency_scanner:
            target = Path(project_path) if project_path else self.workspace
            result = self.dependency_scanner.scan_project(target)
            return result.to_dict()
        return {"error": "Dependency scanner not available"}

    def scan_dependencies_report(self, project_path: str | Path | None = None) -> str:
        """Scan project dependencies and return human-readable report."""
        if self.dependency_scanner:
            target = Path(project_path) if project_path else self.workspace
            result = self.dependency_scanner.scan_project(target)
            return self.dependency_scanner.format_report(result)
        return "Dependency scanner not available."

    def get_dependency_findings(self) -> dict | None:
        """Get most recent cached dependency scan results."""
        if self.dependency_scanner:
            cached = self.dependency_scanner.get_cached_findings()
            if cached:
                return cached.to_dict()
        return None

    # -- LSP --
    def lsp_go_to_definition(self, file_path: str, line: int, column: int) -> list[dict]:
        """Go to definition of symbol at position."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                locations = client.go_to_definition(file_path, line, column)
                return [loc.to_dict() for loc in locations]
        return []

    def lsp_find_references(self, file_path: str, line: int, column: int) -> list[dict]:
        """Find all references to symbol at position."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                locations = client.find_references(file_path, line, column)
                return [loc.to_dict() for loc in locations]
        return []

    def lsp_symbols(self, file_path: str) -> list[dict]:
        """Get all symbols in a document."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                symbols = client.get_symbols(file_path)
                return [sym.to_dict() for sym in symbols]
        return []

    def lsp_workspace_symbols(self, query: str) -> list[dict]:
        """Search for symbols across workspace."""
        if self.lsp:
            all_symbols = []
            for client in self.lsp.clients.values():
                symbols = client.get_workspace_symbols(query)
                all_symbols.extend([sym.to_dict() for sym in symbols])
            return all_symbols
        return []

    def lsp_rename(self, file_path: str, line: int, column: int, new_name: str) -> dict:
        """Rename symbol at position."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                return client.rename(file_path, line, column, new_name)
        return {"changes": []}

    def lsp_hover(self, file_path: str, line: int, column: int) -> dict:
        """Get hover information for symbol at position."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                return client.get_hover(file_path, line, column)
        return {}

    def lsp_diagnostics(self, file_path: str) -> list[dict]:
        """Get diagnostics for a file."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                diagnostics = client.get_diagnostics(file_path)
                return [d.to_dict() for d in diagnostics]
        return []

    def lsp_completions(self, file_path: str, line: int, column: int) -> list[dict]:
        """Get code completions at position."""
        if self.lsp:
            client = self.lsp.find_language_for_file(file_path)
            if client:
                return client.get_completions(file_path, line, column)
        return []

    def lsp_status(self) -> dict:
        """Get LSP status."""
        if self.lsp:
            return self.lsp.status()
        return {"error": "LSP not available"}
