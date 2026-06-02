"""Unit tests for protocol_validator and verdict_validator standalone functions."""

from __future__ import annotations

import json

from src.protocol_validator import validate_debate_turn
from src.verdict_validator import validate_judge_verdict


def _valid_turn(agent: str = "Agent A", turn: int = 1, arg_len: int = 80) -> str:
    """Return a valid JSONL debate-turn string."""
    return json.dumps({
        "agent": agent,
        "turn": turn,
        "argument": "x" * arg_len,
        "references": [],
    })


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


# ── validate_debate_turn() ───────────────────────────────────────────────────


def test_valid_turn_passes_protocol():
    """A fully valid debate turn passes all protocol checks."""
    assert validate_debate_turn(_valid_turn()).valid


def test_missing_agent_field_fails():
    data = {"turn": 1, "argument": "test", "references": []}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "agent" in result.reason


def test_missing_argument_field_fails():
    data = {"agent": "A", "turn": 1, "references": []}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "argument" in result.reason


def test_missing_references_field_passes():
    """references is optional — omitting it is treated as an empty list."""
    data = {"agent": "A", "turn": 1, "argument": "x" * 80}
    assert validate_debate_turn(json.dumps(data)).valid


def test_wrong_agent_name_fails():
    """agent field mismatch fails when expected_agent is set."""
    result = validate_debate_turn(_valid_turn("Agent B"), expected_agent="Agent A")
    assert not result.valid
    assert "mismatch" in result.reason


def test_wrong_turn_number_fails():
    """turn field mismatch fails when expected_turn is set."""
    result = validate_debate_turn(_valid_turn(turn=3), expected_turn=1)
    assert not result.valid


def test_require_references_with_empty_list_fails():
    """require_references=True rejects an empty references list."""
    result = validate_debate_turn(_valid_turn(), require_references=True)
    assert not result.valid
    assert "reference" in result.reason.lower()


def test_require_references_with_non_empty_list_passes():
    """require_references=True passes when references is non-empty."""
    data = {"agent": "A", "turn": 1, "argument": "x" * 80, "references": ["https://example.com"]}
    assert validate_debate_turn(json.dumps(data), require_references=True).valid


def test_non_dict_json_fails():
    """A JSON array instead of object is rejected."""
    result = validate_debate_turn("[1, 2, 3]")
    assert not result.valid
    assert result.category == "format"


def test_invalid_json_fails_as_format():
    result = validate_debate_turn("{bad json}")
    assert not result.valid
    assert result.category == "format"


# ── validate_judge_verdict() ─────────────────────────────────────────────────


def test_valid_verdict_passes():
    result = validate_judge_verdict(json.dumps(_valid_verdict()), "Agent A", "Agent B")
    assert result.valid


def test_invalid_winner_fails():
    verdict = _valid_verdict()
    verdict["winner"] = "Unknown Agent"
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "winner" in result.reason


def test_missing_scores_fails():
    verdict = _valid_verdict()
    del verdict["scores"]
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_score_out_of_range_fails():
    verdict = _valid_verdict()
    verdict["scores"]["Agent A"]["logic"] = 15
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_empty_explanation_fails():
    verdict = _valid_verdict()
    verdict["explanation"] = ""
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_missing_factcheck_flags_fails():
    verdict = _valid_verdict()
    del verdict["factcheck_flags"]
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid


def test_verdict_with_markdown_fence_fails():
    payload = "```json\n" + json.dumps(_valid_verdict()) + "\n```"
    result = validate_judge_verdict(payload, "Agent A", "Agent B")
    assert not result.valid
    assert result.category == "format"


# ── validate_debate_turn() — type checks ─────────────────────────────────────


def test_empty_agent_string_fails():
    """agent field that is an empty string is rejected."""
    data = {"agent": "", "turn": 1, "argument": "x" * 80, "references": []}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "agent" in result.reason.lower()


def test_non_int_turn_fails():
    """turn field that is a string is rejected."""
    data = {"agent": "A", "turn": "1", "argument": "x" * 80, "references": []}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "turn" in result.reason.lower()


def test_empty_argument_string_fails():
    """argument field that is an empty string is rejected."""
    data = {"agent": "A", "turn": 1, "argument": "", "references": []}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "argument" in result.reason.lower()


def test_non_list_references_fails():
    """references field that is not a list is rejected."""
    data = {"agent": "A", "turn": 1, "argument": "x" * 80, "references": "bad"}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "list" in result.reason.lower()


def test_non_string_in_references_fails():
    """references list containing non-strings is rejected."""
    data = {"agent": "A", "turn": 1, "argument": "x" * 80, "references": [1, 2]}
    result = validate_debate_turn(json.dumps(data))
    assert not result.valid
    assert "string" in result.reason.lower()


# ── validate_judge_verdict() — type checks ───────────────────────────────────


def test_verdict_invalid_json_fails():
    """validate_judge_verdict rejects invalid JSON."""
    result = validate_judge_verdict("{bad json}", "Agent A", "Agent B")
    assert not result.valid
    assert result.category == "format"


def test_verdict_array_json_fails():
    """validate_judge_verdict rejects a JSON array instead of an object."""
    result = validate_judge_verdict("[1, 2, 3]", "Agent A", "Agent B")
    assert not result.valid
    assert "object" in result.reason.lower()


def test_verdict_agent_missing_from_scores_fails():
    """validate_judge_verdict rejects scores dict that omits one agent."""
    verdict = _valid_verdict()
    verdict["scores"] = {
        "Agent A": {"logic": 8, "evidence": 9, "clarity": 7, "persuasiveness": 8},
    }
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "Agent B" in result.reason


def test_verdict_agent_scores_not_dict_fails():
    """validate_judge_verdict rejects an agent scores entry that is not a dict."""
    verdict = _valid_verdict()
    verdict["scores"]["Agent A"] = "not_a_dict"
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "dict" in result.reason.lower()


def test_verdict_missing_criterion_fails():
    """validate_judge_verdict rejects scores missing a required criterion."""
    verdict = _valid_verdict()
    del verdict["scores"]["Agent A"]["logic"]
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "logic" in result.reason


def test_verdict_factcheck_flags_not_list_fails():
    """validate_judge_verdict rejects factcheck_flags that is not a list."""
    verdict = _valid_verdict()
    verdict["factcheck_flags"] = "not_a_list"
    result = validate_judge_verdict(json.dumps(verdict), "Agent A", "Agent B")
    assert not result.valid
    assert "list" in result.reason.lower()
