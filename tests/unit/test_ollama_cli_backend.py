"""Unit tests for OllamaCliBackend (ollama run subprocess)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import OllamaCliBackend
from src.backends._ollama_orchestrator import OllamaOrchestratorBackend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def test_ollama_cli_backend_returns_stdout(cost: CostTracker):
    """OllamaCliBackend.invoke returns stripped stdout from the ollama CLI."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ollama response\n"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        result = OllamaCliBackend().invoke("Agent", "llama3.2", "prompt", cost, 2048)

    assert result == "ollama response"


def test_ollama_cli_backend_uses_model_in_command(cost: CostTracker):
    """OllamaCliBackend.invoke passes the model name to the ollama command."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result) as mock_run:
        OllamaCliBackend().invoke("Agent", "mistral", "prompt", cost, 2048)

    cmd = mock_run.call_args.args[0]
    assert cmd == ["ollama", "run", "mistral"]


def test_ollama_cli_backend_records_zero_tokens(cost: CostTracker):
    """OllamaCliBackend.invoke records zero tokens (CLI gives no usage info)."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "reply"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        OllamaCliBackend().invoke("Agent", "llama3", "prompt", cost, 2048)

    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0


def test_ollama_orchestrator_fallback_backend_type():
    """OllamaOrchestratorBackend falls back to ollama-cli-agents for per-turn calls."""
    assert OllamaOrchestratorBackend.fallback_backend_type == "ollama-cli-agents"


def test_ollama_cli_backend_raises_on_nonzero_exit(cost: CostTracker):
    """OllamaCliBackend.invoke raises RuntimeError when ollama exits non-zero."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "model not found"

    with (
        patch("src.backends._cli.subprocess.run", return_value=mock_result),
        pytest.raises(RuntimeError, match="ollama CLI failed"),
    ):
        OllamaCliBackend().invoke("Agent", "nomodel", "prompt", cost, 2048)
