"""Anthropic SDK backend.

Note: ``anthropic`` is imported lazily inside ``__init__`` to avoid Windows
MAX_PATH failures when the project lives in a deeply nested path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backends._base import Backend
from src.shared.gatekeeper import APIGatekeeper

if TYPE_CHECKING:
    from src.cost import CostTracker

# Lazy module-level reference; tests patch ``_get_anthropic`` directly.
anthropic: Any = None  # noqa: N816


def _get_anthropic() -> Any:
    """Return the ``anthropic`` module, importing it on first call."""
    global anthropic  # noqa: PLW0603
    if anthropic is None:
        import anthropic as _ant  # noqa: PLC0415
        anthropic = _ant
    return anthropic


class ApiBackend(Backend):
    """Calls the Anthropic Messages API via APIGatekeeper.

    All requests route through the gatekeeper, which reads rate limits from
    ``config/rate_limits.json`` and retries transient failures automatically.
    Requires ``ANTHROPIC_API_KEY`` environment variable.
    Records actual input/output token counts to the cost tracker.
    """

    def __init__(self) -> None:
        """Initialise the Anthropic SDK client and gatekeeper."""
        self._client: Any = _get_anthropic().Anthropic()
        self._gatekeeper = APIGatekeeper("anthropic")

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
        """Call the Anthropic API through the gatekeeper and record token usage.

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

        message = self._gatekeeper.execute(self._client.messages.create, **kwargs)
        cost_tracker.record_call(name, message.usage.input_tokens, message.usage.output_tokens)
        return message.content[0].text
