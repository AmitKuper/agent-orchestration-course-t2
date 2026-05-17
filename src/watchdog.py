"""Per-agent timeout watchdog using threading.Timer."""

from __future__ import annotations

import threading
from typing import Callable, Optional


class Watchdog:
    """Monitors agent response time and fires a callback on timeout.

    A timeout is treated as an invalid response by the orchestrator and
    triggers the standard retry flow. Use as a context manager to guarantee
    the timer is always cancelled even if the agent raises an exception.
    """

    def __init__(self, timeout_seconds: float, on_timeout: Callable[[], None]) -> None:
        """Initialise the watchdog.

        Args:
            timeout_seconds: Seconds to wait before calling on_timeout.
            on_timeout: Callable invoked when the timer fires; runs in a
                daemon thread so it cannot block interpreter shutdown.
        """
        self._timeout = timeout_seconds
        self._on_timeout = on_timeout
        self._timer: Optional[threading.Timer] = None

    def start(self) -> None:
        """Start the watchdog timer, cancelling any previously running timer."""
        self.cancel()
        self._timer = threading.Timer(self._timeout, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def cancel(self) -> None:
        """Cancel the running timer if one exists."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def __enter__(self) -> Watchdog:
        """Start the timer on context entry."""
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Cancel the timer on context exit regardless of outcome."""
        self.cancel()
