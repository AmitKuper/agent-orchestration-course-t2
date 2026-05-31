"""Judge verdict JSON protocol validator."""

from __future__ import annotations

import json
import re

from src.validation_result import ValidationResult

_MD_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def validate_judge_verdict(
    response: str,
    agent_a: str,
    agent_b: str,
) -> ValidationResult:
    """Validate a judge verdict against the required schema.

    Args:
        response: Raw judge response string.
        agent_a: Name of debater A (valid winner value).
        agent_b: Name of debater B (valid winner value).

    Returns:
        ValidationResult — valid=True only if all checks pass.
    """
    if _MD_FENCE_RE.search(response.strip()):
        return ValidationResult(
            False, "Verdict contains markdown fences. Output raw JSON only.",
            category="format",
        )
    try:
        data = json.loads(response.strip())
    except json.JSONDecodeError as exc:
        return ValidationResult(False, f"Invalid JSON: {exc}", category="format")
    if not isinstance(data, dict):
        return ValidationResult(False, "Verdict must be a JSON object.", category="format")
    winner = data.get("winner")
    if winner not in (agent_a, agent_b):
        return ValidationResult(
            False,
            f"'winner' must be one of '{agent_a}' or '{agent_b}', got {winner!r}.",
            category="content",
        )
    scores = data.get("scores")
    if not isinstance(scores, dict):
        return ValidationResult(False, "'scores' must be a dict.", category="format")
    criteria = ("logic", "evidence", "clarity", "persuasiveness")
    for agent_name in (agent_a, agent_b):
        if agent_name not in scores:
            return ValidationResult(
                False, f"'scores' missing entry for '{agent_name}'.", category="format"
            )
        agent_scores = scores[agent_name]
        if not isinstance(agent_scores, dict):
            return ValidationResult(
                False, f"scores['{agent_name}'] must be a dict.", category="format"
            )
        for criterion in criteria:
            val = agent_scores.get(criterion, agent_scores.get(criterion.capitalize()))
            if val is None:
                return ValidationResult(
                    False,
                    f"scores['{agent_name}'] missing '{criterion}'.",
                    category="format",
                )
            if not isinstance(val, (int, float)) or not (0 <= val <= 10):
                return ValidationResult(
                    False,
                    f"scores['{agent_name}']['{criterion}'] must be 0–10.",
                    category="content",
                )
    explanation = data.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        return ValidationResult(
            False, "'explanation' must be a non-empty string.", category="format"
        )
    if "factcheck_flags" not in data:
        return ValidationResult(
            False, "'factcheck_flags' field is required.", category="format"
        )
    if not isinstance(data["factcheck_flags"], list):
        return ValidationResult(
            False, "'factcheck_flags' must be a list.", category="format"
        )
    return ValidationResult(True)
