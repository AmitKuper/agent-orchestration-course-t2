"""Anthropic SDK backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

from src.backends._base import Backend

if TYPE_CHECKING:
    from src.cost import CostTracker


class ApiBackend(Backend):
    """Calls the Anthropic Messages API directly.

    Requires ``ANTHROPIC_API_KEY`` environment variable.
    Records actual input/output token counts to the cost tracker.
    """

    def __init__(self) -> None:
        """Initialise the Anthropic SDK client."""
        self._client = anthropic.Anthropic()

    def invoke(
        self,
        name: str,
        model: str,
        prompt: str,
        cost_tracker: CostTracker,
        max_tokens: int,
        temperature: float | None = None,
        system: str | None = None,
    ) -> str:
        """Call the Anthropic API and record token usage.

        Args:
            name: Agent display name for cost tracking.
            model: Claude model ID (e.g. 'claude-sonnet-4-6').
            prompt: User message text.
            cost_tracker: Receives input/output token counts after the call.
            max_tokens: Hard cap on response length.
            temperature: Sampling temperature; omitted if None.
            system: System prompt; omitted if None.

        Returns:
            Text content of the first response block.
        """
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if system is not None:
            kwargs["system"] = system
        message = self._client.messages.create(**kwargs)
        cost_tracker.record_call(name, message.usage.input_tokens, message.usage.output_tokens)
        return message.content[0].text
