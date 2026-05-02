"""
Kai DependencyScanner — Software Composition Analysis (SCA).
Scans project dependencies against CVE databases (OSV.dev, NVD) to find
known vulnerabilities in third-party packages.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class PackageDependency:
    """A single project dependency."""
    name: str
    version: str
    ecosystem: str  # PyPI, npm, crates.io, Go, Maven, NuGet
    is_direct: bool = True  # True = direct dependency, False = transitive
    source_file: str = ""
    is_dev: bool = False  # dev/test dependency only?


@dataclass
class CVEFinding:
    """A CVE finding for a specific package."""
    cve_id: str
    package: str
    version: str
    ecosystem: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    cvss_score: float
    summary: str
    affected_versions: str  # version range description
    fixed_version: Optional[str] = None
    references: List[str] = field(default_factory=list)
    published: str = ""
    modified: str = ""


@dataclass
class ScanResult:
    """Complete dependency scan result."""
    target: str
    timestamp: str
    total_packages: int
    vulnerable_packages: int
    total_cves: int
    findings: List[CVEFinding] = field(default_factory=list)
    packages: List[PackageDependency] = field(default_factory=list)
    scan_duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def summary_by_severity(self) -> Dict[str, int]:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in self.findings:
            if f.severity in counts:
                counts[f.severity] += 1
        return counts

    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "timestamp": self.timestamp,
            "total_packages": self.total_packages,
            "vulnerable_packages": self.vulnerable_packages,
            "total_cves": self.total_cves,
            "severity_counts": self.summary_by_severity,
            "findings": [
                {
                    "cve_id": f.cve_id,
                    "package": f.package,
                    "version": f.version,
                    "ecosystem": f.ecosystem,
                    "severity": f.severity,
                    "cvss_score": f.cvss_score,
                    "summary": f.summary,
                    "affected_versions": f.affected_versions,
                    "fixed_version": f.fixed_version,
                    "published": f.published,
                }
                for f in self.findings
            ],
            "scan_duration_seconds": self.scan_duration_seconds,
            "errors": self.errors,
        }


def _parse_version_tuple(version: str) -> tuple:
    """Parse a version string into a comparable tuple."""
    parts = []
    for part in re.split(r"[.\-_]", version):
        # Extract numeric portion
        match = re.match(r"(\d+)", part)
        if match:
            parts.append(int(match.group(1)))
        else:
            parts.append(0)
    return tuple(parts)


def _version_in_range(version: str, affected_ranges: List[Dict]) -> bool:
    """Check if a version falls within any affected range."""
    v_tuple = _parse_version_tuple(version)
    for ar in affected_ranges:
        introduced = ar.get("introduced", "0")
        fixed = ar.get("fixed", None)

        introduced_tuple = _parse_version_tuple(introduced)
        if v_tuple < introduced_tuple:
            continue

        if fixed:
            fixed_tuple = _parse_version_tuple(fixed)
            if v_tuple < fixed_tuple:
                return True
        else:
            return True
    return False


class DependencyScanner:
    """
    Scans project dependencies for known vulnerabilities.
    Uses OSV.dev API (free, open-source, multi-ecosystem).
    """

    OSV_API_BASE = "https://api.osv.dev/v1"
    CACHE_TTL_SECONDS = 86400  # 24 hours

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.cache_path = workspace / "memory" / "dependency_scan_cache.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.write_text(
                json.dumps(self._cache, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _cache_key(self, package: str, version: str, ecosystem: str) -> str:
        raw = f"{ecosystem}:{package}:{version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_cached(self, package: str, version: str, ecosystem: str) -> Optional[List[Dict]]:
        key = self._cache_key(package, version, ecosystem)
        entry = self._cache.get(key)
        if entry and (time.time() - entry.get("timestamp", 0)) < self.CACHE_TTL_SECONDS:
            return entry.get("vulns")
        return None

    def _set_cache(self, package: str, version: str, ecosystem: str, vulns: List[Dict]) -> None:
        key = self._cache_key(package, version, ecosystem)
        self._cache[key] = {
            "timestamp": time.time(),
            "vulns": vulns,
        }
        self._save_cache()

    # === PACKAGE PARSERS ===

    def parse_requirements_txt(self, path: Path) -> List[PackageDependency]:
        """Parse Python requirements.txt or requirements/*.txt files."""
        deps = []
        if not path.exists():
            return deps
        try:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Handle: package==version, package>=version, package~=version
                match = re.match(r"^([a-zA-Z0-9_.-]+)\s*[=~<>!]+\s*([0-9][a-zA-Z0-9.*]*)", line)
                if match:
                    deps.append(PackageDependency(
                        name=match.group(1).lower(),
                        version=match.group(2).rstrip("*"),
                        ecosystem="PyPI",
                        source_file=str(path.relative_to(self.workspace)),
                    ))
                else:
                    # Package with no version pinned
                    match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
                    if match:
                        deps.append(PackageDependency(
                            name=match.group(1).lower(),
                            version="0",  # unknown version, flag it
                            ecosystem="PyPI",
                            source_file=str(path.relative_to(self.workspace)),
                        ))
        except Exception:
            pass
        return deps

    def parse_pipfile(self, path: Path) -> List[PackageDependency]:
        """Parse Python Pipfile (TOML format)."""
        deps = []
        if not path.exists():
            return deps
        try:
            content = path.read_text(encoding="utf-8")
            in_packages = False
            is_dev = False
            for line in content.splitlines():
                line = line.strip()
                if line == "[packages]":
                    in_packages = True
                    is_dev = False
                    continue
                elif line == "[dev-packages]":
                    in_packages = True
                    is_dev = True
                    continue
                elif line.startswith("["):
                    in_packages = False
                    continue
                if in_packages and "=" in line:
                    match = re.match(r'^([a-zA-Z0-9_.-]+)\s*=\s*["\']([~=<>]*[0-9][a-zA-Z0-9.*]*)["\']', line)
                    if match:
                        deps.append(PackageDependency(
                            name=match.group(1).lower(),
                            version=match.group(2).lstrip("=~<>"),
                            ecosystem="PyPI",
                            source_file=str(path.relative_to(self.workspace)),
                            is_dev=is_dev,
                        ))
        except Exception:
            pass
        return deps

    def parse_pyproject_toml(self, path: Path) -> List[PackageDependency]:
        """Parse Python pyproject.toml (basic regex-based, no TOML parser needed)."""
        deps = []
        if not path.exists():
            return deps
        try:
            content = path.read_text(encoding="utf-8")
            # Find dependencies = [...] section
            in_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if re.match(r"dependencies\s*=", stripped):
                    in_deps = True
                    continue
                if in_deps:
                    if stripped == "]":
                        in_deps = False
                        continue
                    # "package>=1.0.0",
                    match = re.match(r'"([a-zA-Z0-9_.-]+)\s*[=~<>!]+\s*([0-9][a-zA-Z0-9.]*)"', stripped)
                    if match:
                        deps.append(PackageDependency(
                            name=match.group(1).lower(),
                            version=match.group(2),
                            ecosystem="PyPI",
                            source_file=str(path.relative_to(self.workspace)),
                        ))
                    # "package" (unpinned)
                    match = re.match(r'"([a-zA-Z0-9_.-]+)"', stripped)
                    if match:
                        deps.append(PackageDependency(
                            name=match.group(1).lower(),
                            version="0",
                            ecosystem="PyPI",
                            source_file=str(path.relative_to(self.workspace)),
                        ))
        except Exception:
            pass
        return deps

    def parse_package_json(self, path: Path) -> List[PackageDependency]:
        """Parse Node.js package.json dependencies and devDependencies."""
        deps = []
        if not path.exists():
            return deps
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for section, is_dev in [("dependencies", False), ("devDependencies", True)]:
                for name, version in data.get(section, {}).items():
                    # Strip ^, ~, >= etc.
                    clean_version = re.sub(r"^[\^~>=< ]+", "", version)
                    deps.append(PackageDependency(
                        name=name,
                        version=clean_version,
                        ecosystem="npm",
                        source_file=str(path.relative_to(self.workspace)),
                        is_dev=is_dev,
                    ))
        except Exception:
            pass
        return deps

    def parse_package_lock(self, path: Path) -> List[PackageDependency]:
        """Parse package-lock.json for exact versions."""
        deps = []
        if not path.exists():
            return deps
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # v2/v3 format
            pkgs = data.get("packages", {})
            for pkg_path, info in pkgs.items():
                if not pkg_path:  # skip root
                    continue
                name = info.get("name", pkg_path.split("node_modules/")[-1])
                version = info.get("version", "0")
                deps.append(PackageDependency(
                    name=name,
                    version=version,
                    ecosystem="npm",
                    source_file=str(path.relative_to(self.workspace)),
                    is_dev=False,
                ))
            # v1 format
            if "dependencies" in data:
                for name, info in data["dependencies"].items():
                    deps.append(PackageDependency(
                        name=name,
                        version=info.get("version", "0"),
                        ecosystem="npm",
                        source_file=str(path.relative_to(self.workspace)),
                    ))
        except Exception:
            pass
        return deps

    def parse_cargo_toml(self, path: Path) -> List[PackageDependency]:
        """Parse Rust Cargo.toml (basic regex-based)."""
        deps = []
        if not path.exists():
            return deps
        try:
            content = path.read_text(encoding="utf-8")
            in_deps = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "[dependencies]" or stripped.startswith("[dependencies."):
                    in_deps = True
                    continue
                elif stripped.startswith("["):
                    in_deps = False
                    continue
                if in_deps and "=" in stripped:
                    match = re.match(r"([a-zA-Z0-9_-]+)\s*=\s*\"([~=<>]*[0-9][0-9.]*)\"", stripped)
                    if match:
                        deps.append(PackageDependency(
                            name=match.group(1),
                            version=match.group(2).lstrip("=~<>^"),
                            ecosystem="crates.io",
                            source_file=str(path.relative_to(self.workspace)),
                        ))
        except Exception:
            pass
        return deps

    def parse_go_mod(self, path: Path) -> List[PackageDependency]:
        """Parse Go go.mod require block."""
        deps = []
        if not path.exists():
            return deps
        try:
            content = path.read_text(encoding="utf-8")
            in_require = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("require ("):
                    in_require = True
                    continue
                elif in_require and stripped == ")":
                    in_require = False
                    continue
                # Single-line require
                match = re.match(r"require\s+([\w./-]+)\s+v?([0-9][a-zA-Z0-9.]*)", stripped)
                if match:
                    deps.append(PackageDependency(
                        name=match.group(1),
                        version=match.group(2),
                        ecosystem="Go",
                        source_file=str(path.relative_to(self.workspace)),
                    ))
                # Multi-line require block
                if in_require:
                    match = re.match(r"([\w./-]+)\s+v?([0-9][a-zA-Z0-9.]*)", stripped)
                    if match and not stripped.startswith("//"):
                        deps.append(PackageDependency(
                            name=match.group(1),
                            version=match.group(2),
                            ecosystem="Go",
                            source_file=str(path.relative_to(self.workspace)),
                        ))
        except Exception:
            pass
        return deps

    # === VULNERABILITY LOOKUP ===

    def query_osv(self, package: str, version: str, ecosystem: str) -> List[CVEFinding]:
        """Query OSV.dev API for vulnerabilities affecting a package version."""
        cached = self._get_cached(package, version, ecosystem)
        if cached is not None:
            return self._osv_response_to_findings(cached, package, version, ecosystem)

        payload = {
            "package": {"name": package, "ecosystem": ecosystem},
            "version": version,
        }
        vulns = []
        try:
            if REQUESTS_AVAILABLE:
                resp = requests.post(
                    f"{self.OSV_API_BASE}/query",
                    json=payload,
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    vulns = data.get("vulns", [])
            else:
                # Fallback: curl
                import tempfile
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    json.dump(payload, f)
                    f.flush()
                    result = subprocess.run(
                        ["curl", "-s", "-X", "POST",
                         f"{self.OSV_API_BASE}/query",
                         "-H", "Content-Type: application/json",
                         "-d", f"@{f.name}"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        vulns = data.get("vulns", [])
        except Exception:
            pass

        self._set_cache(package, version, ecosystem, vulns)
        return self._osv_response_to_findings(vulns, package, version, ecosystem)

    def _osv_response_to_findings(
        self, vulns: List[Dict], package: str, version: str, ecosystem: str
    ) -> List[CVEFinding]:
        """Convert OSV API response to CVEFinding objects."""
        findings = []
        for v in vulns:
            aliases = v.get("aliases", [])
            cve_id = next((a for a in aliases if a.startswith("CVE-")), v.get("id", ""))

            # Calculate max severity
            severity = "LOW"
            cvss_score = 0.0
            for sev in v.get("severity", []):
                if sev.get("type") == "CVSS_V3":
                    score_str = sev.get("score", "0.0")
                    try:
                        score = float(score_str)
                        if score > cvss_score:
                            cvss_score = score
                    except ValueError:
                        pass

            if cvss_score >= 9.0:
                severity = "CRITICAL"
            elif cvss_score >= 7.0:
                severity = "HIGH"
            elif cvss_score >= 4.0:
                severity = "MEDIUM"

            # Extract affected version ranges
            affected_ranges = []
            for affected in v.get("affected", []):
                for rng in affected.get("ranges", []):
                    events = rng.get("events", [])
                    introduced = None
                    fixed = None
                    for event in events:
                        if "introduced" in event:
                            introduced = event["introduced"]
                        if "fixed" in event:
                            fixed = event["fixed"]
                    if introduced is not None:
                        affected_ranges.append({"introduced": introduced, "fixed": fixed})

            # Check if our version is affected
            if affected_ranges and not _version_in_range(version, affected_ranges):
                continue

            fixed_version = None
            for ar in affected_ranges:
                if ar.get("fixed"):
                    if fixed_version is None or _parse_version_tuple(ar["fixed"]) > _parse_version_tuple(fixed_version):
                        fixed_version = ar["fixed"]

            references = [r.get("url", "") for r in v.get("references", []) if r.get("url")]

            findings.append(CVEFinding(
                cve_id=cve_id,
                package=package,
                version=version,
                ecosystem=ecosystem,
                severity=severity,
                cvss_score=cvss_score,
                summary=v.get("summary", v.get("details", ""))[:300],
                affected_versions=v.get("affected", [{}])[0].get("ranges", []) if v.get("affected") else [],
                fixed_version=fixed_version,
                references=references[:5],
                published=v.get("published", ""),
                modified=v.get("modified", ""),
            ))
        return findings

    # === SCAN ENTRY POINT ===

    def scan_project(self, project_path: Optional[Path] = None) -> ScanResult:
        """Scan a project for dependency vulnerabilities."""
        target = project_path or self.workspace
        start_time = time.time()
        errors = []

        # Collect all dependencies
        all_deps: List[PackageDependency] = []

        # Python
        all_deps.extend(self.parse_requirements_txt(target / "requirements.txt"))
        for req_file in target.rglob("requirements*.txt"):
            if "venv" not in str(req_file) and ".tox" not in str(req_file):
                all_deps.extend(self.parse_requirements_txt(req_file))
        all_deps.extend(self.parse_pyproject_toml(target / "pyproject.toml"))
        all_deps.extend(self.parse_pipfile(target / "Pipfile"))

        # JavaScript/TypeScript
        all_deps.extend(self.parse_package_json(target / "package.json"))
        all_deps.extend(self.parse_package_lock(target / "package-lock.json"))
        all_deps.extend(self.parse_package_lock(target / "yarn.lock"))

        # Rust
        all_deps.extend(self.parse_cargo_toml(target / "Cargo.toml"))

        # Go
        all_deps.extend(self.parse_go_mod(target / "go.mod"))

        # Deduplicate
        seen = set()
        unique_deps = []
        for dep in all_deps:
            key = (dep.name, dep.ecosystem)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        # Query vulnerabilities
        findings: List[CVEFinding] = []
        for dep in unique_deps:
            try:
                if dep.version == "0":
                    # Can't check unpinned deps reliably
                    continue
                vulns = self.query_osv(dep.name, dep.version, dep.ecosystem)
                findings.extend(vulns)
            except Exception as e:
                errors.append(f"Error scanning {dep.name}: {str(e)}")

        # Build result
        vuln_packages = len(set((f.package, f.ecosystem) for f in findings))

        result = ScanResult(
            target=str(target),
            timestamp=datetime.utcnow().isoformat(),
            total_packages=len(unique_deps),
            vulnerable_packages=vuln_packages,
            total_cves=len(findings),
            findings=sorted(findings, key=lambda f: -f.cvss_score),
            packages=unique_deps,
            scan_duration_seconds=round(time.time() - start_time, 2),
            errors=errors,
        )

        # Save scan result
        self._save_scan_result(result)
        return result

    def _save_scan_result(self, result: ScanResult) -> None:
        """Persist scan result to reports directory."""
        reports_dir = self.workspace / "vulnerability_reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"dependency_scan_{timestamp}.json"
        report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    def get_cached_findings(self) -> Optional[ScanResult]:
        """Get the most recent cached scan result."""
        reports_dir = self.workspace / "vulnerability_reports"
        if not reports_dir.exists():
            return None
        reports = sorted(reports_dir.glob("dependency_scan_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not reports:
            return None
        try:
            data = json.loads(reports[0].read_text(encoding="utf-8"))
            findings = []
            for f in data.get("findings", []):
                findings.append(CVEFinding(**{k: v for k, v in f.items() if k in CVEFinding.__dataclass_fields__}))
            packages = []
            # Return a simplified result from cache
            return ScanResult(
                target=data.get("target", ""),
                timestamp=data.get("timestamp", ""),
                total_packages=data.get("total_packages", 0),
                vulnerable_packages=data.get("vulnerable_packages", 0),
                total_cves=data.get("total_cves", 0),
                findings=findings,
                scan_duration_seconds=data.get("scan_duration_seconds", 0),
                errors=data.get("errors", []),
            )
        except Exception:
            return None

    def format_report(self, result: ScanResult) -> str:
        """Format scan result as a human-readable report."""
        lines = []
        lines.append(f"DEPENDENCY VULNERABILITY SCAN")
        lines.append(f"{'='*50}")
        lines.append(f"Target: {result.target}")
        lines.append(f"Time: {result.timestamp}")
        lines.append(f"Duration: {result.scan_duration_seconds}s")
        lines.append(f"")
        lines.append(f"PACKAGES SCANNED: {result.total_packages}")
        lines.append(f"VULNERABLE PACKAGES: {result.vulnerable_packages}")
        lines.append(f"TOTAL CVEs FOUND: {result.total_cves}")
        lines.append(f"")

        sev = result.summary_by_severity
        lines.append(f"SEVERITY BREAKDOWN:")
        lines.append(f"  CRITICAL: {sev['CRITICAL']}")
        lines.append(f"  HIGH:     {sev['HIGH']}")
        lines.append(f"  MEDIUM:   {sev['MEDIUM']}")
        lines.append(f"  LOW:      {sev['LOW']}")
        lines.append(f"")

        if result.findings:
            lines.append(f"FINDINGS:")
            lines.append(f"{'-'*50}")
            for f in result.findings:
                lines.append(f"  [{f.severity}] {f.cve_id} — {f.package}@{f.version} ({f.ecosystem})")
                lines.append(f"    CVSS: {f.cvss_score}")
                lines.append(f"    Summary: {f.summary}")
                if f.fixed_version:
                    lines.append(f"    Fix: Upgrade to >= {f.fixed_version}")
                if f.references:
                    lines.append(f"    Links: {', '.join(f.references[:2])}")
                lines.append(f"")

        if result.errors:
            lines.append(f"ERRORS:")
            for err in result.errors:
                lines.append(f"  - {err}")
            lines.append(f"")

        if not result.findings:
            lines.append(f"No known vulnerabilities found in dependencies.")

        return "\n".join(lines)
