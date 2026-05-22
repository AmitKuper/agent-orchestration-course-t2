"""Abstract base class for debate and judge agents with shared retry logic."""

from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING, Optional

from src.validator import ResponseValidator

if TYPE_CHECKING:
    from src.backends import Backend
    from src.config import DebateConfig
    from src.cost import CostTracker
    from src.state import ConversationState

from src.constants import MAX_TOKENS_DEBATE


class BaseAgent(ABC):
    """Abstract base for DebateAgent and JudgeAgent.

    Provides invoke_with_retry() which calls _invoke(), validates the result,
    and retries up to max_retries times — feeding the violation reason back
    into each retry prompt so the agent can self-correct.

    Subclasses that override _invoke() do not require a backend. Subclasses
    that rely on the default _invoke() must pass a Backend instance.
    """

    def __init__(
        self,
        name: str,
        model: str,
        config: DebateConfig,
        state: ConversationState,
        cost_tracker: CostTracker,
        backend: Optional[Backend] = None,
    ) -> None:
        """Initialise with shared infrastructure references.

        Args:
            name: Display name for this agent instance (e.g. "Agent A").
            model: Claude model ID to use for API calls.
            config: Fully resolved debate configuration.
            state: Shared conversation state for history access.
            cost_tracker: Token usage recorder for cost accounting.
            backend: Invocation backend (ApiBackend or CliBackend). Required
                unless the subclass overrides _invoke() directly.
        """
        self.name = name
        self.model = model
        self.config = config
        self.state = state
        self.cost_tracker = cost_tracker
        self._backend = backend
        self._max_tokens: int = MAX_TOKENS_DEBATE
        self._validator = ResponseValidator()
        self._logger = logging.getLogger(f"debate.agent.{name}")

    def invoke_with_retry(self, prompt: str, context: str = "") -> str:
        """Invoke the agent and retry on validation failure.

        Calls _invoke(), validates the response, and on failure builds a
        retry prompt that explains the violation. Returns empty string if
        all attempts are exhausted (caller should log and skip the turn).

        Args:
            prompt: The main prompt to send.
            context: Optional context prepended to the prompt on first attempt.

        Returns:
            Accepted response string, or empty string after max retries.
        """
        current_prompt = f"{context}\n\n{prompt}".strip() if context else prompt
        for attempt in range(self.config.max_retries + 1):
            response = self._invoke(current_prompt)
            result = self._validator.validate(response, self.config.min_response_len)
            if result.valid:
                return response
            self._logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt + 1,
                self.config.max_retries + 1,
                self.name,
                result.reason,
            )
            if attempt < self.config.max_retries:
                current_prompt = self._build_retry_prompt(prompt, result.reason)
        self._logger.warning("All retries exhausted for %s — skipping turn.", self.name)
        return ""

    def _invoke(self, prompt: str) -> str:
        """Send prompt to the configured backend and return the raw response.

        Args:
            prompt: Full prompt to send.

        Returns:
            Raw string response from the backend.

        Raises:
            NotImplementedError: If no backend was provided at construction.
        """
        if self._backend is None:
            raise NotImplementedError(
                f"{type(self).__name__} must either provide a backend or override _invoke()."
            )
        return self._backend.invoke(
            self.name, self.model, prompt, self.cost_tracker, self._max_tokens,
            self.config.temperature,
        )

    def _build_retry_prompt(self, original_prompt: str, violation_reason: str) -> str:
        """Construct a retry prompt that explains the previous violation.

        Args:
            original_prompt: The original task prompt (not the failed attempt).
            violation_reason: Human-readable explanation of what was invalid.

        Returns:
            New prompt string with the violation explanation prepended.
        """
        return (
            f"Your previous response was rejected: {violation_reason}\n"
            f"Output ONLY the raw JSON line — no markdown, no explanation, no code fences.\n\n"
            f"{original_prompt}"
        )
