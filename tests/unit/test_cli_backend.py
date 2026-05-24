"""Unit tests for CliBackend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import CliBackend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def test_cli_backend_returns_stdout(cost: CostTracker):
    """CliBackend.invoke returns stripped stdout from the claude CLI."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '{"agent":"A","turn":1,"argument":"ok","references":[]}\n'

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        result = CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)

    assert result == '{"agent":"A","turn":1,"argument":"ok","references":[]}'


def test_cli_backend_passes_model_flag(cost: CostTracker):
    """CliBackend.invoke includes --model <model> in the claude command."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result) as mock_run:
        CliBackend().invoke("Agent", "claude-sonnet-4-6", "prompt", cost, 2048)

    cmd = mock_run.call_args.args[0]
    assert "--model" in cmd
    assert "claude-sonnet-4-6" in cmd


def test_cli_backend_records_zero_tokens(cost: CostTracker):
    """CliBackend.invoke records zero tokens (not available from CLI)."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)

    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0


def test_cli_backend_raises_on_nonzero_exit(cost: CostTracker):
    """CliBackend.invoke raises RuntimeError when claude CLI exits non-zero."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some error"

    with (
        patch("src.backends._cli.subprocess.run", return_value=mock_result),
        pytest.raises(RuntimeError, match="claude CLI failed"),
    ):
        CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)
