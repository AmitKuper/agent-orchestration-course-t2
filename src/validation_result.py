"""ValidationResult dataclass shared across all validator modules."""

from __future__ import annotations

from dataclasses import dataclass


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
