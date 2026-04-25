import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    workspace = Path(tempfile.mkdtemp(prefix="kai_test_"))
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def mock_ollama_config(monkeypatch):
    """Set minimal Ollama config for testing without actual Ollama."""
    monkeypatch.setenv("KAI_MODEL", "dummy-model")
    monkeypatch.setenv("KAI_PRIMARY_MODEL_TIMEOUT", "1")
    monkeypatch.setenv("KAI_FALLBACK_MODEL_TIMEOUT", "1")
    monkeypatch.setenv("KAI_DISABLE_WEB_FALLBACK", "1")
    monkeypatch.setenv("KAI_DISABLE_BROWSER_FALLBACK", "1")
