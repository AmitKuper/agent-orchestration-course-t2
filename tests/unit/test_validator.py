"""Unit tests for src/validator.py — ResponseValidator and ValidationResult."""

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


# ── validate_debate_turn() — protocol field checks ───────────────────────────


def test_valid_turn_passes_protocol(v: ResponseValidator):
    """A fully valid debate turn passes all protocol checks."""
    assert v.validate_debate_turn(_valid_turn()).valid


def test_missing_agent_field_fails(v: ResponseValidator):
    data = {"turn": 1, "argument": "test", "references": []}
    result = v.validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "agent" in result.reason


def test_missing_argument_field_fails(v: ResponseValidator):
    data = {"agent": "A", "turn": 1, "references": []}
    result = v.validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "argument" in result.reason


def test_missing_references_field_fails(v: ResponseValidator):
    data = {"agent": "A", "turn": 1, "argument": "test"}
    result = v.validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "references" in result.reason


def test_wrong_agent_name_fails(v: ResponseValidator):
    """agent field mismatch fails when expected_agent is set."""
    result = v.validate_debate_turn(
        _valid_turn("Agent B"), expected_agent="Agent A"
    )
    assert not result.valid
    assert "mismatch" in result.reason


def test_wrong_turn_number_fails(v: ResponseValidator):
    """turn field mismatch fails when expected_turn is set."""
    result = v.validate_debate_turn(
        _valid_turn(turn=3), expected_turn=1
    )
    assert not result.valid


def test_require_references_with_empty_list_fails(v: ResponseValidator):
    """require_references=True rejects an empty references list."""
    result = v.validate_debate_turn(_valid_turn(), require_references=True)
    assert not result.valid
    assert "reference" in result.reason.lower()


def test_require_references_with_non_empty_list_passes(v: ResponseValidator):
    """require_references=True passes when references is non-empty."""
    data = {"agent": "A", "turn": 1, "argument": "x" * 80, "references": ["https://example.com"]}
    result = v.validate_debate_turn(json.dumps(data), require_references=True)
    assert result.valid


def test_non_dict_json_fails(v: ResponseValidator):
    """A JSON array instead of object is rejected."""
    result = v.validate_debate_turn("[1, 2, 3]")
    assert not result.valid
    assert result.category == "format"


def test_invalid_json_fails_as_format(v: ResponseValidator):
    result = v.validate_debate_turn("{bad json}")
    assert not result.valid
    assert result.category == "format"


# ── validate_judge_verdict() ─────────────────────────────────────────────────


def _valid_verdict(agent_a: str = "Agent A", agent_b: str = "Agent B") -> dict:
    """Return a valid judge verdict dict."""
    return {
        "winner": agent_a,
        "scores": {
            agent_a: {"logic": 8, "evidence": 9, "clarity": 7, "persuasiveness": 8},
            agent_b: {"logic": 6, "evidence": 7, "clarity": 6, "persuasiveness": 7},
        },
        "tiebreaker": None,
        "explanation": "Agent A presented stronger evidence.",
        "factcheck_flags": [],
    }


def test_valid_verdict_passes(v: ResponseValidator):
    result = v.validate_judge_verdict(json.dumps(_valid_verdict()), "Agent A", "Agent B")
    assert result.valid


def test_invalid_winner_fails(v: ResponseValidator):
    verdict = _valid_verdict()
    verdict["winner"] = "Unknown Agent"
    result = v.validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "winner" in result.reason


def test_missing_scores_fails(v: ResponseValidator):
    verdict = _valid_verdict()
    del verdict["scores"]
    result = v.validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_score_out_of_range_fails(v: ResponseValidator):
    verdict = _valid_verdict()
    verdict["scores"]["Agent A"]["logic"] = 15
    result = v.validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_empty_explanation_fails(v: ResponseValidator):
    verdict = _valid_verdict()
    verdict["explanation"] = ""
    result = v.validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_missing_factcheck_flags_fails(v: ResponseValidator):
    verdict = _valid_verdict()
    del verdict["factcheck_flags"]
    result = v.validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_verdict_with_markdown_fence_fails(v: ResponseValidator):
    payload = "```json\n" + json.dumps(_valid_verdict()) + "\n```"
    result = v.validate_judge_verdict(payload, "Agent A", "Agent B")
    assert not result.valid
    assert result.category == "format"


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
