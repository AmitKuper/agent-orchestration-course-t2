"""Integration test: resume_debate raises when debate is already complete."""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator import DebateOrchestrator
from src.config import DebateConfig
from src.cost import CostTracker
from src.output import OutputManager
from src.state import ConversationState


@pytest.fixture
def complete_setup(tmp_path: Path):
    """Set up a fully-completed 4-turn debate."""
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
    state.append_turn({"agent": config.name_a, "turn": 1, "argument": "C" * 50, "references": []})
    state.append_turn({"agent": config.name_b, "turn": 2, "argument": "D" * 50, "references": []})
    state.append_turn({"agent": config.name_a, "turn": 3, "argument": "x" * 20, "references": []})
    state.append_turn({"agent": config.name_b, "turn": 4, "argument": "y" * 20, "references": []})
    cost = CostTracker(folder.name)
    orch = DebateOrchestrator(config, output, state, cost)
    return orch


def test_resume_raises_if_already_complete(complete_setup):
    """resume_debate raises RuntimeError when the debate is fully complete."""
    orch = complete_setup
    with pytest.raises(RuntimeError, match="complete"):
        orch.resume_debate()
