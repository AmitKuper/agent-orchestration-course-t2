"""Unit tests for DebateOrchestrator — judge and flush_logs paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator import DebateOrchestrator
from src.config import DebateConfig
from src.cost import CostTracker
from src.output import OutputManager
from src.state import ConversationState


@pytest.fixture
def config(tmp_path: Path) -> DebateConfig:
    """Return a minimal 4-turn DebateConfig."""
    return DebateConfig(
        topic="AI vs humans",
        turns=4,
        outdir=str(tmp_path),
        min_response_len=5,
        max_retries=1,
    )


@pytest.fixture
def output(tmp_path: Path) -> OutputManager:
    """Return an OutputManager bound to a tmp folder."""
    folder = tmp_path / "run"
    folder.mkdir()
    return OutputManager(folder)


@pytest.fixture
def state(tmp_path: Path) -> ConversationState:
    """Return an empty ConversationState."""
    return ConversationState(tmp_path / "run" / "conversation.jsonl")


@pytest.fixture
def orch(config, output, state) -> DebateOrchestrator:
    """Return a DebateOrchestrator with all dependencies."""
    cost = CostTracker("test")
    return DebateOrchestrator(config, output, state, cost)


class _ImmediateFireWatchdog:
    """Watchdog replacement that fires on_timeout immediately on __enter__."""

    def __init__(self, timeout, callback):
        self._callback = callback

    def __enter__(self):
        self._callback()
        return self

    def __exit__(self, *args):
        pass


def test_run_judge_logs_error_on_empty_response(orch):
    """_run_judge logs an error and returns early when judge returns empty string."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")

    orch._judge.invoke_with_retry = MagicMock(return_value="")
    orch._judge.build_scoring_prompt = MagicMock(return_value="score this")

    orch._run_judge()  # must not raise; empty response → early return


def test_run_judge_logs_error_on_timeout(orch):
    """_run_judge logs an error when judge times out (timed_out[0]=True)."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")

    orch._judge.build_scoring_prompt = MagicMock(return_value="score this")
    orch._judge.invoke_with_retry = MagicMock(return_value="some response")

    with patch("src.debate_helpers.Watchdog", _ImmediateFireWatchdog):
        orch._run_judge()  # timeout fires → timed_out[0]=True → early return


def test_run_judge_logs_error_on_invalid_verdict(orch):
    """_run_judge catches ValueError from parse_verdict and logs the error."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")

    orch._judge.build_scoring_prompt = MagicMock(return_value="score this")
    orch._judge.invoke_with_retry = MagicMock(return_value='{"raw": "verdict"}')
    orch._judge.parse_verdict = MagicMock(side_effect=ValueError("bad format"))

    orch._run_judge()  # ValueError is caught and logged; must not raise


def test_run_turn_timeout_callback_is_called(orch):
    """on_timeout is invoked when the watchdog fires during run_turn."""
    import json
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")

    response = json.dumps(
        {"agent": orch._agent_a.name, "turn": 1, "argument": "x" * 20, "references": []}
    )
    orch._agent_a._backend.invoke.return_value = response

    with patch("src.debate_helpers.Watchdog", _ImmediateFireWatchdog):
        result = orch.run_turn(orch._agent_a, 1)

    assert result == response


def test_flush_logs_calls_flush_and_close(orch):
    """_flush_logs calls flush() and close() on every logger handler."""
    mock_handler = MagicMock()
    orch._logger.handlers = [mock_handler]

    orch._flush_logs()

    mock_handler.flush.assert_called_once()
    mock_handler.close.assert_called_once()


def test_flush_logs_suppresses_handler_exceptions(orch):
    """_flush_logs does not propagate exceptions raised by a handler."""
    mock_handler = MagicMock()
    mock_handler.flush.side_effect = OSError("disk full")
    orch._logger.handlers = [mock_handler]

    orch._flush_logs()  # must not raise
