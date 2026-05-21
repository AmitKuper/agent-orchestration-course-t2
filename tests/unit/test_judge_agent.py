"""Unit tests for src/agents/judge.py — JudgeAgent scoring prompt and verdict parsing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.judge import JudgeAgent
from src.config import DebateConfig
from src.cost import CostTracker
from src.state import ConversationState

_VERDICT = {
    "winner": "AgentA",
    "scores": {
        "AgentA": {
            "logic": 8,
            "evidence": 7,
            "clarity": 9,
            "persuasiveness": 8,
            "total": 32,
        },
        "AgentB": {
            "logic": 6,
            "evidence": 7,
            "clarity": 7,
            "persuasiveness": 6,
            "total": 26,
        },
    },
    "tiebreaker": None,
    "explanation": "AgentA argued more convincingly.",
    "factcheck_flags": [],
}


@pytest.fixture
def config(tmp_path: Path) -> DebateConfig:
    """Return a minimal DebateConfig."""
    return DebateConfig(topic="test", outdir=str(tmp_path))


@pytest.fixture
def agent(config, tmp_path) -> JudgeAgent:
    """Return a JudgeAgent with a patched Anthropic client."""
    state = ConversationState(tmp_path / "conv.jsonl")
    cost = CostTracker("test")
    with patch("anthropic.Anthropic"):
        return JudgeAgent(
            name="Judge",
            model="claude-test",
            config=config,
            state=state,
            cost_tracker=cost,
            agent_a_name="AgentA",
            agent_b_name="AgentB",
        )


def test_build_scoring_prompt_contains_agent_names(agent: JudgeAgent):
    """build_scoring_prompt references both debater names."""
    prompt = agent.build_scoring_prompt([], factcheck_enabled=False)
    assert "AgentA" in prompt
    assert "AgentB" in prompt


def test_build_scoring_prompt_factcheck_disabled(agent: JudgeAgent):
    """Prompt instructs judge to set factcheck_flags to [] when disabled."""
    prompt = agent.build_scoring_prompt([], factcheck_enabled=False)
    assert "[]" in prompt


def test_build_scoring_prompt_factcheck_enabled(agent: JudgeAgent):
    """Prompt includes factcheck instruction when enabled."""
    prompt = agent.build_scoring_prompt([], factcheck_enabled=True)
    assert "fabricated" in prompt.lower() or "factcheck" in prompt.lower()


def test_build_scoring_prompt_includes_transcript(agent: JudgeAgent):
    """Prompt includes turn arguments from the history."""
    turns = [{"turn": 1, "agent": "AgentA", "argument": "my argument text"}]
    prompt = agent.build_scoring_prompt(turns, factcheck_enabled=False)
    assert "my argument text" in prompt


def test_parse_verdict_valid_json(agent: JudgeAgent):
    """parse_verdict returns dict from valid JSON."""
    result = agent.parse_verdict(json.dumps(_VERDICT))
    assert result["winner"] == "AgentA"
    assert result["scores"]["AgentA"]["total"] == 32


def test_parse_verdict_invalid_json_raises(agent: JudgeAgent):
    """parse_verdict raises ValueError on invalid JSON."""
    with pytest.raises(ValueError, match="invalid JSON"):
        agent.parse_verdict("{not json}")


def test_invoke_records_cost(agent: JudgeAgent):
    """_invoke records token usage to the cost tracker."""
    mock_resp = MagicMock()
    mock_resp.content[0].text = json.dumps(_VERDICT)
    mock_resp.usage.input_tokens = 500
    mock_resp.usage.output_tokens = 200
    agent._client.messages.create.return_value = mock_resp

    agent._invoke("score this debate")

    assert agent.cost_tracker.get_run_summary()["total_input_tokens"] == 500
