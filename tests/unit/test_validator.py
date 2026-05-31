"""Unit tests for ResponseValidator base checks and validate_json/validate_novelty."""

from __future__ import annotations

import json

import pytest

from src.validator import ResponseValidator


@pytest.fixture
def v() -> ResponseValidator:
    """Return a fresh ResponseValidator for each test."""
    return ResponseValidator()


def _valid_turn(agent: str = "Agent A", turn: int = 1, arg_len: int = 80) -> str:
    """Return a valid JSONL debate-turn string."""
    return json.dumps({
        "agent": agent,
        "turn": turn,
        "argument": "x" * arg_len,
        "references": [],
    })


# ── validate() — base checks ─────────────────────────────────────────────────


def test_empty_string_is_invalid(v: ResponseValidator):
    assert not v.validate("", 10).valid


def test_whitespace_only_is_invalid(v: ResponseValidator):
    assert not v.validate("   \n\t  ", 10).valid


def test_too_short_is_invalid(v: ResponseValidator):
    result = v.validate("hi", 50)
    assert not result.valid
    assert "short" in result.reason.lower()


def test_api_error_marker_is_invalid(v: ResponseValidator):
    assert not v.validate("error: rate_limit_error occurred", 5).valid


def test_traceback_is_invalid(v: ResponseValidator):
    assert not v.validate("Traceback (most recent call last): ...", 10).valid


def test_disrespectful_language_is_invalid(v: ResponseValidator):
    assert not v.validate("This is bullshit argument nonsense fuck you", 10).valid


def test_markdown_fence_is_invalid(v: ResponseValidator):
    """Markdown code fences are rejected before JSON parsing."""
    response = "```json\n" + _valid_turn() + "\n```"
    result = v.validate(response, 10)
    assert not result.valid
    assert result.category == "format"


def test_unresolved_placeholder_is_invalid(v: ResponseValidator):
    """Unresolved $PLACEHOLDER tokens are rejected."""
    response = '{"agent":"A","turn":$TURN_NUMBER,"argument":"test","references":[]}'
    result = v.validate(response, 10)
    assert not result.valid
    assert result.category == "format"


def test_valid_response_passes(v: ResponseValidator):
    result = v.validate(_valid_turn(), 50)
    assert result.valid
    assert result.reason == ""


def test_min_len_boundary_passes(v: ResponseValidator):
    response = _valid_turn()
    assert len(response) >= 50
    assert v.validate(response, 50).valid


def test_min_len_boundary_fails(v: ResponseValidator):
    """One character under min_len is rejected before JSON check."""
    response = "x" * 49
    assert not v.validate(response, 50).valid


# ── validate_json() ──────────────────────────────────────────────────────────


def test_valid_json_object(v: ResponseValidator):
    assert v.validate_json('{"key": "value"}').valid


def test_valid_jsonl_line(v: ResponseValidator):
    line = '{"agent": "A", "turn": 1, "argument": "test", "references": []}'
    assert v.validate_json(line).valid


def test_invalid_json_is_rejected(v: ResponseValidator):
    result = v.validate_json("{not json}")
    assert not result.valid
    assert "JSON" in result.reason


def test_empty_json_string_is_rejected(v: ResponseValidator):
    assert not v.validate_json("").valid


def test_plain_text_is_rejected(v: ResponseValidator):
    assert not v.validate_json("just some text").valid


# ── validate_novelty() ───────────────────────────────────────────────────────


def test_novelty_passes_for_distinct_argument(v: ResponseValidator):
    prior = ["Solar panels produce clean energy and reduce carbon emissions significantly."]
    new_arg = "Nuclear power provides reliable baseload and has the lowest lifecycle emissions."
    assert v.validate_novelty(new_arg, prior).valid


def test_novelty_fails_for_near_duplicate(v: ResponseValidator):
    text = "Solar panels produce clean energy and significantly reduce carbon emissions worldwide."
    result = v.validate_novelty(text, [text])
    assert not result.valid
    assert result.category == "content"


def test_novelty_passes_with_no_prior_turns(v: ResponseValidator):
    assert v.validate_novelty("Any opening argument.", []).valid
