"""Unit tests for src/validator.py — ResponseValidator and ValidationResult."""

from __future__ import annotations

import pytest

from src.validator import ResponseValidator


@pytest.fixture
def v() -> ResponseValidator:
    """Return a fresh ResponseValidator for each test."""
    return ResponseValidator()


# ── validate() ──────────────────────────────────────────────────────────────


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


def test_valid_response_passes(v: ResponseValidator):
    response = '{"agent":"A","turn":1,"argument":"' + "x" * 80 + '","references":[]}'
    result = v.validate(response, 50)
    assert result.valid
    assert result.reason == ""


def test_min_len_boundary_passes(v: ResponseValidator):
    """A valid JSON response at or above min_len is accepted."""
    response = '{"agent":"A","turn":1,"argument":"' + "x" * 80 + '","references":[]}'
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
