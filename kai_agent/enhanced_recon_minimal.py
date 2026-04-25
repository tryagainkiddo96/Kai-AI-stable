"""
Enhanced reconnaissance module integrating ghost_eye capabilities into Kai.
Provides comprehensive information gathering and reconnaissance tools.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ReconResult:
    """Structured reconnaissance result"""

    target: str
    timestamp: str
    dns_records: Dict[str, List[str]]
    whois_info: Optional[Dict] = None
    ip_location: Optional[Dict] = None
    http_headers: Optional[Dict] = None
    cms_detection: Optional[str] = None
    traceroute: Optional[List[str]] = None
    certificate_info: Optional[Dict] = None
    robots_txt: Optional[str] = None
    links_found: Optional[List[str]] = None


class KaiReconnaissance:
    """
    Enhanced reconnaissance module with ghost_eye-inspired capabilities.
    Provides comprehensive information gathering for security assessments.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.results_dir = workspace / "recon_results"
        self.results_dir.mkdir(exist_ok=True)

    def dns_lookup(self, target: str) -> Dict[str, List[str]]:
        """Perform comprehensive DNS enumeration"""
        records = {}
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA"]

        for record_type in record_types:
            try:
                import subprocess

                result = subprocess.run(
                    ["nslookup", "-type=" + record_type, target],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True,
                )
                if result.stdout.strip():
                    records[record_type] = result.stdout.strip().split("\n")[:5]
            except:
                pass

        return records

    def save_recon_result(self, result: ReconResult) -> None:
        """Save reconnaissance results to file"""
        filename = "recon_{}_{}.json".format(
            result.target.replace("/", "_").replace(":", "_"),
            result.timestamp.replace(" ", "_").replace(":", "_"),
        )
        filepath = self.results_dir / filename

        data = {
            "target": result.target,
            "timestamp": result.timestamp,
            "dns_records": result.dns_records or {},
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
