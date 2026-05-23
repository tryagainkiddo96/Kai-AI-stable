"""CTOS Database — persistent SQLite layer for NetMap, Breach, Urban Scanner, Journal, Rituals."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional


class CTOSDatabase:
    """Persistent SQLite storage for all CTOS modules."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = None
        if self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), timeout=30, isolation_level=None)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
        return self._local.conn

    def _commit(self):
        pass

    _flush = _commit

    def _init_schema(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                ip TEXT PRIMARY KEY,
                mac TEXT DEFAULT '',
                vendor TEXT DEFAULT '',
                hostname TEXT DEFAULT '',
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                os_guess TEXT DEFAULT '',
                ports_json TEXT DEFAULT '[]',
                services_json TEXT DEFAULT '[]',
                smb_access INTEGER DEFAULT 0,
                rdp_open INTEGER DEFAULT 0,
                tailscale_ip TEXT DEFAULT '',
                tags_json TEXT DEFAULT '[]',
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS breach_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                result TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS urban_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                detail_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT DEFAULT '',
                data_json TEXT DEFAULT '{}',
                importance INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rituals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                steps_json TEXT NOT NULL,
                created REAL NOT NULL,
                uses INTEGER DEFAULT 0,
                last_used REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS twin_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                subsystem TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source_window TEXT DEFAULT '',
                timestamp REAL NOT NULL,
                session_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS dns_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                timestamp REAL NOT NULL,
                process_name TEXT DEFAULT '',
                query_count INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                cwd TEXT DEFAULT '',
                exit_code INTEGER DEFAULT 0,
                timestamp REAL NOT NULL,
                intent TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS thermal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone TEXT NOT NULL,
                temp_celsius REAL NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS disk_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive TEXT NOT NULL,
                label TEXT DEFAULT '',
                total_bytes REAL DEFAULT 0,
                free_bytes REAL DEFAULT 0,
                smart_wear REAL DEFAULT 0,
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hardware_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT DEFAULT '',
                device_type TEXT DEFAULT '',
                serial TEXT DEFAULT '',
                action TEXT DEFAULT 'detected',
                timestamp REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS arp_watch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                mac TEXT DEFAULT '',
                vendor TEXT DEFAULT '',
                state TEXT DEFAULT 'new',
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                is_intruder INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS troll_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                hostname TEXT DEFAULT '',
                last_trolled REAL DEFAULT 0,
                wallpaper_set TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS forensics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                trigger_source TEXT DEFAULT '',
                snapshot_json TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                icon TEXT DEFAULT '',
                unlocked_at REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS achievement_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracker_name TEXT UNIQUE NOT NULL,
                current_value INTEGER DEFAULT 0,
                target_value INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                dream_text TEXT DEFAULT '',
                raw_event_count INTEGER DEFAULT 0,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                probability REAL DEFAULT 0.0,
                sample_count INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_breach_ip ON breach_log(ip);
            CREATE INDEX IF NOT EXISTS idx_urban_time ON urban_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_journal_time ON journal(timestamp);
            CREATE INDEX IF NOT EXISTS idx_journal_type ON journal(event_type);
            CREATE INDEX IF NOT EXISTS idx_twin_subsys ON twin_health(subsystem);
            CREATE INDEX IF NOT EXISTS idx_clip_ts ON clipboard_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_dns_domain ON dns_queries(domain);
            CREATE INDEX IF NOT EXISTS idx_dns_ts ON dns_queries(timestamp);
            CREATE INDEX IF NOT EXISTS idx_cmd_ts ON command_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_thermal_ts ON thermal_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_disk_ts ON disk_snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_hw_ts ON hardware_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_arp_ip ON arp_watch(ip);
            CREATE INDEX IF NOT EXISTS idx_forensic_ts ON forensics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_dream_date ON dreams(date);
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                channel TEXT NOT NULL,
                message TEXT NOT NULL,
                target TEXT DEFAULT '',
                success INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS dns_blocked (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                domain TEXT NOT NULL,
                client_ip TEXT DEFAULT '',
                action TEXT DEFAULT 'blocked'
            );
            CREATE TABLE IF NOT EXISTS traffic_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                local_ip TEXT DEFAULT '',
                local_port INTEGER DEFAULT 0,
                remote_ip TEXT DEFAULT '',
                remote_port INTEGER DEFAULT 0,
                protocol TEXT DEFAULT 'TCP',
                process_name TEXT DEFAULT '',
                state TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS browser_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                browser TEXT DEFAULT '',
                visit_count INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                action_type TEXT NOT NULL,
                params_json TEXT DEFAULT '{}',
                enabled INTEGER DEFAULT 1,
                created REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_pattern_dow ON daily_patterns(day_of_week, hour);
            CREATE INDEX IF NOT EXISTS idx_notify_ts ON notifications(timestamp);
            CREATE INDEX IF NOT EXISTS idx_dns_block_ts ON dns_blocked(timestamp);
            CREATE INDEX IF NOT EXISTS idx_traffic_ts ON traffic_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_browser_ts ON browser_history(timestamp);

            CREATE VIRTUAL TABLE IF NOT EXISTS chat_fts USING fts5(
                role, content, tokenize='unicode61'
            );
        """)
        self._commit()

    # ── Devices ────────────────────────────────────────────────────────────────

    def upsert_device(self, ip: str, **kwargs):
        now = time.time()
        existing = self.get_device(ip)
        data = {
            "ip": ip,
            "first_seen": existing["first_seen"] if existing else now,
            "last_seen": now,
            "mac": kwargs.get("mac", existing["mac"] if existing else ""),
            "vendor": kwargs.get("vendor", existing["vendor"] if existing else ""),
            "hostname": kwargs.get("hostname", existing["hostname"] if existing else ""),
            "os_guess": kwargs.get("os_guess", existing["os_guess"] if existing else ""),
            "ports_json": json.dumps(kwargs.get("ports", json.loads(existing["ports_json"]) if existing and existing.get("ports_json") else [])),
            "services_json": json.dumps(kwargs.get("services", json.loads(existing["services_json"]) if existing and existing.get("services_json") else [])),
            "smb_access": int(kwargs.get("smb_access", existing["smb_access"] if existing else 0)),
            "rdp_open": int(kwargs.get("rdp_open", existing["rdp_open"] if existing else 0)),
            "tailscale_ip": kwargs.get("tailscale_ip", existing["tailscale_ip"] if existing else ""),
            "tags_json": json.dumps(kwargs.get("tags", json.loads(existing["tags_json"]) if existing and existing.get("tags_json") else [])),
            "notes": kwargs.get("notes", existing["notes"] if existing else ""),
        }
        c = self._conn()
        c.execute("""
            INSERT OR REPLACE INTO devices
            (ip, mac, vendor, hostname, first_seen, last_seen, os_guess, ports_json, services_json, smb_access, rdp_open, tailscale_ip, tags_json, notes)
            VALUES (:ip, :mac, :vendor, :hostname, :first_seen, :last_seen, :os_guess, :ports_json, :services_json, :smb_access, :rdp_open, :tailscale_ip, :tags_json, :notes)
        """, data)
        self._commit()
        self._flush()

    def get_device(self, ip: str) -> Optional[dict]:
        c = self._conn()
        row = c.execute("SELECT * FROM devices WHERE ip = ?", (ip,)).fetchone()
        if row:
            d = dict(row)
            d["ports"] = json.loads(d.get("ports_json", "[]"))
            d["services"] = json.loads(d.get("services_json", "[]"))
            d["tags"] = json.loads(d.get("tags_json", "[]"))
            return d
        return None

    def all_devices(self) -> list[dict]:
        c = self._conn()
        rows = c.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["ports"] = json.loads(d.get("ports_json", "[]"))
            d["services"] = json.loads(d.get("services_json", "[]"))
            d["tags"] = json.loads(d.get("tags_json", "[]"))
            result.append(d)
        return result

    def delete_device(self, ip: str):
        self._conn().execute("DELETE FROM devices WHERE ip = ?", (ip,))
        self._commit()

    # ── Breach Log ──────────────────────────────────────────────────────────────

    def log_breach(self, ip: str, action: str, result: str = ""):
        self._conn().execute(
            "INSERT INTO breach_log (ip, timestamp, action, result) VALUES (?, ?, ?, ?)",
            (ip, time.time(), action, result),
        )
        self._commit()
        self._flush()

    def get_breach_log(self, ip: str, limit: int = 50) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM breach_log WHERE ip = ? ORDER BY timestamp DESC LIMIT ?",
            (ip, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Urban Events ────────────────────────────────────────────────────────────

    def add_urban_event(self, event_type: str, summary: str, detail: dict = None, source: str = ""):
        self._conn().execute(
            "INSERT INTO urban_events (timestamp, event_type, source, summary, detail_json) VALUES (?, ?, ?, ?, ?)",
            (time.time(), event_type, source, summary, json.dumps(detail or {})),
        )
        self._commit()

    def get_urban_events(self, limit: int = 100, since: float = 0) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM urban_events WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
            (since, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Journal ──────────────────────────────────────────────────────────────────

    def journal_entry(self, event_type: str, data: dict, source: str = "", importance: int = 0):
        self._conn().execute(
            "INSERT INTO journal (timestamp, event_type, source, data_json, importance) VALUES (?, ?, ?, ?, ?)",
            (time.time(), event_type, source, json.dumps(data), importance),
        )
        self._commit()

    def query_journal(self, event_type: str = "", limit: int = 50, since: float = 0) -> list[dict]:
        if event_type:
            rows = self._conn().execute(
                "SELECT * FROM journal WHERE event_type = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, since, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM journal WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d.get("data_json", "{}"))
            result.append(d)
        return result

    # ── Rituals ──────────────────────────────────────────────────────────────────

    def save_ritual(self, name: str, steps: list[dict]) -> bool:
        try:
            self._conn().execute(
                "INSERT INTO rituals (name, steps_json, created, last_used) VALUES (?, ?, ?, ?)",
                (name, json.dumps(steps), time.time(), 0),
            )
            self._commit()
            self._flush()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_ritual(self, name: str) -> Optional[dict]:
        row = self._conn().execute("SELECT * FROM rituals WHERE name = ?", (name,)).fetchone()
        if row:
            d = dict(row)
            d["steps"] = json.loads(d["steps_json"])
            return d
        return None

    def all_rituals(self) -> list[dict]:
        rows = self._conn().execute("SELECT * FROM rituals ORDER BY uses DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["steps"] = json.loads(d["steps_json"])
            result.append(d)
        return result

    def use_ritual(self, name: str):
        self._conn().execute(
            "UPDATE rituals SET uses = uses + 1, last_used = ? WHERE name = ?",
            (time.time(), name),
        )
        self._commit()
        self._flush()

    def delete_ritual(self, name: str):
        self._conn().execute("DELETE FROM rituals WHERE name = ?", (name,))
        self._commit()
        self._flush()

    # ── Twin Health ──────────────────────────────────────────────────────────────

    def log_health(self, subsystem: str, status: str, detail: str = ""):
        self._conn().execute(
            "INSERT INTO twin_health (timestamp, subsystem, status, detail) VALUES (?, ?, ?, ?)",
            (time.time(), subsystem, status, detail),
        )
        self._commit()

    def get_recent_health(self, limit: int = 100) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM twin_health ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_subsystem_health(self, subsystem: str, limit: int = 20) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM twin_health WHERE subsystem = ? ORDER BY timestamp DESC LIMIT ?",
            (subsystem, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Clipboard History ─────────────────────────────────────────────────────────

    def log_clipboard(self, content: str, source_window: str = "", session_id: str = ""):
        self._conn().execute(
            "INSERT INTO clipboard_history (content, source_window, timestamp, session_id) VALUES (?, ?, ?, ?)",
            (content[:2000], source_window, time.time(), session_id),
        )
        self._commit()

    def query_clipboard(self, search: str = "", since: float = 0, limit: int = 100) -> list[dict]:
        if search:
            rows = self._conn().execute(
                "SELECT * FROM clipboard_history WHERE content LIKE ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{search}%", since, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM clipboard_history WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def clipboard_stats(self) -> dict:
        row = self._conn().execute("SELECT COUNT(*) as total, MAX(timestamp) as last FROM clipboard_history").fetchone()
        return dict(row) if row else {"total": 0, "last": 0}

    # ── DNS Queries ───────────────────────────────────────────────────────────────

    def log_dns_query(self, domain: str, process_name: str = ""):
        existing = self._conn().execute(
            "SELECT id, query_count FROM dns_queries WHERE domain = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 1",
            (domain, time.time() - 300),
        ).fetchone()
        if existing:
            self._conn().execute("UPDATE dns_queries SET query_count = query_count + 1, timestamp = ? WHERE id = ?",
                                 (time.time(), existing["id"]))
        else:
            self._conn().execute(
                "INSERT INTO dns_queries (domain, timestamp, process_name) VALUES (?, ?, ?)",
                (domain, time.time(), process_name),
            )
        self._commit()

    def query_dns_history(self, search: str = "", limit: int = 100) -> list[dict]:
        if search:
            rows = self._conn().execute(
                "SELECT * FROM dns_queries WHERE domain LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{search}%", limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM dns_queries ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def top_domains(self, limit: int = 20) -> list[dict]:
        rows = self._conn().execute(
            "SELECT domain, SUM(query_count) as total, MAX(timestamp) as last_seen FROM dns_queries GROUP BY domain ORDER BY total DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Command History ────────────────────────────────────────────────────────────

    def log_command(self, command: str, cwd: str = "", exit_code: int = 0, intent: str = ""):
        self._conn().execute(
            "INSERT INTO command_history (command, cwd, exit_code, timestamp, intent) VALUES (?, ?, ?, ?, ?)",
            (command[:500], cwd, exit_code, time.time(), intent),
        )
        self._commit()

    def query_commands(self, intent: str = "", limit: int = 100) -> list[dict]:
        if intent:
            rows = self._conn().execute(
                "SELECT * FROM command_history WHERE intent = ? ORDER BY timestamp DESC LIMIT ?",
                (intent, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM command_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Thermal History ────────────────────────────────────────────────────────────

    def log_temperature(self, zone: str, temp_celsius: float):
        self._conn().execute(
            "INSERT INTO thermal_history (zone, temp_celsius, timestamp) VALUES (?, ?, ?)",
            (zone, temp_celsius, time.time()),
        )
        self._commit()

    def query_temperatures(self, zone: str = "", hours: int = 24, limit: int = 500) -> list[dict]:
        since = time.time() - (hours * 3600)
        if zone:
            rows = self._conn().execute(
                "SELECT * FROM thermal_history WHERE zone = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (zone, since, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM thermal_history WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def latest_temps(self) -> dict:
        rows = self._conn().execute(
            "SELECT zone, temp_celsius, MAX(timestamp) as ts FROM thermal_history GROUP BY zone ORDER BY ts DESC"
        ).fetchall()
        return {r["zone"]: {"temp": r["temp_celsius"], "timestamp": r["ts"]} for r in rows}

    # ── Disk Snapshots ─────────────────────────────────────────────────────────────

    def log_disk(self, drive: str, total_bytes: float, free_bytes: float, smart_wear: float = 0, label: str = ""):
        self._conn().execute(
            "INSERT INTO disk_snapshots (drive, label, total_bytes, free_bytes, smart_wear, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (drive, label, total_bytes, free_bytes, smart_wear, time.time()),
        )
        self._commit()

    def latest_disk(self) -> list[dict]:
        rows = self._conn().execute("""
            SELECT drive, label, total_bytes, free_bytes, smart_wear, MAX(timestamp) as ts
            FROM disk_snapshots GROUP BY drive ORDER BY drive
        """).fetchall()
        return [dict(r) for r in rows]

    def disk_history(self, drive: str, limit: int = 30) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM disk_snapshots WHERE drive = ? ORDER BY timestamp DESC LIMIT ?",
            (drive, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Hardware Events ────────────────────────────────────────────────────────────

    def log_hardware(self, device_name: str, device_type: str, serial: str = "", action: str = "detected"):
        self._conn().execute(
            "INSERT INTO hardware_events (device_name, device_type, serial, action, timestamp) VALUES (?, ?, ?, ?, ?)",
            (device_name, device_type, serial, action, time.time()),
        )
        self._commit()

    def query_hardware(self, device_type: str = "", limit: int = 100) -> list[dict]:
        if device_type:
            rows = self._conn().execute(
                "SELECT * FROM hardware_events WHERE device_type = ? ORDER BY timestamp DESC LIMIT ?",
                (device_type, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM hardware_events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── ARP Watch ──────────────────────────────────────────────────────────────────

    def upsert_arp(self, ip: str, mac: str = "", vendor: str = ""):
        now = time.time()
        existing = self._conn().execute("SELECT * FROM arp_watch WHERE ip = ?", (ip,)).fetchone()
        if existing:
            self._conn().execute(
                "UPDATE arp_watch SET mac = ?, vendor = ?, last_seen = ? WHERE ip = ?",
                (mac, vendor, now, ip),
            )
        else:
            self._conn().execute(
                "INSERT INTO arp_watch (ip, mac, vendor, state, first_seen, last_seen) VALUES (?, ?, ?, 'new', ?, ?)",
                (ip, mac, vendor, now, now),
            )
        self._commit()
        self._flush()

    def mark_intruder(self, ip: str):
        self._conn().execute("UPDATE arp_watch SET is_intruder = 1 WHERE ip = ?", (ip,))
        self._commit()
        self._flush()

    def get_arp_entries(self, limit: int = 100) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM arp_watch ORDER BY last_seen DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Troll Targets ──────────────────────────────────────────────────────────────

    def upsert_troll_target(self, ip: str, hostname: str = ""):
        existing = self._conn().execute("SELECT * FROM troll_targets WHERE ip = ?", (ip,)).fetchone()
        if not existing:
            self._conn().execute(
                "INSERT INTO troll_targets (ip, hostname) VALUES (?, ?)", (ip, hostname),
            )
            self._commit()

    def get_troll_targets(self) -> list[dict]:
        rows = self._conn().execute("SELECT * FROM troll_targets ORDER BY last_trolled DESC").fetchall()
        return [dict(r) for r in rows]

    def log_troll(self, ip: str, wallpaper: str = ""):
        self._conn().execute(
            "UPDATE troll_targets SET last_trolled = ?, wallpaper_set = ? WHERE ip = ?",
            (time.time(), wallpaper, ip),
        )
        self._commit()

    def delete_troll_target(self, ip: str):
        self._conn().execute("DELETE FROM troll_targets WHERE ip = ?", (ip,))
        self._commit()

    # ── Forensics ──────────────────────────────────────────────────────────────────

    def log_forensic(self, trigger_source: str, snapshot: dict):
        self._conn().execute(
            "INSERT INTO forensics (timestamp, trigger_source, snapshot_json) VALUES (?, ?, ?)",
            (time.time(), trigger_source, json.dumps(snapshot)),
        )
        self._commit()

    def get_forensics(self, limit: int = 20) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM forensics ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["snapshot"] = json.loads(d.get("snapshot_json", "{}"))
            result.append(d)
        return result

    # ── Achievements ───────────────────────────────────────────────────────────────

    def unlock_achievement(self, name: str, description: str = "", icon: str = "") -> bool:
        try:
            self._conn().execute(
                "INSERT INTO achievements (name, description, icon, unlocked_at) VALUES (?, ?, ?, ?)",
                (name, description, icon, time.time()),
            )
            self._commit()
            self._flush()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_achievements(self) -> list[dict]:
        rows = self._conn().execute("SELECT * FROM achievements ORDER BY unlocked_at DESC").fetchall()
        return [dict(r) for r in rows]

    def is_achievement_unlocked(self, name: str) -> bool:
        row = self._conn().execute("SELECT id FROM achievements WHERE name = ?", (name,)).fetchone()
        return row is not None

    def get_progress(self) -> list[dict]:
        rows = self._conn().execute("SELECT * FROM achievement_progress ORDER BY tracker_name").fetchall()
        return [dict(r) for r in rows]

    def update_progress(self, tracker_name: str, increment: int = 1, target: int = 1):
        existing = self._conn().execute(
            "SELECT id, current_value FROM achievement_progress WHERE tracker_name = ?", (tracker_name,),
        ).fetchone()
        if existing:
            self._conn().execute(
                "UPDATE achievement_progress SET current_value = current_value + ? WHERE tracker_name = ?",
                (increment, tracker_name),
            )
        else:
            self._conn().execute(
                "INSERT INTO achievement_progress (tracker_name, current_value, target_value) VALUES (?, ?, ?)",
                (tracker_name, increment, target),
            )
        self._commit()

    # ── Dreams ─────────────────────────────────────────────────────────────────────

    def save_dream(self, date: str, dream_text: str, raw_event_count: int = 0):
        self._conn().execute(
            "INSERT INTO dreams (date, dream_text, raw_event_count, created) VALUES (?, ?, ?, ?)",
            (date, dream_text, raw_event_count, time.time()),
        )
        self._commit()
        self._flush()

    def get_dreams(self, limit: int = 10) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM dreams ORDER BY created DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def latest_dream(self) -> Optional[dict]:
        row = self._conn().execute("SELECT * FROM dreams ORDER BY created DESC LIMIT 1").fetchone()
        if row:
            return dict(row)
        return None

    # ── Daily Patterns ─────────────────────────────────────────────────────────────

    def record_activity(self, day_of_week: int, hour: int, activity_type: str):
        existing = self._conn().execute(
            "SELECT id, sample_count FROM daily_patterns WHERE day_of_week = ? AND hour = ? AND activity_type = ?",
            (day_of_week, hour, activity_type),
        ).fetchone()
        if existing:
            n = existing["sample_count"] + 1
            self._conn().execute(
                "UPDATE daily_patterns SET sample_count = ?, probability = ? WHERE id = ?",
                (n, min(1.0, n / 14.0), existing["id"]),
            )
        else:
            self._conn().execute(
                "INSERT INTO daily_patterns (day_of_week, hour, activity_type, probability, sample_count) VALUES (?, ?, ?, ?, ?)",
                (day_of_week, hour, activity_type, 0.05, 1),
            )
        self._commit()

    def get_patterns(self, day_of_week: int = -1) -> list[dict]:
        if day_of_week >= 0:
            rows = self._conn().execute(
                "SELECT * FROM daily_patterns WHERE day_of_week = ? AND probability > 0.2 ORDER BY probability DESC",
                (day_of_week,),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM daily_patterns WHERE probability > 0.2 ORDER BY day_of_week, hour"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Notifications ──────────────────────────────────────────────────────────────

    def log_notification(self, channel: str, message: str, target: str = "", success: bool = False):
        self._conn().execute(
            "INSERT INTO notifications (timestamp, channel, message, target, success) VALUES (?, ?, ?, ?, ?)",
            (time.time(), channel, message[:500], target, int(success)),
        )
        self._commit()

    def get_notifications(self, limit: int = 50) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── DNS Block Log ──────────────────────────────────────────────────────────────

    def log_dns_block(self, domain: str, client_ip: str = "", action: str = "blocked"):
        self._conn().execute(
            "INSERT INTO dns_blocked (timestamp, domain, client_ip, action) VALUES (?, ?, ?, ?)",
            (time.time(), domain, client_ip, action),
        )
        self._commit()

    def get_dns_blocks(self, limit: int = 100) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM dns_blocked ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def dns_block_stats(self) -> dict:
        row = self._conn().execute("SELECT COUNT(*) as total, COUNT(DISTINCT domain) as unique_domains FROM dns_blocked").fetchone()
        return dict(row) if row else {"total": 0, "unique_domains": 0}

    # ── Traffic Log ────────────────────────────────────────────────────────────────

    def log_traffic(self, local_ip: str, local_port: int, remote_ip: str, remote_port: int,
                    protocol: str = "TCP", process_name: str = "", state: str = ""):
        self._conn().execute(
            "INSERT INTO traffic_log (timestamp, local_ip, local_port, remote_ip, remote_port, protocol, process_name, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), local_ip, local_port, remote_ip, remote_port, protocol, process_name[:50], state),
        )
        self._commit()

    def query_traffic(self, limit: int = 100, since: float = 0) -> list[dict]:
        if since > 0:
            rows = self._conn().execute(
                "SELECT * FROM traffic_log WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM traffic_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Browser History ─────────────────────────────────────────────────────────────

    def log_browser_visit(self, url: str, title: str = "", browser: str = ""):
        self._conn().execute(
            "INSERT INTO browser_history (timestamp, url, title, browser) VALUES (?, ?, ?, ?)",
            (time.time(), url[:1000], title[:300], browser),
        )
        self._commit()

    def query_browser_history(self, search: str = "", limit: int = 50) -> list[dict]:
        if search:
            rows = self._conn().execute(
                "SELECT * FROM browser_history WHERE url LIKE ? OR title LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{search}%", f"%{search}%", limit),
            ).fetchall()
        else:
            rows = self._conn().execute(
                "SELECT * FROM browser_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Alert Rules ─────────────────────────────────────────────────────────────────

    def save_alert_rule(self, name: str, event_type: str, action_type: str, params: dict = None):
        try:
            self._conn().execute(
                "INSERT INTO alert_rules (name, event_type, action_type, params_json, created) VALUES (?, ?, ?, ?, ?)",
                (name, event_type, action_type, json.dumps(params or {}), time.time()),
            )
            self._commit()
            self._flush()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_alert_rules(self, enabled_only: bool = True) -> list[dict]:
        if enabled_only:
            rows = self._conn().execute("SELECT * FROM alert_rules WHERE enabled = 1 ORDER BY name").fetchall()
        else:
            rows = self._conn().execute("SELECT * FROM alert_rules ORDER BY name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["params"] = json.loads(d.get("params_json", "{}"))
            result.append(d)
        return result

    def toggle_alert_rule(self, name: str, enabled: bool):
        self._conn().execute("UPDATE alert_rules SET enabled = ? WHERE name = ?", (int(enabled), name))
        self._commit()
        self._flush()

    def delete_alert_rule(self, name: str):
        self._conn().execute("DELETE FROM alert_rules WHERE name = ?", (name,))
        self._commit()
        self._flush()

    # ── FTS5 Chat Search ──────────────────────────────────────────────────────────

    def index_chat(self, role: str, content: str):
        """Index a chat message in FTS5 for full-text search."""
        try:
            self._conn().execute(
                "INSERT INTO chat_fts (role, content) VALUES (?, ?)",
                (role, content[:5000]),
            )
            self._commit()
        except Exception:
            pass

    def search_chat(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across chat history via FTS5."""
        try:
            terms = " OR ".join(f'"{w}"' for w in query.split() if len(w) > 2)
            if not terms:
                return []
            rows = self._conn().execute(
                "SELECT rank, role, content FROM chat_fts WHERE chat_fts MATCH ? ORDER BY rank LIMIT ?",
                (terms, limit),
            ).fetchall()
            return [{"rank": r["rank"], "role": r["role"], "content": r["content"][:500]} for r in rows]
        except Exception:
            return []
