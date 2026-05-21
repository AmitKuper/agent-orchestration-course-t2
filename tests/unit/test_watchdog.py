"""Unit tests for src/watchdog.py — timeout, cancel, and context manager."""

from __future__ import annotations

import threading
import time

from src.watchdog import Watchdog


def test_fires_on_timeout():
    """Watchdog calls on_timeout after the specified delay."""
    fired = threading.Event()
    wd = Watchdog(timeout_seconds=0.05, on_timeout=fired.set)
    wd.start()
    assert fired.wait(timeout=0.5), "Watchdog did not fire within expected window."
    wd.cancel()


def test_cancel_prevents_fire():
    """Cancelling before timeout prevents on_timeout from being called."""
    fired = threading.Event()
    wd = Watchdog(timeout_seconds=0.2, on_timeout=fired.set)
    wd.start()
    wd.cancel()
    fired.wait(timeout=0.4)
    assert not fired.is_set(), "Watchdog fired after cancel."


def test_start_resets_timer():
    """Calling start() a second time resets the timer, not stacks it."""
    counter = {"n": 0}

    def cb():
        counter["n"] += 1

    wd = Watchdog(timeout_seconds=0.1, on_timeout=cb)
    wd.start()
    time.sleep(0.05)
    wd.start()  # reset
    time.sleep(0.15)
    wd.cancel()
    assert counter["n"] == 1, "Timer should fire exactly once after reset."


def test_context_manager_cancels_on_exit():
    """Using Watchdog as a context manager cancels the timer on exit."""
    fired = threading.Event()
    with Watchdog(timeout_seconds=0.3, on_timeout=fired.set):
        pass  # exits immediately
    fired.wait(timeout=0.5)
    assert not fired.is_set(), "Timer should have been cancelled by __exit__."


def test_context_manager_fires_if_slow():
    """Watchdog fires inside a context manager if the block takes too long."""
    fired = threading.Event()
    with Watchdog(timeout_seconds=0.05, on_timeout=fired.set):
        fired.wait(timeout=0.3)
    assert fired.is_set(), "Watchdog should fire during slow block."


def test_cancel_with_no_timer_is_safe():
    """Calling cancel() before start() does not raise."""
    wd = Watchdog(timeout_seconds=1.0, on_timeout=lambda: None)
    wd.cancel()  # should not raise
