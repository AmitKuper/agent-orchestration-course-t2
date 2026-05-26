"""Integration test: run_debate saves config file to the output folder."""

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

_VERDICT = json.dumps(
    {
        "winner": "Agent A",
        "scores": {
            "Agent A": {"logic": 8, "evidence": 7, "clarity": 8, "persuasiveness": 8, "total": 31},
            "Agent B": {"logic": 6, "evidence": 6, "clarity": 7, "persuasiveness": 6, "total": 25},
        },
        "tiebreaker": None,
        "explanation": "Agent A argued better.",
        "factcheck_flags": [],
    }
)


def _debate_response(agent_name: str, turn: int) -> MagicMock:
    """Build a mock API response for a debate turn."""
    text = json.dumps({"agent": agent_name, "turn": turn, "argument": "A" * 50, "references": []})
    m = MagicMock()
    m.content[0].text = text
    m.usage.input_tokens = 100
    m.usage.output_tokens = 50
    return m


def _verdict_response() -> MagicMock:
    """Build a mock judge verdict response."""
    m = MagicMock()
    m.content[0].text = _VERDICT
    m.usage.input_tokens = 200
    m.usage.output_tokens = 100
    return m


@pytest.fixture
def setup(tmp_path: Path):
    """Return orchestrator and output manager for a 4-turn debate."""
    config = DebateConfig(
        topic="AI will replace humans",
        turns=4,
        outdir=str(tmp_path),
        min_response_len=10,
        max_retries=1,
    )
    folder = tmp_path / "run"
    folder.mkdir()
    output = OutputManager(folder)
    state = ConversationState(output.conversation_path)
    cost = CostTracker(folder.name)
    orch = DebateOrchestrator(config, output, state, cost)
    return orch, output


def test_full_debate_writes_config_file(setup):
    """run_debate saves the config JSON to the output folder."""
    orch, output = setup
    cfg = orch.config

    side_effects = [
        _debate_response(cfg.name_a, 1),
        _debate_response(cfg.name_b, 2),
        _debate_response(cfg.name_a, 3),
        _debate_response(cfg.name_b, 4),
        _verdict_response(),
    ]

    mock_mod = MagicMock()
    mock_mod.Anthropic.return_value.messages.create.side_effect = side_effects

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("src.backends._api._get_anthropic", return_value=mock_mod),
        patch("src.shared.gatekeeper.time.sleep"),
    ):
        orch.run_debate()

    assert output.config_path.exists()
