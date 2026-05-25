"""Stance validation service — ensures debaters stay on their assigned side.

Provides deterministic rule-based stance checking via concession phrase
detection and keyword matching. Used by the orchestrator to reject turns
where an agent concedes or argues the opposite side.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

_logger = logging.getLogger("debate.stance_validator")

_CONCESSION_PHRASES: tuple[str, ...] = (
    "i agree with",
    "you are right",
    "you're right",
    "my opponent is correct",
    "i concede",
    "i changed my mind",
    "i no longer support",
    "i must admit you are correct",
    "i must admit you're correct",
    "i was wrong",
    "i stand corrected",
    "i surrender",
    "i give up",
    "you have convinced me",
    "you've convinced me",
    "you make a good point against",
    "i now believe the opposite",
    "i withdraw my position",
    "i cannot defend",
)


@dataclass
class StanceResult:
    """Outcome of a stance validation check.

    Attributes:
        valid: True if the response appears to defend the assigned position.
        reason: Human-readable explanation when valid=False.
    """

    valid: bool
    reason: str = ""


class StanceValidator:
    """Rule-based validator ensuring a debater stays on their assigned side.

    Checks for concession phrases and explicit capitulation language.
    Logs each check at DEBUG (PASS) or WARNING (FAIL) level.
    """

    def validate(self, response: str, position: str, agent_name: str) -> StanceResult:
        """Check whether a turn response defends the assigned position.

        Args:
            response: The raw argument text from the debater.
            position: The position this agent was assigned to defend.
            agent_name: Display name of the agent (for logging).

        Returns:
            StanceResult with valid=True if no concession is detected.
        """
        lower = response.lower()
        for phrase in _CONCESSION_PHRASES:
            if re.search(rf"\b{re.escape(phrase)}\b", lower):
                reason = (
                    f"Response contains concession phrase '{phrase}'. "
                    f"{agent_name} must continue defending: {position}"
                )
                _logger.warning("Stance FAIL [%s]: %s", agent_name, reason)
                return StanceResult(False, reason)

        _logger.debug("Stance PASS [%s]", agent_name)
        return StanceResult(True)
