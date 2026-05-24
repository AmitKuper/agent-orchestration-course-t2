"""Unit tests for DebateOrchestrator — topic, agents, and turn logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator import DebateOrchestrator, InvalidTopicError
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


def _fake_turn(agent_name: str, turn: int) -> str:
    return json.dumps(
        {"agent": agent_name, "turn": turn, "argument": "x" * 20, "references": []}
    )


def test_validate_topic_returns_positions(orch):
    """validate_topic returns (position_a, position_b) on a valid topic."""
    with patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")):
        pos_a, pos_b = orch.validate_topic("test topic")
    assert pos_a == "FOR"
    assert pos_b == "AGAINST"


def test_validate_topic_raises_on_invalid(orch):
    """validate_topic re-raises InvalidTopicError from the helper."""
    with (
        patch("orchestrator.validate_topic", side_effect=InvalidTopicError("bad")),
        pytest.raises(InvalidTopicError),
    ):
        orch.validate_topic("bad topic")


def test_initialize_agents_sets_agents(orch):
    """initialize_agents creates _agent_a, _agent_b and _judge."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")
    assert orch._agent_a is not None
    assert orch._agent_b is not None
    assert orch._judge is not None


def test_initialize_agents_assigns_positions(orch):
    """Agent A gets position_a, Agent B gets position_b."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")
    assert orch._agent_a.position == "FOR"
    assert orch._agent_b.position == "AGAINST"


def test_run_turn_returns_response(orch):
    """run_turn returns the agent's JSONL response when it is valid."""
    mock_backend = MagicMock()
    with patch("orchestrator.make_backend", return_value=mock_backend):
        orch.initialize_agents("FOR", "AGAINST")

    response = _fake_turn("AgentA", 1)
    mock_backend.invoke.return_value = response
    result = orch.run_turn(orch._agent_a, 1)
    assert result == response


def test_run_turn_returns_empty_on_bad_json(orch):
    """run_turn returns empty string when the agent returns invalid JSON."""
    mock_backend = MagicMock()
    with patch("orchestrator.make_backend", return_value=mock_backend):
        orch.initialize_agents("FOR", "AGAINST")

    mock_backend.invoke.return_value = "not json at all here!"
    result = orch.run_turn(orch._agent_a, 1)
    assert result == ""


def test_run_turns_alternates_ab(orch):
    """_run_turns assigns even turns to B and odd turns to A."""
    with patch("orchestrator.make_backend"):
        orch.initialize_agents("FOR", "AGAINST")

    calls = []

    def fake_run_turn(agent, turn):
        calls.append((agent.name, turn))
        return _fake_turn(agent.name, turn)

    orch.run_turn = fake_run_turn
    orch._run_turns(1)

    agents_in_order = [name for name, _ in calls]
    assert agents_in_order[0] == orch.config.name_a
    assert agents_in_order[1] == orch.config.name_b


def test_resume_raises_if_complete(orch, state):
    """resume_debate raises RuntimeError if the debate is already complete."""
    for i in range(1, 5):
        state.append_turn({"agent": "A", "turn": i, "argument": "x", "references": []})
    with pytest.raises(RuntimeError, match="complete"):
        orch.resume_debate()
