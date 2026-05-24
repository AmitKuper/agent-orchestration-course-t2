"""Unit tests for src/agents/judge.py — JudgeAgent scoring prompt and verdict parsing."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import ANY, MagicMock

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
def mock_backend() -> MagicMock:
    """Return a mock backend whose invoke() returns a valid verdict JSON."""
    backend = MagicMock()
    backend.invoke.return_value = json.dumps(_VERDICT)
    return backend


@pytest.fixture
def agent(config, tmp_path, mock_backend) -> JudgeAgent:
    """Return a JudgeAgent with a mock backend."""
    state = ConversationState(tmp_path / "conv.jsonl")
    cost = CostTracker("test")
    return JudgeAgent(
        name="Judge",
        model="claude-test",
        config=config,
        state=state,
        cost_tracker=cost,
        agent_a_name="AgentA",
        agent_b_name="AgentB",
        backend=mock_backend,
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


def test_parse_verdict_computes_total(agent: JudgeAgent):
    """parse_verdict recomputes total from the four criteria."""
    verdict = json.loads(json.dumps(_VERDICT))
    verdict["scores"]["AgentA"]["total"] = 999  # deliberately wrong
    result = agent.parse_verdict(json.dumps(verdict))
    assert result["scores"]["AgentA"]["total"] == 32  # 8+7+9+8


def test_parse_verdict_accepts_capitalised_keys(agent: JudgeAgent):
    """parse_verdict normalises 'Logic' → 'logic' etc."""
    verdict = {
        "winner": "AgentA",
        "scores": {
            "AgentA": {"Logic": 8, "Evidence": 7, "Clarity": 9, "Persuasiveness": 8},
            "AgentB": {"Logic": 6, "Evidence": 7, "Clarity": 7, "Persuasiveness": 6},
        },
        "tiebreaker": None,
        "explanation": "A was better.",
        "factcheck_flags": [],
    }
    result = agent.parse_verdict(json.dumps(verdict))
    assert result["scores"]["AgentA"]["logic"] == 8
    assert result["scores"]["AgentA"]["total"] == 32


def test_parse_verdict_missing_score_key_raises(agent: JudgeAgent):
    """parse_verdict raises ValueError when a criterion is absent."""
    verdict = json.loads(json.dumps(_VERDICT))
    del verdict["scores"]["AgentA"]["logic"]
    with pytest.raises(ValueError, match="logic"):
        agent.parse_verdict(json.dumps(verdict))


def test_parse_verdict_missing_agent_raises(agent: JudgeAgent):
    """parse_verdict raises ValueError when an agent entry is absent."""
    verdict = json.loads(json.dumps(_VERDICT))
    del verdict["scores"]["AgentB"]
    with pytest.raises(ValueError, match="AgentB"):
        agent.parse_verdict(json.dumps(verdict))


def test_parse_verdict_score_out_of_range_raises(agent: JudgeAgent):
    """parse_verdict raises ValueError when a score exceeds 10."""
    verdict = json.loads(json.dumps(_VERDICT))
    verdict["scores"]["AgentA"]["logic"] = 11
    with pytest.raises(ValueError, match="0–10"):
        agent.parse_verdict(json.dumps(verdict))


def test_parse_verdict_missing_winner_raises(agent: JudgeAgent):
    """parse_verdict raises ValueError when winner is absent."""
    verdict = json.loads(json.dumps(_VERDICT))
    del verdict["winner"]
    with pytest.raises(ValueError, match="winner"):
        agent.parse_verdict(json.dumps(verdict))


def test_parse_verdict_defaults_optional_fields(agent: JudgeAgent):
    """parse_verdict fills in tiebreaker and factcheck_flags when absent."""
    verdict = json.loads(json.dumps(_VERDICT))
    del verdict["tiebreaker"]
    del verdict["factcheck_flags"]
    result = agent.parse_verdict(json.dumps(verdict))
    assert result["tiebreaker"] is None
    assert result["factcheck_flags"] == []


def test_invoke_delegates_to_backend(agent: JudgeAgent, mock_backend: MagicMock):
    """_invoke calls backend.invoke with max_tokens=4096 for the judge."""
    agent._invoke("score this debate")

    mock_backend.invoke.assert_called_once_with(
        "Judge", "claude-test", "score this debate", agent.cost_tracker, 4096, None, ANY
    )
