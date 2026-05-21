"""Integration test: interrupted debate resumes from last completed turn."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator import DebateOrchestrator
from src.config import DebateConfig
from src.cost import CostTracker
from src.output import OutputManager
from src.state import ConversationState


def _api_response(agent_name: str, turn: int) -> MagicMock:
    """Build a mock API response for a debate turn."""
    text = json.dumps(
        {
            "agent": agent_name,
            "turn": turn,
            "argument": "B" * 50,
            "references": [],
        }
    )
    m = MagicMock()
    m.content[0].text = text
    m.usage.input_tokens = 80
    m.usage.output_tokens = 40
    return m


def _verdict_response() -> MagicMock:
    """Build a mock judge verdict response."""
    verdict = {
        "winner": "Agent A",
        "scores": {
            "Agent A": {
                "logic": 7,
                "evidence": 7,
                "clarity": 7,
                "persuasiveness": 7,
                "total": 28,
            },
            "Agent B": {
                "logic": 6,
                "evidence": 6,
                "clarity": 6,
                "persuasiveness": 6,
                "total": 24,
            },
        },
        "tiebreaker": None,
        "explanation": "A was better.",
        "factcheck_flags": [],
    }
    m = MagicMock()
    m.content[0].text = json.dumps(verdict)
    m.usage.input_tokens = 150
    m.usage.output_tokens = 80
    return m


@pytest.fixture
def partial_setup(tmp_path: Path):
    """Set up a debate with 2 turns already completed in the JSONL file."""
    config = DebateConfig(
        topic="Cats vs dogs",
        turns=4,
        outdir=str(tmp_path),
        min_response_len=10,
        max_retries=1,
    )
    folder = tmp_path / "run"
    folder.mkdir()
    output = OutputManager(folder)

    state = ConversationState(output.conversation_path)
    state.append_turn(
        {"agent": config.name_a, "turn": 1, "argument": "C" * 50, "references": []}
    )
    state.append_turn(
        {"agent": config.name_b, "turn": 2, "argument": "D" * 50, "references": []}
    )

    cost = CostTracker(folder.name)
    orch = DebateOrchestrator(config, output, state, cost)
    return orch, state, output


def test_resume_starts_from_turn_3(partial_setup):
    """resume_debate continues from turn 3 without re-running turns 1-2."""
    orch, state, output = partial_setup
    cfg = orch.config

    resume_responses = [
        _api_response(cfg.name_a, 3),
        _api_response(cfg.name_b, 4),
        _verdict_response(),
    ]

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("anthropic.Anthropic") as mock_anthropic,
    ):
        mock_anthropic.return_value.messages.create.side_effect = resume_responses

        orch.resume_debate()

    turns = state.get_turns()
    assert len(turns) == 4
    assert turns[2]["turn"] == 3
    assert turns[3]["turn"] == 4


def test_resume_preserves_existing_turns(partial_setup):
    """The first two turns written before interruption are unchanged after resume."""
    orch, state, output = partial_setup
    cfg = orch.config

    existing_arg_1 = state.get_turns()[0]["argument"]
    existing_arg_2 = state.get_turns()[1]["argument"]

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("anthropic.Anthropic") as mock_anthropic,
    ):
        mock_anthropic.return_value.messages.create.side_effect = [
            _api_response(cfg.name_a, 3),
            _api_response(cfg.name_b, 4),
            _verdict_response(),
        ]

        orch.resume_debate()

    turns = state.get_turns()
    assert turns[0]["argument"] == existing_arg_1
    assert turns[1]["argument"] == existing_arg_2


def test_resume_raises_if_already_complete(partial_setup):
    """resume_debate raises RuntimeError when the debate is fully complete."""
    orch, state, _ = partial_setup
    cfg = orch.config
    state.append_turn(
        {"agent": cfg.name_a, "turn": 3, "argument": "x" * 20, "references": []}
    )
    state.append_turn(
        {"agent": cfg.name_b, "turn": 4, "argument": "y" * 20, "references": []}
    )

    with pytest.raises(RuntimeError, match="complete"):
        orch.resume_debate()
