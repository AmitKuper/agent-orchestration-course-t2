"""API and CLI backends for agent invocations.

ApiBackend  — Anthropic SDK directly (requires ANTHROPIC_API_KEY).
CliBackend  — shells out to `claude --print` via Pro OAuth.
OllamaBackend — calls Ollama's OpenAI-compatible endpoint directly
                (requires `requests`; install with `pip install requests`).
                Set OLLAMA_BASE_URL env var to override the default
                http://localhost:11434.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from src.cost import CostTracker

_OLLAMA_DEFAULT_URL = "http://localhost:11434"


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
        temperature: float | None = None,
    ) -> str:
        """Send prompt and return raw response text.

        Args:
            name: Agent display name (for cost tracking).
            model: Model identifier (used by ApiBackend and OllamaBackend).
            prompt: Full prompt string to send.
            cost_tracker: Records token usage after the call.
            max_tokens: Maximum tokens allowed in the response.
            temperature: Sampling temperature; None = model default.

        Returns:
            Raw response string from the model.
        """


class ApiBackend(Backend):
    """Calls the Anthropic Messages API directly."""

    def __init__(self) -> None:
        """Initialise the Anthropic SDK client."""
        self._client = anthropic.Anthropic()

    def invoke(self, name, model, prompt, cost_tracker, max_tokens, temperature=None) -> str:
        """Call the Anthropic API and record token usage."""
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if temperature is not None:
            kwargs["temperature"] = temperature
        message = self._client.messages.create(**kwargs)
        cost_tracker.record_call(name, message.usage.input_tokens, message.usage.output_tokens)
        return message.content[0].text


class CliBackend(Backend):
    """Shells out to `claude --print` — uses Pro OAuth, no API key required.

    If `ollama launch claude` has been run beforehand, this backend will
    route through Ollama automatically via the Claude Code integration.
    Token counts are unavailable; records zeros to the cost tracker.
    """

    def invoke(self, name, model, prompt, cost_tracker, max_tokens, temperature=None) -> str:
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


class OllamaBackend(Backend):
    """Calls Ollama's OpenAI-compatible REST API directly.

    Uses the model name passed per-call (e.g. "llama3.2"), so set
    --model-a / --model-b / --model-judge to your Ollama model names.
    Base URL is read from OLLAMA_BASE_URL (default http://localhost:11434).
    Requires: pip install requests
    """

    def __init__(self) -> None:
        """Import requests and resolve the Ollama base URL."""
        try:
            import requests as _requests
            self._requests = _requests
        except ImportError as exc:
            raise ImportError(
                "OllamaBackend requires the 'requests' package: pip install requests"
            ) from exc
        self._base_url = os.getenv("OLLAMA_BASE_URL", _OLLAMA_DEFAULT_URL).rstrip("/")

    def invoke(self, name, model, prompt, cost_tracker, max_tokens, temperature=None) -> str:
        """POST to Ollama's /v1/chat/completions and return the response text."""
        options: dict = {"num_predict": max_tokens}
        if temperature is not None:
            options["temperature"] = temperature
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": options,
        }
        response = self._requests.post(
            f"{self._base_url}/v1/chat/completions",
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        cost_tracker.record_call(
            name,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )
        return data["choices"][0]["message"]["content"]


def make_backend(backend_type: str) -> Backend:
    """Instantiate the correct backend from a type string.

    Args:
        backend_type: One of "api", "cli", or "ollama".

    Returns:
        Configured backend instance.

    Raises:
        ValueError: If backend_type is not recognised.
    """
    if backend_type == "api":
        return ApiBackend()
    if backend_type == "cli":
        return CliBackend()
    if backend_type == "ollama":
        return OllamaBackend()
    raise ValueError(f"Unknown backend: {backend_type!r}. Choose 'api', 'cli', or 'ollama'.")
