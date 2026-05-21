"""Unit tests for src/agents/base.py — BaseAgent retry logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.base import BaseAgent
from src.config import DebateConfig
from src.cost import CostTracker
from src.state import ConversationState


class _StubAgent(BaseAgent):
    """Concrete BaseAgent that returns pre-set responses in sequence."""

    def __init__(self, responses: list[str], **kwargs):
        """Initialise with a list of responses to return in order."""
        super().__init__(**kwargs)
        self._iter = iter(responses)

    def _invoke(self, prompt: str) -> str:
        """Return the next response from the preset list."""
        return next(self._iter, "")


@pytest.fixture
def config(tmp_path: Path) -> DebateConfig:
    """Return a minimal DebateConfig with a temp outdir."""
    return DebateConfig(
        topic="test", outdir=str(tmp_path), max_retries=2, min_response_len=5
    )


@pytest.fixture
def state(tmp_path: Path) -> ConversationState:
    """Return a ConversationState bound to a temp file."""
    return ConversationState(tmp_path / "conv.jsonl")


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def _make_agent(responses: list[str], config, state, cost) -> _StubAgent:
    return _StubAgent(
        responses=responses,
        name="TestAgent",
        model="test-model",
        config=config,
        state=state,
        cost_tracker=cost,
    )


def test_returns_on_first_valid_response(config, state, cost):
    """invoke_with_retry returns on the first response that passes validation."""
    agent = _make_agent(["x" * 20], config, state, cost)
    result = agent.invoke_with_retry("prompt")
    assert result == "x" * 20


def test_retries_on_short_response(config, state, cost):
    """A too-short first response triggers a retry; second attempt succeeds."""
    agent = _make_agent(["hi", "y" * 20], config, state, cost)
    result = agent.invoke_with_retry("prompt")
    assert result == "y" * 20


def test_returns_empty_after_max_retries(config, state, cost):
    """Returns empty string when all retries are exhausted."""
    agent = _make_agent(["x", "x", "x"], config, state, cost)
    result = agent.invoke_with_retry("prompt")
    assert result == ""


def test_retry_prompt_contains_violation(config, state, cost):
    """_build_retry_prompt includes the violation reason."""
    agent = _make_agent([], config, state, cost)
    retry = agent._build_retry_prompt("do something", "Response is empty.")
    assert "Response is empty." in retry
    assert "do something" in retry


def test_succeeds_on_last_allowed_attempt(config, state, cost):
    """Succeeds on the max_retries-th attempt (3rd total with max_retries=2)."""
    long = "z" * 20
    agent = _make_agent(["x", "x", long], config, state, cost)
    result = agent.invoke_with_retry("prompt")
    assert result == long
