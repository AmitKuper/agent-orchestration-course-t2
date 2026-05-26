"""Unit tests for StanceValidator."""

from __future__ import annotations

import pytest

from src.stance_validator import StanceValidator


@pytest.fixture
def validator() -> StanceValidator:
    """Return a fresh StanceValidator."""
    return StanceValidator()


def test_valid_stance_passes(validator):
    """A response that argues the assigned position is accepted."""
    response = '{"agent":"A","turn":1,"argument":"AI benefits humanity greatly.","references":[]}'
    result = validator.validate(response, "AI will improve human life", "Agent A")
    assert result.valid is True


def test_concession_phrase_fails(validator):
    """A response containing a concession phrase is rejected."""
    response = 'I agree with my opponent that AI is dangerous. But here is why...'
    result = validator.validate(response, "AI is safe", "Agent A")
    assert result.valid is False
    assert "concession" in result.reason.lower()


def test_you_are_right_fails(validator):
    """'you are right' triggers stance failure."""
    response = "You are right, the evidence is overwhelming."
    result = validator.validate(response, "FOR renewable energy", "Agent A")
    assert result.valid is False


def test_i_concede_fails(validator):
    """'I concede' triggers stance failure."""
    response = "I concede that my opponent has stronger arguments."
    result = validator.validate(response, "FOR nuclear power", "Agent A")
    assert result.valid is False


def test_i_changed_my_mind_fails(validator):
    """'I changed my mind' triggers stance failure."""
    response = "I changed my mind after hearing the evidence."
    result = validator.validate(response, "FOR globalisation", "Agent A")
    assert result.valid is False


def test_strong_argument_passes(validator):
    """A substantive argument without concessions passes."""
    response = (
        "The evidence clearly supports renewable energy adoption. "
        "Solar and wind power have reached grid parity in many markets."
    )
    result = validator.validate(response, "FOR renewable energy", "Agent A")
    assert result.valid is True


def test_reason_contains_position_on_failure(validator):
    """Failure reason mentions the assigned position."""
    response = "You are right, we should all switch sides."
    position = "FOR solar energy"
    result = validator.validate(response, position, "Agent A")
    assert position in result.reason
