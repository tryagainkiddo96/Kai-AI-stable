"""Tool Calling — protocol for LLM to request tool execution."""
from __future__ import annotations

import json
import re


def parse_tool_calls(text: str) -> list[dict]:
    """Extract tool call requests from LLM output.

    Format: <tool>tool_name</tool><args>{"key": "value"}</args>
    Returns list of {"name": str, "args": dict}
    """
    pattern = r"<tool>\s*([\w_]+)\s*</tool>\s*<args>\s*(.*?)\s*</args>"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    calls = []
    for name, args_text in matches:
        try:
            args = json.loads(args_text) if args_text.strip() else {}
        except json.JSONDecodeError:
            args = {"raw": args_text.strip()}
        calls.append({"name": name.strip(), "args": args})
    return calls


TOOL_CALL_SYSTEM = """
TOOL USAGE: You can request tools by outputting a tool call block. The system will execute it and feed you the result. Continue analyzing after each result.

Format your tool calls like this:
<tool>tool_name</tool><args>{"param1": "value1"}</args>

Available tools:
- run_shell(command, timeout) — Run any shell command
- read_file(path) — Read a file's contents
- list_files(path) — List directory contents
- search_web(query) — Search the internet for information
- webclaw_scrape(url, fmt, include, exclude) — Extract clean LLM-optimized content from a URL (fmt: llm, markdown, json, text, html)
- webclaw_crawl(url, depth, max_pages) — Recursively crawl a site, extract all pages
- webclaw_map(url) — Discover all URLs from a site's sitemap
- webclaw_brand(url) — Extract brand identity (colors, fonts, logos) from a website
- webclaw_batch(urls, fmt) — Extract content from multiple URLs in parallel
- webclaw_diff(url, snapshot_file) — Compare current page against a previous snapshot
- nuclei_scan(target, templates, severity, timeout) — Template-based vuln scanner (1000+ CVE templates)
- opsec_status() — Check Tor, proxychains, and external IP
- opsec_enable_tor() — Install/configure Tor + proxychains for anonymous routing
- active_recon(target, ports, timeout) — Nmap port scan
- web_recon(url, timeout) — Nikto web vulnerability scanner
- dir_busting(url, wordlist, timeout) — Gobuster directory enumeration
- vulnerability_scan(target, scan_type, timeout) — Nmap vulnerability scan
- service_enum(target, service, timeout) — Enumerate specific service (smb, ssh, ftp, dns, smtp, snmp)
- search_exploits(query, timeout) — Search for known exploits
- passive_recon(target, timeout) — OSINT: WHOIS, DNS, certificate transparency
- hash_crack(hash_file, hash_type, wordlist, timeout) — Crack password hashes
- password_attack(target, service, username, wordlist, timeout) — Brute force login
- privilege_escalation_check(target_ip, timeout) — Check for privesc vectors
- capture_screen_ocr() — Capture screen and read text
- write_file(path, content) — Write content to a file
- create_engagement(name, target, scope, rules) — Create pentest engagement
- generate_report(engagement_name, target) — Generate pentest report

RULES:
1. Only output ONE tool call per response
2. After receiving results, analyze them and decide next step
3. Maximum 3 tool calls per user request
4. If you've done 3 tool calls, stop and give your final analysis
5. Always explain what you found in plain English
6. If a tool fails, try a different approach rather than giving up
"""


def strip_tool_tags(text: str) -> str:
    """Remove tool call blocks from text for display."""
    return re.sub(r"<tool>.*?</tool>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def format_tool_result(tool_name: str, result: str) -> str:
    """Format a tool result for feeding back to the LLM."""
    max_chars = 6000
    if len(result) > max_chars:
        result = result[:max_chars] + "\n[... output truncated ...]"
    return f"\n\n--- Tool Result ({tool_name}) ---\n{result}\n--- End Tool Result ---\n\nContinue your analysis. You can call another tool or give your final answer."
