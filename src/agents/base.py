"""Abstract base class for debate and judge agents with shared retry logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.agents.loader import load_agent_def  # noqa: F401 — re-exported
from src.constants import MAX_TOKENS_DEBATE
from src.stance_validator import StanceValidator
from src.validator import ResponseValidator, ValidationResult

if TYPE_CHECKING:
    from src.backends import Backend
    from src.config import DebateConfig
    from src.cost import CostTracker
    from src.state import ConversationState

__all__ = ["BaseAgent", "load_agent_def"]


class BaseAgent:
    """Abstract base for DebateAgent and JudgeAgent.

    Provides invoke_with_retry() which calls _invoke(), validates the result,
    and retries up to max_retries times — feeding the violation reason back
    into each retry prompt so the agent can self-correct.

    Subclasses that rely on the default _invoke() must pass a Backend instance.
    """

    def __init__(
        self,
        name: str,
        model: str,
        config: DebateConfig,
        state: ConversationState,
        cost_tracker: CostTracker,
        backend: Backend | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Initialise agent with shared infrastructure references."""
        self.name = name
        self.model = model
        self.config = config
        self.state = state
        self.cost_tracker = cost_tracker
        self._backend = backend
        self._system_prompt = system_prompt or None
        self._max_tokens: int = MAX_TOKENS_DEBATE
        self._validator = ResponseValidator()
        self._stance_validator = StanceValidator()
        self._assigned_position: str | None = None
        self._logger = logging.getLogger(f"debate.agent.{name}")

    def invoke_with_retry(self, prompt: str, context: str = "") -> str:
        """Invoke the agent, validate, and retry up to max_retries on failure.

        Returns accepted response string, or empty string after all retries.
        """
        full_prompt = f"{context}\n\n{prompt}".strip() if context else prompt
        current_prompt = full_prompt
        for attempt in range(self.config.max_retries + 1):
            response = self._invoke(current_prompt)
            result = self._validate_response(response)
            if result.valid and self._assigned_position is not None:
                stance = self._stance_validator.validate(
                    response, self._assigned_position, self.name
                )
                if not stance.valid:
                    result = type(result)(False, stance.reason, "content")
            if result.valid:
                result = self._extra_validate(response)
            if result.valid:
                return response
            self._logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt + 1, self.config.max_retries + 1, self.name, result.reason,
            )
            if attempt < self.config.max_retries:
                if result.category == "format":
                    current_prompt = self._build_format_retry_prompt(prompt, result.reason)
                else:
                    current_prompt = self._build_content_retry_prompt(full_prompt, result.reason)
        self._logger.error("All retries exhausted for %s — skipping turn.", self.name)
        return ""

    def _validate_response(self, response: str) -> ValidationResult:
        """Run base format/length/content checks. Override in subclasses for different schemas."""
        return self._validator.validate(
            response,
            self.config.min_response_len,
            require_references=getattr(self.config, "require_references", False),
        )

    def _extra_validate(self, response: str) -> ValidationResult:
        """Hook for subclass-specific validation. Returns valid by default."""
        return ValidationResult(True)

    def _invoke(self, prompt: str) -> str:
        """Send prompt to the backend and return the raw response.

        Raises NotImplementedError if no backend was provided.
        """
        if self._backend is None:
            raise NotImplementedError(
                f"{type(self).__name__} must either provide a backend or override _invoke()."
            )
        return self._backend.invoke(
            self.name, self.model, prompt, self.cost_tracker, self._max_tokens,
            self.config.temperature, self._system_prompt,
        )

    def _build_format_retry_prompt(self, prompt: str, reason: str) -> str:
        """Build retry prompt for format/JSON errors (no history re-attached)."""
        return (
            f"Your previous response was rejected: {reason}\n"
            f"Output ONLY the raw JSON line — no markdown, no explanation, no code fences.\n\n"
            f"{prompt}"
        )

    def _build_content_retry_prompt(self, prompt_with_context: str, reason: str) -> str:
        """Build retry prompt for content errors (full history context re-attached)."""
        return (
            f"Your previous response was rejected: {reason}\n"
            f"Please provide a substantive response that meets the requirements.\n\n"
            f"{prompt_with_context}"
        )
