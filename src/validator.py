"""Response validation rules for debate and judge agent outputs.

Validates the full JSON communication protocol, not just json.loads.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.constants import API_ERROR_MARKERS, DISRESPECTFUL_PATTERNS, NOVELTY_THRESHOLD

_PLACEHOLDER_RE = re.compile(r"\$[A-Z_]+")
_MD_FENCE_RE = re.compile(r"^```", re.MULTILINE)


@dataclass
class ValidationResult:
    """Outcome of a single response validation check.

    Attributes:
        valid: True if the response passed all checks.
        reason: Human-readable explanation of why the check failed.
        category: 'format' for structural/JSON errors; 'content' for all others.
            Retry logic uses this to decide whether to re-attach history context.
    """

    valid: bool
    reason: str = ""
    category: str = "content"


class ResponseValidator:
    """Validates agent responses before the orchestrator accepts them.

    Checks run in order of cheapness: empty → length → API error → language →
    markdown fences → placeholders → JSON structure → protocol fields.
    The first failing check short-circuits the rest.
    """

    def validate(
        self,
        response: str,
        min_len: int,
        expected_agent: str | None = None,
        expected_turn: int | None = None,
        require_references: bool = False,
    ) -> ValidationResult:
        """Run all content checks on a response string.

        Args:
            response: Raw string returned by the agent.
            min_len: Minimum acceptable character length after stripping.
            expected_agent: If set, the ``agent`` field must match this value.
            expected_turn: If set, the ``turn`` field must match this value.
            require_references: If True, ``references`` must be non-empty.

        Returns:
            ValidationResult — valid=True only if all checks pass.
        """
        if not response or not response.strip():
            return ValidationResult(False, "Response is empty.")
        stripped = response.strip()
        if len(stripped) < min_len:
            return ValidationResult(
                False, f"Response is too short (minimum {min_len} characters)."
            )
        if self._contains_api_error(stripped):
            return ValidationResult(False, "Response contains an API error message.")
        if self._contains_disrespectful_language(stripped):
            return ValidationResult(False, "Response contains disrespectful language.")
        if _MD_FENCE_RE.search(stripped):
            return ValidationResult(
                False,
                "Response contains markdown code fences. Output raw JSON only.",
                category="format",
            )
        if _PLACEHOLDER_RE.search(stripped):
            return ValidationResult(
                False,
                "Response contains unresolved placeholders (e.g. $TURN_NUMBER).",
                category="format",
            )
        return self.validate_debate_turn(
            stripped, expected_agent, expected_turn, require_references
        )

    def validate_debate_turn(
        self,
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
                category="format"
            )
        for field in ("agent", "turn", "argument", "references"):
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
        if not isinstance(data["references"], list):
            return ValidationResult(
                False, "Field 'references' must be a list.", category="format"
            )
        if not all(isinstance(r, str) for r in data["references"]):
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

    def validate_judge_verdict(
        self,
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
                category="format"
            )
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError as exc:
            return ValidationResult(False, f"Invalid JSON: {exc}", category="format")
        if not isinstance(data, dict):
            return ValidationResult(False, "Verdict must be a JSON object.", category="format")

        # winner
        winner = data.get("winner")
        if winner not in (agent_a, agent_b):
            return ValidationResult(
                False,
                f"'winner' must be one of '{agent_a}' or '{agent_b}', got {winner!r}.",
                category="content",
            )
        # scores
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
                val = agent_scores.get(criterion)
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
        # explanation
        explanation = data.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            return ValidationResult(
                False, "'explanation' must be a non-empty string.", category="format"
            )
        # factcheck_flags
        if "factcheck_flags" not in data:
            return ValidationResult(
                False, "'factcheck_flags' field is required.", category="format"
            )
        if not isinstance(data["factcheck_flags"], list):
            return ValidationResult(
                False, "'factcheck_flags' must be a list.", category="format"
            )
        return ValidationResult(True)

    def validate_json(self, response: str) -> ValidationResult:
        """Verify that response is well-formed JSON using json.loads.

        Args:
            response: Raw string expected to parse as JSON.

        Returns:
            ValidationResult — valid=True if json.loads succeeds.
        """
        try:
            json.loads(response)
            return ValidationResult(True)
        except json.JSONDecodeError as exc:
            return ValidationResult(False, f"Invalid JSON: {exc}", category="format")

    def validate_novelty(self, argument: str, prior_arguments: list[str]) -> ValidationResult:
        """Check that the argument is not near-duplicate of any prior turn by the same agent.

        Args:
            argument: The new argument text to check.
            prior_arguments: All previous argument texts from this agent.

        Returns:
            ValidationResult — invalid if similarity exceeds NOVELTY_THRESHOLD.
        """
        for prior in prior_arguments:
            ratio = SequenceMatcher(None, argument.lower(), prior.lower()).ratio()
            if ratio > NOVELTY_THRESHOLD:
                return ValidationResult(
                    False,
                    "Your argument is too similar to a previous turn. "
                    "You must introduce new points, angles, or evidence.",
                    category="content",
                )
        return ValidationResult(True)

    def _contains_api_error(self, response: str) -> bool:
        """Return True if the response resembles an API error string."""
        lower = response.lower()
        return any(marker in lower for marker in API_ERROR_MARKERS)

    def _contains_disrespectful_language(self, response: str) -> bool:
        """Return True if the response contains any disrespectful terms."""
        lower = response.lower()
        return any(
            re.search(rf"\b{re.escape(p)}\b", lower) for p in DISRESPECTFUL_PATTERNS
        )
