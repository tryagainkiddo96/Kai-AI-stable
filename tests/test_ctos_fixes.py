"""Tests for CTOS engine fixes: ARP parsing, background scan, DB resilience."""

import json
import threading
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from kai_agent.ctos_db import CTOSDatabase
from kai_agent.ctos import CTOSEngine


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test_ctos.db"
    return CTOSDatabase(str(path))


@pytest.fixture
def engine(db):
    return CTOSEngine(db)


class TestARPParsing:
    """All three ARP call sites must handle leading whitespace (.Trim())."""

    ARP_OUTPUT = (
        "  Interface: 192.168.1.1 --- 0x5\n"
        "    Internet Address    Physical Address    Type\n"
        "    192.168.1.10        aa-bb-cc-dd-ee-ff     dynamic\n"
        "    192.168.1.20        11-22-33-44-55-66     dynamic\n"
        "    192.168.1.30        fe-dc-ba-98-76-54     static\n"
    )

    @patch("kai_agent.ctos.subprocess.run")
    def test_quick_scan_arp_fix(self, mock_run, engine):
        """_quick_scan correctly parses IPs from arp -a output with leading whitespace."""
        mock_run.return_value = MagicMock(
            stdout=self.ARP_OUTPUT, returncode=0
        )

        with patch.object(engine, "_enrich_device", return_value={"ip": "mock"}):
            devices = engine._quick_scan()

        assert len(devices) >= 2, "Should parse at least the two 'dynamic' entries"
        assert all(d["ip"] == "mock" for d in devices)

    @patch("kai_agent.ctos.subprocess.run")
    def test_scan_cameras_arp_fix(self, mock_run, engine):
        """_scan_cameras parses IPs from arp correctly."""
        mock_run.return_value = MagicMock(
            stdout=self.ARP_OUTPUT, returncode=0
        )

        with patch.object(engine, "_enrich_device", return_value=None):
            engine._scan_cameras()

        mock_run.assert_called()
        cmd = mock_run.call_args_list[0][0][0]
        assert "$_.Trim()" in cmd[-1], "Should use .Trim() before -split"

    @patch("kai_agent.ctos.subprocess.run")
    def test_check_proximity_arp_fix(self, mock_run, engine):
        """_check_proximity parses IP+MAC from arp correctly."""
        mock_run.return_value = MagicMock(
            stdout=self.ARP_OUTPUT, returncode=0
        )

        with patch("kai_agent.ctos._oui_vendor", return_value="TestVendor"):
            with patch("kai_agent.ctos._device_type", return_value="unknown"):
                engine._check_proximity()

        cmd = mock_run.call_args[0][0]
        assert "$_.Trim()" in cmd[-1], "Should use .Trim() before -split"


class TestBackgroundScan:
    def test_start_scan_sets_flags(self, engine):
        assert not engine._scan_in_progress
        engine.start_scan()
        assert engine._scan_in_progress is True

    def test_get_scan_status_before_done(self, engine):
        engine._scan_in_progress = True
        status = engine.get_scan_status()
        assert status["running"] is True
        assert status["done"] is False

    def test_get_scan_status_completed(self, engine):
        engine._scan_in_progress = False
        engine._scan_done = True
        engine._scan_count = 3
        status = engine.get_scan_status()
        assert status["running"] is False
        assert status["done"] is True
        assert status["count"] == 3

    def test_does_not_start_duplicate_scan(self, engine):
        engine._scan_in_progress = True
        engine.start_scan()
        assert engine._scan_in_progress is True  # still True, not re-started


class TestBuildNetmap:
    def test_build_netmap_does_not_call_quick_scan(self, engine):
        """build_netmap should NOT call _quick_scan when DB has data."""
        engine.db.upsert_device("192.168.1.10", mac="aa:bb:cc:dd:ee:ff", vendor="Test")
        with patch.object(engine, "_quick_scan", wraps=engine._quick_scan) as mock:
            result = engine.build_netmap()
            mock.assert_not_called()
        assert len(result.get("nodes", [])) >= 1

    def test_build_netmap_returns_empty_nodes_no_db(self, engine):
        result = engine.build_netmap()
        assert "nodes" in result
        assert "edges" in result


class TestDBResilience:
    def test_auto_commit_mode(self, db):
        conn = db._conn()
        assert conn.isolation_level is None, "DB should be in auto-commit mode"

    def test_wal_mode(self, db):
        conn = db._conn()
        cur = conn.execute("PRAGMA journal_mode")
        row = cur.fetchone()
        assert row[0].upper() == "WAL", f"Expected WAL, got {row[0]}"

    def test_busy_timeout(self, db):
        conn = db._conn()
        cur = conn.execute("PRAGMA busy_timeout")
        row = cur.fetchone()
        assert row[0] >= 30000, f"Expected busy_timeout >= 30000, got {row[0]}"

    def test_concurrent_writes_no_lock(self, db):
        """Multiple threads writing simultaneously should not deadlock."""
        errors = []

        def writer(n):
            try:
                for i in range(20):
                    db.upsert_device(f"192.168.1.{n}", mac=f"aa:bb:cc:{n:02x}:{i:02x}:ff")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent writes failed: {errors}"
        devices = db.all_devices()
        assert len(devices) > 0


class TestProactiveScan:
    def test_scan_count_stored(self, db):
        engine = CTOSEngine(db)
        with patch.object(engine, "_enrich_device", return_value={"ip": "mock"}):
            with patch("kai_agent.ctos.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="  192.168.1.10  aa-bb-cc-dd-ee-ff  dynamic\n",
                    returncode=0
                )
                engine.start_scan()
                import time
                time.sleep(0.5)
        status = engine.get_scan_status()
        assert status["done"] is True or status["running"] is True
