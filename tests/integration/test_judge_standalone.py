"""Integration test: judge runs standalone against a completed JSONL debate file."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.judge import JudgeAgent
from src.config import DebateConfig
from src.cost import CostTracker
from src.state import ConversationState

_TURNS = [
    {"agent": "Alice", "turn": i, "argument": "X" * 60, "references": []}
    for i in range(1, 5)
]

_VERDICT = {
    "winner": "Alice",
    "scores": {
        "Alice": {
            "logic": 9,
            "evidence": 8,
            "clarity": 9,
            "persuasiveness": 9,
            "total": 35,
        },
        "Bob": {
            "logic": 7,
            "evidence": 7,
            "clarity": 7,
            "persuasiveness": 7,
            "total": 28,
        },
    },
    "tiebreaker": None,
    "explanation": "Alice was stronger on every criterion.",
    "factcheck_flags": [],
}


@pytest.fixture
def completed_state(tmp_path: Path) -> ConversationState:
    """Write 4 completed turns to a JSONL file and return the loaded state."""
    path = tmp_path / "conversation.jsonl"
    state = ConversationState(path)
    for turn in _TURNS:
        state.append_turn(turn)
    return ConversationState.load_from_file(path)


@pytest.fixture
def judge_agent(tmp_path: Path, completed_state: ConversationState) -> JudgeAgent:
    """Return a JudgeAgent wired to the completed state."""
    config = DebateConfig(topic="test", outdir=str(tmp_path))
    cost = CostTracker("judge-test")
    with patch("anthropic.Anthropic"):
        return JudgeAgent(
            name="Judge",
            model="claude-test",
            config=config,
            state=completed_state,
            cost_tracker=cost,
            agent_a_name="Alice",
            agent_b_name="Bob",
        )


def test_judge_produces_valid_verdict(
    judge_agent: JudgeAgent, completed_state: ConversationState
):
    """Judge returns a verdict with correct structure from a completed debate."""
    mock_resp = MagicMock()
    mock_resp.content[0].text = json.dumps(_VERDICT)
    mock_resp.usage.input_tokens = 300
    mock_resp.usage.output_tokens = 150
    judge_agent._client.messages.create.return_value = mock_resp

    history = completed_state.get_turns()
    prompt = judge_agent.build_scoring_prompt(history, factcheck_enabled=False)
    response = judge_agent._invoke(prompt)
    verdict = judge_agent.parse_verdict(response)

    assert verdict["winner"] == "Alice"
    assert "Alice" in verdict["scores"]
    assert "Bob" in verdict["scores"]
    assert verdict["scores"]["Alice"]["total"] == 35


def test_judge_winner_has_higher_score(
    judge_agent: JudgeAgent, completed_state: ConversationState
):
    """The declared winner has a higher total score than the loser."""
    mock_resp = MagicMock()
    mock_resp.content[0].text = json.dumps(_VERDICT)
    mock_resp.usage.input_tokens = 300
    mock_resp.usage.output_tokens = 150
    judge_agent._client.messages.create.return_value = mock_resp

    history = completed_state.get_turns()
    prompt = judge_agent.build_scoring_prompt(history, factcheck_enabled=False)
    verdict = judge_agent.parse_verdict(judge_agent._invoke(prompt))

    winner = verdict["winner"]
    loser = "Bob" if winner == "Alice" else "Alice"
    assert verdict["scores"][winner]["total"] > verdict["scores"][loser]["total"]


def test_judge_factcheck_flags_empty_when_disabled(
    judge_agent: JudgeAgent, completed_state: ConversationState
):
    """factcheck_flags is [] when factcheck is disabled."""
    mock_resp = MagicMock()
    mock_resp.content[0].text = json.dumps(_VERDICT)
    mock_resp.usage.input_tokens = 100
    mock_resp.usage.output_tokens = 50
    judge_agent._client.messages.create.return_value = mock_resp

    history = completed_state.get_turns()
    prompt = judge_agent.build_scoring_prompt(history, factcheck_enabled=False)
    verdict = judge_agent.parse_verdict(judge_agent._invoke(prompt))
    assert verdict["factcheck_flags"] == []
