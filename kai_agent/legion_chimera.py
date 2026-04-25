from __future__ import annotations

import hashlib
import json
import random
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


@dataclass
class LegionWorker:
    id: str
    provider: str
    endpoint: str
    max_concurrent: int = 5
    current_load: int = 0
    status: str = "active"
    region: str = "unknown"
    tags: list[str] = field(default_factory=list)
    last_heartbeat: str = field(default_factory=_utc_now_iso)


class LegionController:
    def __init__(self, save_path: Path, source_path: Path | None = None) -> None:
        self.save_path = save_path
        self.source_path = source_path
        self._lock = threading.Lock()
        self.workers: dict[str, LegionWorker] = {}
        self._load()

    def _load(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _read_json(self.save_path, {"workers": []})
        workers = payload.get("workers", [])
        if not isinstance(workers, list):
            raise ValueError(f"Invalid workers payload in {self.save_path}")
        parsed: dict[str, LegionWorker] = {}
        for item in workers:
            if not isinstance(item, dict):
                continue
            worker = LegionWorker(
                id=str(item.get("id") or f"worker_{uuid.uuid4().hex[:8]}"),
                provider=str(item.get("provider") or "unknown"),
                endpoint=str(item.get("endpoint") or ""),
                max_concurrent=int(item.get("max_concurrent") or 5),
                current_load=int(item.get("current_load") or 0),
                status=str(item.get("status") or "active"),
                region=str(item.get("region") or "unknown"),
                tags=[str(tag) for tag in (item.get("tags") or []) if str(tag).strip()],
                last_heartbeat=str(item.get("last_heartbeat") or _utc_now_iso()),
            )
            if worker.endpoint:
                parsed[worker.id] = worker
        self.workers = parsed

    def _save(self) -> None:
        payload = {
            "workers": [asdict(worker) for worker in self.workers.values()],
            "updated_at": _utc_now_iso(),
            "source_script": str(self.source_path) if self.source_path else "",
        }
        self.save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def recruit_worker(
        self,
        provider: str,
        endpoint: str,
        *,
        region: str = "unknown",
        max_concurrent: int = 5,
        tags: list[str] | None = None,
    ) -> LegionWorker:
        provider = provider.strip()
        endpoint = endpoint.strip()
        region = region.strip() or "unknown"
        if not provider:
            raise ValueError("provider is required")
        if not endpoint:
            raise ValueError("endpoint is required")
        with self._lock:
            worker_id = f"{provider}_{uuid.uuid4().hex[:8]}"
            worker = LegionWorker(
                id=worker_id,
                provider=provider,
                endpoint=endpoint,
                max_concurrent=max(1, int(max_concurrent)),
                region=region,
                tags=[str(tag).strip() for tag in (tags or []) if str(tag).strip()],
            )
            self.workers[worker.id] = worker
            self._save()
            return worker

    def heartbeat(self, worker_id: str, *, status: str = "active") -> LegionWorker:
        with self._lock:
            worker = self.workers.get(worker_id)
            if worker is None:
                raise KeyError(f"unknown worker: {worker_id}")
            worker.last_heartbeat = _utc_now_iso()
            worker.status = status.strip() or "active"
            self._save()
            return worker

    def list_bots(self) -> list[dict[str, Any]]:
        """List all registered workers (bots)."""
        return [asdict(worker) for worker in self.workers.values()]

    def stats(self) -> dict[str, Any]:
        workers = list(self.workers.values())
        providers = sorted({worker.provider for worker in workers})
        return {
            "total_workers": len(workers),
            "active_workers": sum(1 for worker in workers if worker.status == "active"),
            "providers": providers,
            "source_script_present": bool(self.source_path and self.source_path.exists()),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "ok": True,
            "updated_at": _utc_now_iso(),
            "stats": self.stats(),
            "workers": [asdict(worker) for worker in self.workers.values()],
            "source_script": str(self.source_path) if self.source_path else "",
        }


class ChimeraController:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 Chrome/117.0.0.0",
    ]
    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "application/json, text/plain, */*",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    ]
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.8",
        "fr-FR,fr;q=0.9",
        "de-DE,de;q=0.9",
    ]
    TLS_VERSIONS = ["TLSv1.2", "TLSv1.3"]
    MUTATION_DEPTH = {
        "low": 1,
        "medium": 3,
        "high": 6,
    }

    def __init__(self, save_path: Path, source_path: Path | None = None) -> None:
        self.save_path = save_path
        self.source_path = source_path
        self._lock = threading.Lock()
        self.mutation_count = 0
        self.current_fingerprint: dict[str, Any] = {}
        self._load()

    def _generate_fingerprint(self) -> dict[str, Any]:
        return {
            "user_agent": random.choice(self.USER_AGENTS),
            "accept": random.choice(self.ACCEPT_HEADERS),
            "accept_language": random.choice(self.ACCEPT_LANGUAGES),
            "tls_version": random.choice(self.TLS_VERSIONS),
            "fingerprint_id": hashlib.sha256(uuid.uuid4().hex.encode("utf-8")).hexdigest()[:16],
            "mutated_at": _utc_now_iso(),
        }

    def _load(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _read_json(self.save_path, {})
        self.mutation_count = int(payload.get("mutation_count", 0) or 0)
        current = payload.get("current_fingerprint")
        if isinstance(current, dict) and current:
            self.current_fingerprint = current
            return
        self.current_fingerprint = self._generate_fingerprint()
        self._save()

    def _save(self) -> None:
        payload = {
            "mutation_count": self.mutation_count,
            "current_fingerprint": self.current_fingerprint,
            "updated_at": _utc_now_iso(),
            "source_script": str(self.source_path) if self.source_path else "",
        }
        self.save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def mutate(self, intensity: str = "medium") -> dict[str, Any]:
        with self._lock:
            depth = self.MUTATION_DEPTH.get(intensity, self.MUTATION_DEPTH["medium"])
            keys = ["user_agent", "accept", "accept_language", "tls_version"]
            for _ in range(depth):
                field_name = random.choice(keys)
                if field_name == "user_agent":
                    self.current_fingerprint[field_name] = random.choice(self.USER_AGENTS)
                elif field_name == "accept":
                    self.current_fingerprint[field_name] = random.choice(self.ACCEPT_HEADERS)
                elif field_name == "accept_language":
                    self.current_fingerprint[field_name] = random.choice(self.ACCEPT_LANGUAGES)
                elif field_name == "tls_version":
                    self.current_fingerprint[field_name] = random.choice(self.TLS_VERSIONS)
            self.mutation_count += 1
            self.current_fingerprint["fingerprint_id"] = hashlib.sha256(
                f"{self.mutation_count}:{uuid.uuid4().hex}".encode("utf-8")
            ).hexdigest()[:16]
            self.current_fingerprint["mutated_at"] = _utc_now_iso()
            self._save()
            return self.snapshot()

    def headers(self) -> dict[str, str]:
        current = self.current_fingerprint
        return {
            "User-Agent": str(current.get("user_agent") or ""),
            "Accept": str(current.get("accept") or ""),
            "Accept-Language": str(current.get("accept_language") or ""),
            "X-Chimera-Fingerprint": str(current.get("fingerprint_id") or ""),
        }

    def status(self) -> dict[str, Any]:
        """Get Chimera status summary."""
        return {
            "ok": True,
            "mutation_count": self.mutation_count,
            "fingerprint_id": self.current_fingerprint.get("fingerprint_id", ""),
            "user_agent": self.current_fingerprint.get("user_agent", ""),
            "mutated_at": self.current_fingerprint.get("mutated_at", ""),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "ok": True,
            "updated_at": _utc_now_iso(),
            "mutation_count": self.mutation_count,
            "current_fingerprint": self.current_fingerprint,
            "headers": self.headers(),
            "source_script": str(self.source_path) if self.source_path else "",
            "source_script_present": bool(self.source_path and self.source_path.exists()),
        }
