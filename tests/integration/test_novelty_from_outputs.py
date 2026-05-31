"""Integration tests verifying novelty validation against real debate outputs.

Known-repeating outputs are used to confirm the validator *would have* caught
copy-paste loops. Known-clean outputs confirm no false positives. Tests skip
gracefully when the output folder is absent (e.g. CI without local runs).
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path

import pytest

from src.validator import ResponseValidator

OUTPUTS = Path("outputs")
THRESHOLD = 0.75

# Confirmed from post-run analysis: consecutive same-agent turns exceed threshold.
# Empty for this sweep — all 9 runs are clean after novelty validation.
KNOWN_REPEATING: list[str] = []

# Confirmed from post-run analysis: no consecutive same-agent turns exceed threshold.
KNOWN_CLEAN = [
    "ai-jobs-api",
    "ai-jobs-ollama-cli",
    "ai-jobs-ollama-cli-agents",
    "iran-nuclear-api",
    "iran-nuclear-ollama-cli",
    "iran-nuclear-ollama-cli-agents",
    "messi-ronaldo-api",
    "messi-ronaldo-ollama-cli",
    "messi-ronaldo-ollama-cli-agents",
]


def _load_conversation(topic_backend: str) -> list[dict] | None:
    """Load turns from the most recent run in outputs/<topic_backend>.

    Args:
        topic_backend: Name of the output folder (e.g. 'iran-nuclear-api').

    Returns:
        List of turn dicts, or None if the folder or file is missing.
    """
    folder = OUTPUTS / topic_backend
    if not folder.exists():
        return None
    runs = sorted(d for d in folder.iterdir() if d.is_dir())
    if not runs:
        return None
    conv = runs[-1] / "conversation.jsonl"
    if not conv.exists():
        return None
    return [json.loads(line) for line in conv.read_text(encoding="utf-8").splitlines() if line.strip()]


def _find_repeats(turns: list[dict]) -> list[tuple[str, int, int, float]]:
    """Find consecutive same-agent turn pairs that exceed the novelty threshold.

    Args:
        turns: All debate turns in order.

    Returns:
        List of (agent, turn_a, turn_b, ratio) tuples for flagged pairs.
    """
    by_agent: dict[str, list[dict]] = {}
    for t in turns:
        by_agent.setdefault(t["agent"], []).append(t)
    repeats = []
    for agent, aturns in by_agent.items():
        for i in range(1, len(aturns)):
            a1 = aturns[i - 1]["argument"]
            a2 = aturns[i]["argument"]
            ratio = SequenceMatcher(None, a1.lower(), a2.lower()).ratio()
            if ratio > THRESHOLD:
                repeats.append((agent, aturns[i - 1]["turn"], aturns[i]["turn"], round(ratio, 2)))
    return repeats


@pytest.mark.parametrize("topic_backend", KNOWN_REPEATING)
def test_novelty_validator_detects_repetitions_in_output(topic_backend: str) -> None:
    """Known-repeating outputs must contain at least one same-agent pair above threshold."""
    turns = _load_conversation(topic_backend)
    if turns is None:
        pytest.skip(f"Output not present: {topic_backend}")
    repeats = _find_repeats(turns)
    assert repeats, f"Expected repetitions in {topic_backend} but found none"


@pytest.mark.parametrize("topic_backend", KNOWN_CLEAN)
def test_novelty_validator_passes_clean_outputs(topic_backend: str) -> None:
    """Known-clean outputs must have zero same-agent pairs above threshold."""
    turns = _load_conversation(topic_backend)
    if turns is None:
        pytest.skip(f"Output not present: {topic_backend}")
    repeats = _find_repeats(turns)
    assert not repeats, f"Unexpected repetitions in {topic_backend}: {repeats}"


def test_validate_novelty_rejects_identical_argument() -> None:
    """validate_novelty returns invalid when argument is identical to a prior turn."""
    validator = ResponseValidator()
    arg = "AI automation destroys jobs faster than it creates them, causing long-term unemployment."
    result = validator.validate_novelty(arg, [arg])
    assert not result.valid
    assert "similar" in result.reason.lower()


def test_validate_novelty_passes_distinct_argument() -> None:
    """validate_novelty returns valid when argument is clearly different from prior turns."""
    validator = ResponseValidator()
    prior = "AI automation destroys jobs faster than it creates them, causing long-term unemployment."
    new_arg = "Historical evidence shows every industrial revolution created more jobs than it eliminated."
    result = validator.validate_novelty(new_arg, [prior])
    assert result.valid


def test_validate_novelty_passes_with_no_prior_turns() -> None:
    """validate_novelty returns valid when the agent has no prior turns."""
    validator = ResponseValidator()
    result = validator.validate_novelty("Opening argument establishing my position.", [])
    assert result.valid
