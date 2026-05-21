"""API and CLI backends for agent invocations.

ApiBackend calls the Anthropic SDK directly (requires ANTHROPIC_API_KEY).
CliBackend shells out to `claude --print` using the Pro OAuth subscription.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from src.cost import CostTracker


class Backend(ABC):
    """Abstract invocation backend — decouples agents from the transport layer."""

    @abstractmethod
    def invoke(
        self,
        name: str,
        model: str,
        prompt: str,
        cost_tracker: CostTracker,
        max_tokens: int,
    ) -> str:
        """Send prompt and return raw response text.

        Args:
            name: Agent display name (for cost tracking).
            model: Model identifier (used by ApiBackend; ignored by CliBackend).
            prompt: Full prompt string to send.
            cost_tracker: Records token usage after the call.
            max_tokens: Maximum tokens allowed in the response.

        Returns:
            Raw response string from the model.
        """


class ApiBackend(Backend):
    """Calls the Anthropic Messages API directly."""

    def __init__(self) -> None:
        """Initialise the Anthropic SDK client."""
        self._client = anthropic.Anthropic()

    def invoke(self, name, model, prompt, cost_tracker, max_tokens) -> str:
        """Call the Anthropic API and record token usage."""
        message = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        cost_tracker.record_call(name, message.usage.input_tokens, message.usage.output_tokens)
        return message.content[0].text


class CliBackend(Backend):
    """Shells out to `claude --print` — uses Pro OAuth, no API key required.

    Token counts are unavailable; records zeros to the cost tracker.
    """

    def invoke(self, name, model, prompt, cost_tracker, max_tokens) -> str:
        """Run `claude --print` with prompt on stdin and return stdout."""
        result = subprocess.run(
            ["claude", "--print", "--dangerously-skip-permissions"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {result.stderr[:200]}")
        cost_tracker.record_call(name, 0, 0)
        return result.stdout.strip()


def make_backend(backend_type: str) -> Backend:
    """Return an ApiBackend or CliBackend based on the backend_type string.

    Args:
        backend_type: Either "api" or "cli".

    Returns:
        Configured backend instance.

    Raises:
        ValueError: If backend_type is not recognised.
    """
    if backend_type == "cli":
        return CliBackend()
    if backend_type == "api":
        return ApiBackend()
    raise ValueError(f"Unknown backend: {backend_type!r}. Choose 'api' or 'cli'.")
