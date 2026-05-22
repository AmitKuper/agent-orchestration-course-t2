"""Integration test: 4-turn debate runs end-to-end with mocked API calls."""

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
            "Agent A": {
                "logic": 8,
                "evidence": 7,
                "clarity": 8,
                "persuasiveness": 8,
                "total": 31,
            },
            "Agent B": {
                "logic": 6,
                "evidence": 6,
                "clarity": 7,
                "persuasiveness": 6,
                "total": 25,
            },
        },
        "tiebreaker": None,
        "explanation": "Agent A argued better.",
        "factcheck_flags": [],
    }
)


def _debate_response(agent_name: str, turn: int) -> MagicMock:
    """Build a mock API response returning a valid JSONL debate turn."""
    text = json.dumps(
        {
            "agent": agent_name,
            "turn": turn,
            "argument": "A" * 50,
            "references": [],
        }
    )
    m = MagicMock()
    m.content[0].text = text
    m.usage.input_tokens = 100
    m.usage.output_tokens = 50
    return m


def _verdict_response() -> MagicMock:
    """Build a mock API response returning a valid judge verdict."""
    m = MagicMock()
    m.content[0].text = _VERDICT
    m.usage.input_tokens = 200
    m.usage.output_tokens = 100
    return m


@pytest.fixture
def setup(tmp_path: Path):
    """Return orchestrator, state, and output manager for a 4-turn debate."""
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
    return orch, state, output


def test_full_debate_writes_four_turns(setup, tmp_path):
    """A 4-turn debate appends 4 entries to the JSONL conversation file."""
    orch, state, output = setup
    cfg = orch.config

    side_effects = [
        _debate_response(cfg.name_a, 1),
        _debate_response(cfg.name_b, 2),
        _debate_response(cfg.name_a, 3),
        _debate_response(cfg.name_b, 4),
        _verdict_response(),
    ]

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("anthropic.Anthropic") as mock_anthropic,
    ):
        mock_anthropic.return_value.messages.create.side_effect = side_effects

        orch.run_debate()

    turns = state.get_turns()
    assert len(turns) == 4
    assert turns[0]["turn"] == 1
    assert turns[3]["turn"] == 4


def test_full_debate_writes_result_file(setup, tmp_path):
    """A completed debate writes at least one result file to the output folder."""
    orch, state, output = setup
    cfg = orch.config

    side_effects = [
        _debate_response(cfg.name_a, 1),
        _debate_response(cfg.name_b, 2),
        _debate_response(cfg.name_a, 3),
        _debate_response(cfg.name_b, 4),
        _verdict_response(),
    ]

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("anthropic.Anthropic") as mock_anthropic,
    ):
        mock_anthropic.return_value.messages.create.side_effect = side_effects

        orch.run_debate()

    result_files = list(output.folder.glob("result.json"))
    assert len(result_files) == 1
    verdict = json.loads(result_files[0].read_text())
    assert verdict["winner"] == "Agent A"


def test_full_debate_writes_config_file(setup):
    """run_debate saves the config JSON to the output folder."""
    orch, state, output = setup
    cfg = orch.config

    side_effects = [
        _debate_response(cfg.name_a, 1),
        _debate_response(cfg.name_b, 2),
        _debate_response(cfg.name_a, 3),
        _debate_response(cfg.name_b, 4),
        _verdict_response(),
    ]

    with (
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
        patch("anthropic.Anthropic") as mock_anthropic,
    ):
        mock_anthropic.return_value.messages.create.side_effect = side_effects

        orch.run_debate()

    assert output.config_path.exists()
