"""Tests for Kai Web UI Flask routes with mocked KaiCompanion."""

import json
from unittest.mock import MagicMock, patch

import pytest
import kai_web_ui


@pytest.fixture
def client():
    kai_web_ui._kai_instance = None
    kai_web_ui.app.config["TESTING"] = True
    with kai_web_ui.app.test_client() as c:
        yield c


def _mock_kai():
    """Return a mocked KaiCompanion with all required attributes."""
    kai = MagicMock()
    kai.provider = "groq"
    kai.model = "llama-3.3-70b"
    kai.ask.return_value = "Mocked reply"
    kai._ctos = MagicMock()
    kai._ctos.build_netmap.return_value = {"nodes": [], "edges": []}
    kai._ctos.get_scan_status.return_value = {"running": False, "done": True, "count": 0}
    kai._ctos.start_scan.return_value = None
    kai._ctos.db = MagicMock()
    kai._ctos.db.all_devices.return_value = []
    kai._ctos.db.get_urban_events.return_value = []
    kai._ctos.db.query_journal.return_value = []
    kai._ctos.breach.return_value = {"ip": "192.168.1.1", "type": "router"}
    kai._last_structured = None
    kai._chess_advice_queue = MagicMock()
    kai._chess_advice_queue.empty.return_value = True
    kai._twin = MagicMock()
    kai._twin.status.return_value = {"provider": "groq", "model": "llama-3.3-70b"}
    kai._ghost_protocol = MagicMock()
    kai._ghost_protocol.analyze_wifi.return_value = {"status": "ok"}
    kai._clipboard = MagicMock()
    kai._clipboard.get_history.return_value = []
    kai._dns = MagicMock()
    kai._dns.get_history.return_value = []
    kai._dns.get_top_domains.return_value = []
    kai._thermal = MagicMock()
    kai._thermal.get_current.return_value = {}
    kai._disk = MagicMock()
    kai._disk.get_status.return_value = []
    kai._disk.predict_full.return_value = {"days_remaining": 365}
    kai._port_whisperer = MagicMock()
    kai._port_whisperer.get_ports.return_value = []
    kai._bouncer = MagicMock()
    kai._bouncer.get_entries.return_value = []
    kai._bouncer.get_intruders.return_value = []
    kai._troll = MagicMock()
    kai._troll.list_targets.return_value = []
    kai._troll.add_target.return_value = None
    kai._troll.troll_all.return_value = {"status": "ok"}
    kai._bloodhound = MagicMock()
    kai._bloodhound.get_latest.return_value = []
    kai._achievements = MagicMock()
    kai._achievements.get_all.return_value = []
    kai._dreams = MagicMock()
    kai._dreams.get_latest.return_value = {}
    kai._dreams.get_dreams.return_value = []
    kai._butler = MagicMock()
    kai._butler.get_patterns.return_value = []
    kai._butler.suggest_routine.return_value = []
    kai._precog = MagicMock()
    kai._precog.predict.return_value = []
    kai._precog.most_common.return_value = []
    return kai


class TestCoreRoutes:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"K//AI" in resp.data

    def test_ask_returns_reply(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.post("/ask", json={"message": "hello"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data
        assert data["reply"] == "Mocked reply"

    def test_ask_empty_message(self, client):
        resp = client.post("/ask", json={"message": ""})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "No message" in data["reply"]

    def test_status(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["provider"] == "groq"


class TestNetmapRoutes:
    def test_netmap_get(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/netmap")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "nodes" in data

    def test_netmap_scan(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.post("/netmap/scan")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_netmap_scan_status(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/netmap/scan/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "running" in data
        assert "done" in data
        assert "count" in data

    def test_breach_dossier(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/breach/192.168.1.1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ip"] == "192.168.1.1"


class TestDataRoutes:
    def test_last_structured(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/last_structured")
        assert resp.status_code == 200

    def test_urban_timeline(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/urban/timeline")
        assert resp.status_code == 200

    def test_clipboard_history(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/clipboard/history")
        assert resp.status_code == 200

    def test_dns_history(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/dns/history")
        assert resp.status_code == 200

    def test_thermal_current(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/thermal/current")
        assert resp.status_code == 200

    def test_disk_status(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/disk/status")
        assert resp.status_code == 200

    def test_achievements_all(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.get("/achievements/all")
        assert resp.status_code == 200

    def test_hunt(self, client):
        kai = _mock_kai()
        kai._handle_hunt.return_value = "Hunt complete"
        with patch("kai_web_ui.get_kai", return_value=kai):
            resp = client.post("/hunt", json={"target": "192.168.1.10"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data

    def test_workflow(self, client):
        kai = _mock_kai()
        kai._handle_workflow.return_value = "Workflow complete"
        with patch("kai_web_ui.get_kai", return_value=kai):
            resp = client.post("/workflow", json={"target": "192.168.1.10", "workflow": "web"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data


class TestRebuild:
    def test_rebuild_works(self, client):
        with patch("kai_web_ui.get_kai", return_value=_mock_kai()):
            resp = client.post("/rebuild")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ok" in data
