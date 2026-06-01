"""API Gatekeeper — centralized handler for all external API calls.

Routes every external call through a single choke point that enforces
rate limits (read from config/rate_limits.json), adds retry logic with
exponential back-off, and logs every attempt.

Design note: the gatekeeper is synchronous (no FIFO queue). All callers
block in the calling thread. This is intentional for the course project,
which runs one debate turn at a time. A full async queue would add
complexity without benefit given the sequential debate flow.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
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
    per-backend RPM cap, retry delay, and exponential back-off.

    RPM enforcement uses a sliding window: timestamps of recent requests
    are kept in a deque. Before each call, timestamps older than 60 s are
    dropped. If the window is full, the gatekeeper sleeps until the oldest
    timestamp is old enough to make room.
    """

    def __init__(self, backend_type: str = "anthropic", _clock: Any = None) -> None:
        """Initialise gatekeeper for a specific backend.

        Args:
            backend_type: Key in rate_limits.json (e.g. 'anthropic', 'ollama', 'cli').
            _clock: Injectable clock for testing (defaults to time.monotonic).
        """
        limits = _load_limits()
        cfg = limits.get(backend_type, {})
        self._retry_delay: float = float(cfg.get("retry_delay_seconds", 5))
        self._max_retries: int = int(cfg.get("max_retries", 3))
        self._backoff: float = float(cfg.get("backoff_multiplier", 2.0))
        self._rpm: int = int(cfg.get("requests_per_minute", 0))
        self._backend_type = backend_type
        self._window: deque[float] = deque()
        self._clock = _clock or time.monotonic

    # ── public status ──────────────────────────────────────────────────────

    @property
    def recent_request_count(self) -> int:
        """Number of requests recorded in the current 60-second window."""
        now = self._clock()
        return sum(1 for t in self._window if now - t < 60.0)

    @property
    def configured_rpm(self) -> int:
        """Configured requests-per-minute limit (0 = unlimited)."""
        return self._rpm

    # ── rate limiting ──────────────────────────────────────────────────────

    def _enforce_rpm(self) -> None:
        """Block until the RPM limit allows another request.

        Uses a 60-second sliding window. If the window is full, sleep until
        the oldest timestamp is more than 60 s ago.
        """
        if self._rpm <= 0:
            return
        now = self._clock()
        # evict timestamps older than 60 s
        while self._window and now - self._window[0] >= 60.0:
            self._window.popleft()
        if len(self._window) >= self._rpm:
            wait = 60.0 - (now - self._window[0])
            if wait > 0:
                _logger.debug(
                    "Gatekeeper: RPM limit %d reached for %s. Waiting %.1fs.",
                    self._rpm, self._backend_type, wait,
                )
                time.sleep(wait)
                # re-evict after sleep
                now = self._clock()
                while self._window and now - self._window[0] >= 60.0:
                    self._window.popleft()
        self._window.append(self._clock())

    # ── main entry point ───────────────────────────────────────────────────

    def execute(self, call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute an external API call with RPM enforcement, retry, and back-off.

        Args:
            call: Callable that performs the external request.
            *args: Positional arguments forwarded to ``call``.
            **kwargs: Keyword arguments forwarded to ``call``.

        Returns:
            The return value of ``call``.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        self._enforce_rpm()
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
