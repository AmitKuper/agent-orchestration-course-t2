"""Response validation rules for debate and judge agent outputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.constants import API_ERROR_MARKERS, DISRESPECTFUL_PATTERNS


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

    Checks run in order of cheapness: empty → length → API error → language.
    The first failing check short-circuits the rest and returns its reason,
    which the orchestrator forwards to the agent as a retry explanation.
    """

    def validate(self, response: str, min_len: int) -> ValidationResult:
        """Run all content checks on a response string.

        Args:
            response: Raw string returned by the agent.
            min_len: Minimum acceptable character length after stripping.

        Returns:
            ValidationResult — valid=True only if all checks pass.
        """
        if not response or not response.strip():
            return ValidationResult(False, "Response is empty.")
        if len(response.strip()) < min_len:
            return ValidationResult(
                False, f"Response is too short (minimum {min_len} characters)."
            )
        if self._contains_api_error(response):
            return ValidationResult(False, "Response contains an API error message.")
        if self._contains_disrespectful_language(response):
            return ValidationResult(False, "Response contains disrespectful language.")
        return self.validate_json(response)

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
