"""
Smoke tests for KaiAssistant — mocks Ollama so no LLM required.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kai_agent.assistant import KaiAssistant, parse_args


@pytest.fixture
def assistant(tmp_path):
    """Create a KaiAssistant with mocked Ollama client."""
    workspace = tmp_path / "kai_test"
    a = KaiAssistant(model="test-model", workspace=workspace)
    # Mock the client so no network calls
    a.client.chat = MagicMock(return_value="Mocked Kai response")
    a.client.list_models = MagicMock(return_value=["test-model"])
    return a


class TestInstantiation:
    def test_assistant_creates_workspace(self, tmp_path):
        ws = tmp_path / "new_workspace"
        a = KaiAssistant(model="test-model", workspace=ws)
        assert ws.exists()
        assert (ws / "memory").exists()
        assert (ws / "logs").exists()

    def test_assistant_has_all_subsystems(self, assistant):
        assert assistant.memory is not None
        assert assistant.tools is not None
        assert assistant.emotions is not None
        assert assistant.learning is not None
        assert assistant.skills_system is not None
        assert assistant.autonomous_learner is not None
        assert assistant.web_automation is not None
        assert assistant.kali is not None
        assert assistant.hardware_integration is not None


class TestAskMethod:
    @patch("kai_agent.assistant.KaiAssistant._maybe_short_circuit_tool_result", return_value=None)
    @patch("kai_agent.smart_router.SmartRouter.route", return_value={"handler": "llm"})
    def test_ask_returns_response(self, mock_router_route, mock_short_circuit, assistant):
        reply = asyncio.run(assistant.ask("Hello Kai"))
        assert reply == "Mocked Kai response"
        assistant.client.chat.assert_called_once()
        mock_short_circuit.assert_called_once()
        mock_router_route.assert_called_once()

    def test_ask_updates_history(self, assistant):
        initial_len = len(assistant.history)
        asyncio.run(assistant.ask("Test question"))
        assert len(assistant.history) == initial_len + 2  # user + assistant

    def test_ask_limits_history(self, assistant):
        # build_messages caps the returned context, but ask() doesn't truncate history
        # It returns: system + up to max_history*2 history + 1 current prompt
        assistant.max_history = 4
        for i in range(10):
            asyncio.run(assistant.ask(f"Question {i}"))
        msgs = assistant.build_messages("test")
        assert len(msgs) <= 2 + (assistant.max_history * 2)

    def test_build_messages_limits_context(self, assistant):
        assistant.max_history = 2
        for i in range(5):
            asyncio.run(assistant.ask(f"Question {i}"))
        msgs = assistant.build_messages("final")
        # system + up to 2 user + 2 assistant + 1 current prompt
        assert len(msgs) <= 6


class TestMemoryCommands:
    def test_remember_returns_dict(self, assistant):
        result = assistant.remember("test note about Python")
        assert isinstance(result, dict)
        assert "content" in result or "note" in result

    def test_recall_via_memory(self, assistant):
        assistant.memory.save_note("Python is a programming language", category="test")
        notes = assistant.memory.load_notes()
        contents = [n.get("content", "") for n in notes]
        assert any("Python" in c for c in contents)


class TestToolCommands:
    def test_capabilities_command(self, assistant):
        result = asyncio.run(assistant.ask("/capabilities"))
        assert len(result) > 0

    def test_status_command(self, assistant):
        result = asyncio.run(assistant.ask("/status"))
        assert "status" in result.lower() or "Kai" in result


class TestDesktopTools:
    def test_desktop_tools_instantiated(self, assistant):
        assert assistant.tools is not None
        # Check it has expected methods
        assert hasattr(assistant.tools, "list_capabilities")
        assert hasattr(assistant.tools, "search_web")

    def test_list_capabilities_returns_string(self, assistant):
        caps = assistant.tools.list_capabilities()
        assert isinstance(caps, str)


class TestEmotionalState:
    def test_emotions_load(self, assistant):
        assert assistant.emotions is not None

    def test_emotions_have_state(self, assistant):
        state = assistant.emotions.get_state()
        assert isinstance(state, dict)


class TestLearningSystem:
    def test_learning_system_loads(self, assistant):
        assert assistant.learning is not None

    def test_skills_system_loads(self, assistant):
        assert assistant.skills_system is not None


class TestParseArgs:
    def test_parse_args_defaults(self):
        with patch.object(sys, "argv", ["kai"]):
            args = parse_args()
        assert args.model == "sam860/dolphin3-llama3.2:3b"

    def test_parse_args_custom_model(self):
        with patch.object(sys, "argv", ["kai", "--model", "deepseek-r1:1.5b"]):
            args = parse_args()
        assert args.model == "deepseek-r1:1.5b"


class TestConversationSummary:
    def test_summary_loads(self, assistant):
        assert assistant.conversation_summary is not None
        assert isinstance(assistant.conversation_summary, str)

    def test_summary_persists(self, assistant):
        summary = assistant.conversation_summary
        # Create new assistant with same workspace
        a2 = KaiAssistant(model="test-model", workspace=assistant.workspace)
        assert a2.conversation_summary == summary
