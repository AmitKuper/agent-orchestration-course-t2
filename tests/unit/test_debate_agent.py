"""Unit tests for src/agents/debate.py — DebateAgent prompt building and invocation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, MagicMock

import pytest

from src.agents.debate import DebateAgent
from src.config import DebateConfig
from src.cost import CostTracker
from src.state import ConversationState


@pytest.fixture
def config(tmp_path: Path) -> DebateConfig:
    """Return a minimal DebateConfig."""
    return DebateConfig(topic="test", min_response_len=10, outdir=str(tmp_path))


@pytest.fixture
def state(tmp_path: Path) -> ConversationState:
    """Return an empty ConversationState."""
    return ConversationState(tmp_path / "conv.jsonl")


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


@pytest.fixture
def mock_backend() -> MagicMock:
    """Return a mock backend whose invoke() returns a valid JSONL response."""
    backend = MagicMock()
    backend.invoke.return_value = (
        '{"agent":"AgentA","turn":1,"argument":"test argument here","references":[]}'
    )
    return backend


@pytest.fixture
def agent(config, state, cost, mock_backend) -> DebateAgent:
    """Return a DebateAgent with a mock backend."""
    return DebateAgent(
        name="AgentA",
        model="claude-test",
        config=config,
        state=state,
        cost_tracker=cost,
        position="FOR the motion",
        opponent_name="AgentB",
        backend=mock_backend,
    )


def test_build_prompt_contains_position(agent: DebateAgent):
    """build_prompt includes the agent's assigned position."""
    prompt = agent.build_prompt([], 1, 9)
    assert "FOR the motion" in prompt


def test_build_prompt_contains_turn_number(agent: DebateAgent):
    """build_prompt includes the current turn number."""
    prompt = agent.build_prompt([], 3, 7)
    assert "3" in prompt


def test_build_prompt_contains_turns_remaining(agent: DebateAgent):
    """build_prompt includes the turns remaining count."""
    prompt = agent.build_prompt([], 1, 9)
    assert "9" in prompt


def test_build_prompt_contains_opponent(agent: DebateAgent):
    """build_prompt names the opponent."""
    prompt = agent.build_prompt([], 1, 9)
    assert "AgentB" in prompt


def test_format_history_empty(agent: DebateAgent):
    """_format_history with empty list returns the opening-argument notice."""
    result = agent._format_history([])
    assert "opening" in result.lower()


def test_format_history_includes_arguments(agent: DebateAgent):
    """_format_history includes each turn's argument text."""
    turns = [
        {"agent": "AgentA", "turn": 1, "argument": "First point here."},
        {"agent": "AgentB", "turn": 2, "argument": "Counter argument."},
    ]
    result = agent._format_history(turns)
    assert "First point here." in result
    assert "Counter argument." in result


def test_invoke_delegates_to_backend(agent: DebateAgent, mock_backend: MagicMock):
    """_invoke calls backend.invoke with the correct arguments."""
    result = agent._invoke("some prompt")

    mock_backend.invoke.assert_called_once_with(
        "AgentA", "claude-test", "some prompt", agent.cost_tracker, 2048, None, ANY
    )
    assert result == mock_backend.invoke.return_value
