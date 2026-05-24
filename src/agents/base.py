"""Abstract base class for debate and judge agents with shared retry logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.agents.loader import load_agent_def  # noqa: F401 — re-exported
from src.constants import MAX_TOKENS_DEBATE
from src.validator import ResponseValidator

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
        """Initialise with shared infrastructure references.

        Args:
            name: Display name for this agent instance (e.g. "Agent A").
            model: Claude model ID to use for API calls.
            config: Fully resolved debate configuration.
            state: Shared conversation state for history access.
            cost_tracker: Token usage recorder for cost accounting.
            backend: Invocation backend. Required unless subclass overrides _invoke().
            system_prompt: Optional system prompt injected on every call.
        """
        self.name = name
        self.model = model
        self.config = config
        self.state = state
        self.cost_tracker = cost_tracker
        self._backend = backend
        self._system_prompt = system_prompt or None
        self._max_tokens: int = MAX_TOKENS_DEBATE
        self._validator = ResponseValidator()
        self._logger = logging.getLogger(f"debate.agent.{name}")

    def invoke_with_retry(self, prompt: str, context: str = "") -> str:
        """Invoke the agent and retry on validation failure.

        Args:
            prompt: The main prompt to send.
            context: Optional context prepended to the prompt on first attempt.

        Returns:
            Accepted response string, or empty string after max retries.
        """
        full_prompt = f"{context}\n\n{prompt}".strip() if context else prompt
        current_prompt = full_prompt
        for attempt in range(self.config.max_retries + 1):
            response = self._invoke(current_prompt)
            result = self._validator.validate(response, self.config.min_response_len)
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
            self.config.temperature, self._system_prompt,
        )

    def _build_format_retry_prompt(self, prompt: str, reason: str) -> str:
        """Retry prompt for format/JSON errors — no history re-attached.

        The agent produced the right content but the wrong structure. Re-sending
        history would add noise; just explain the structural error and repeat the
        bare task so the agent can focus on fixing the format.

        Args:
            prompt: The original task prompt (without history context).
            reason: JSONDecodeError or other structural failure description.

        Returns:
            Compact prompt focused on format correction.
        """
        return (
            f"Your previous response was rejected: {reason}\n"
            f"Output ONLY the raw JSON line — no markdown, no explanation, no code fences.\n\n"
            f"{prompt}"
        )

    def _build_content_retry_prompt(self, prompt_with_context: str, reason: str) -> str:
        """Retry prompt for content errors — full history context re-attached.

        Re-attaches history so the agent can produce a substantive response
        grounded in the debate so far (too short, empty, disrespectful, etc.).

        Args:
            prompt_with_context: The full prompt including history context.
            reason: Human-readable description of the content violation.

        Returns:
            Prompt with history context and a clear correction instruction.
        """
        return (
            f"Your previous response was rejected: {reason}\n"
            f"Please provide a substantive response that meets the requirements.\n\n"
            f"{prompt_with_context}"
        )
