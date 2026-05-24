"""API Gatekeeper — centralized handler for all external API calls.

Routes every external call through a single choke point that enforces
rate limits (read from config/rate_limits.json), adds retry logic with
exponential back-off, and logs every attempt.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

_RATE_LIMITS_PATH = Path("config/rate_limits.json")
_logger = logging.getLogger("debate.gatekeeper")


def _load_limits() -> dict:
    """Load rate limit config; return empty dict if file is missing."""
    if _RATE_LIMITS_PATH.exists():
        return json.loads(_RATE_LIMITS_PATH.read_text(encoding="utf-8"))
    return {}


class APIGatekeeper:
    """Centralized handler for all external API calls.

    Reads rate limits from config/rate_limits.json and enforces them via
    per-backend retry delay and back-off multiplier.
    """

    def __init__(self, backend_type: str = "anthropic") -> None:
        """Initialise gatekeeper for a specific backend.

        Args:
            backend_type: Key in rate_limits.json (e.g. 'anthropic', 'ollama', 'cli').
        """
        limits = _load_limits()
        cfg = limits.get(backend_type, {})
        self._retry_delay: float = float(cfg.get("retry_delay_seconds", 5))
        self._max_retries: int = int(cfg.get("max_retries", 3))
        self._backoff: float = float(cfg.get("backoff_multiplier", 2.0))
        self._backend_type = backend_type

    def execute(self, call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute an external API call with retry and back-off.

        Args:
            call: Callable that performs the external request.
            *args: Positional arguments forwarded to ``call``.
            **kwargs: Keyword arguments forwarded to ``call``.

        Returns:
            The return value of ``call``.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        delay = self._retry_delay
        for attempt in range(1, self._max_retries + 2):
            try:
                return call(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                if attempt > self._max_retries:
                    raise RuntimeError(
                        f"Gatekeeper: {self._backend_type} call failed after "
                        f"{self._max_retries} retries: {exc}"
                    ) from exc
                _logger.warning(
                    "Gatekeeper: attempt %d/%d failed (%s). Retrying in %.1fs.",
                    attempt, self._max_retries, exc, delay,
                )
                time.sleep(delay)
                delay *= self._backoff
        return None  # unreachable; satisfies type checkers
