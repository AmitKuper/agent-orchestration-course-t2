"""Unit-style tests for ResponseValidator.validate_novelty."""

from __future__ import annotations

from src.validator import ResponseValidator


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
