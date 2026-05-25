"""Ollama HTTP API backend."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.backends._base import Backend
from src.shared.gatekeeper import APIGatekeeper

if TYPE_CHECKING:
    from src.cost import CostTracker

_DEFAULT_URL = "http://localhost:11434"


class OllamaBackend(Backend):
    """Calls Ollama's OpenAI-compatible REST API through the APIGatekeeper.

    Set ``--model-a`` / ``--model-b`` / ``--model-judge`` to Ollama model names.
    Base URL is read from ``OLLAMA_BASE_URL`` (default http://localhost:11434).
    Requires: ``pip install requests`` (or ``uv sync --extra ollama``).
    All requests are routed through the gatekeeper for rate limiting and retry.
    """

    def __init__(self) -> None:
        """Import requests, resolve base URL, and initialise gatekeeper.

        Raises:
            ImportError: If the ``requests`` package is not installed.
        """
        try:
            import requests as _requests  # noqa: PLC0415
            self._requests = _requests
        except ImportError as exc:
            raise ImportError(
                "OllamaBackend requires the 'requests' package: "
                "uv sync --extra ollama"
            ) from exc
        self._base_url = os.getenv("OLLAMA_BASE_URL", _DEFAULT_URL).rstrip("/")
        self._gatekeeper = APIGatekeeper("ollama")

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
        """POST to Ollama's /v1/chat/completions through the gatekeeper.

        Args:
            name: Agent display name for cost tracking.
            model: Ollama model name (e.g. 'llama3.2').
            prompt: User message text.
            cost_tracker: Receives prompt/completion token counts.
            max_tokens: Passed as ``num_predict`` to Ollama.
            temperature: Added to options when provided.
            system: Prepended as a system message when provided.

        Returns:
            Content string from the first choice in the API response.

        Raises:
            requests.HTTPError: If the Ollama API returns a non-2xx status.
        """
        options: dict = {"num_predict": max_tokens}
        if temperature is not None:
            options["temperature"] = temperature
        messages = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        def _call() -> dict:
            response = self._requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            return response.json()

        data = self._gatekeeper.execute(_call)
        usage = data.get("usage", {})
        cost_tracker.record_call(
            name, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        )
        return data["choices"][0]["message"]["content"]
