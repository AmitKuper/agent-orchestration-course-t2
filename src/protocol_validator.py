"""Debate-turn JSON protocol validator."""

from __future__ import annotations

import json

from src.validation_result import ValidationResult


def validate_debate_turn(
    response: str,
    expected_agent: str | None = None,
    expected_turn: int | None = None,
    require_references: bool = False,
) -> ValidationResult:
    """Validate a debate-turn response against the JSONL protocol.

    Checks: valid JSON, required fields (agent, turn, argument, references),
    field types, optional agent/turn equality, optional non-empty references.

    Args:
        response: Stripped response string.
        expected_agent: If provided, must equal the ``agent`` field.
        expected_turn: If provided, must equal the ``turn`` field.
        require_references: If True, ``references`` must be non-empty.

    Returns:
        ValidationResult with category='format' for structural issues.
    """
    try:
        data = json.loads(response)
    except json.JSONDecodeError as exc:
        return ValidationResult(False, f"Invalid JSON: {exc}", category="format")
    if not isinstance(data, dict):
        return ValidationResult(
            False, "Response must be a JSON object, not an array or scalar.",
            category="format",
        )
    for field in ("agent", "turn", "argument"):
        if field not in data:
            return ValidationResult(
                False, f"Missing required field: '{field}'.", category="format"
            )
    if not isinstance(data["agent"], str) or not data["agent"].strip():
        return ValidationResult(
            False, "Field 'agent' must be a non-empty string.", category="format"
        )
    if not isinstance(data["turn"], int):
        return ValidationResult(
            False, "Field 'turn' must be an integer.", category="format"
        )
    if not isinstance(data["argument"], str) or not data["argument"].strip():
        return ValidationResult(
            False, "Field 'argument' must be a non-empty string.", category="format"
        )
    refs = data.get("references", [])
    if not isinstance(refs, list):
        return ValidationResult(
            False, "Field 'references' must be a list.", category="format"
        )
    if not all(isinstance(r, str) for r in refs):
        return ValidationResult(
            False, "All entries in 'references' must be strings.", category="format"
        )
    if expected_agent is not None and data["agent"] != expected_agent:
        return ValidationResult(
            False,
            f"Agent mismatch: expected '{expected_agent}', got '{data['agent']}'.",
            category="content",
        )
    if expected_turn is not None and data["turn"] != expected_turn:
        return ValidationResult(
            False,
            f"Turn mismatch: expected {expected_turn}, got {data['turn']}.",
            category="content",
        )
    if require_references and not data["references"]:
        return ValidationResult(
            False,
            "References list is empty. Provide at least one source citation.",
            category="content",
        )
    return ValidationResult(True)
