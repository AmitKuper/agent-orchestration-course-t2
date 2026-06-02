"""Unit tests for src/shared/gatekeeper.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.shared.gatekeeper import APIGatekeeper


def test_gatekeeper_returns_call_result():
    """APIGatekeeper.execute returns the result of the wrapped callable."""
    gk = APIGatekeeper("anthropic")
    result = gk.execute(lambda: 42)
    assert result == 42


def test_gatekeeper_forwards_args_and_kwargs():
    """APIGatekeeper.execute passes *args and **kwargs to the callable."""
    def add(a, b, *, offset=0):
        return a + b + offset

    gk = APIGatekeeper("anthropic")
    result = gk.execute(add, 3, 4, offset=10)
    assert result == 17


def test_gatekeeper_retries_on_exception():
    """APIGatekeeper.execute retries after a transient exception."""
    call = MagicMock(side_effect=[RuntimeError("transient"), "ok"])
    gk = APIGatekeeper("anthropic")
    with patch("src.shared.gatekeeper.time.sleep"):
        result = gk.execute(call)
    assert result == "ok"
    assert call.call_count == 2


def test_gatekeeper_raises_after_max_retries():
    """APIGatekeeper.execute raises RuntimeError when all retries are exhausted."""
    call = MagicMock(side_effect=RuntimeError("always fails"))
    gk = APIGatekeeper("anthropic")
    with (
        patch("src.shared.gatekeeper.time.sleep"),
        pytest.raises(RuntimeError, match="retries"),
    ):
        gk.execute(call)


def test_gatekeeper_uses_config_from_json(tmp_path):
    """APIGatekeeper reads retry_delay_seconds from config/rate_limits.json."""
    import json
    rate_limits = {"test_backend": {"retry_delay_seconds": 99, "max_retries": 1, "backoff_multiplier": 1}}
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "rate_limits.json").write_text(json.dumps(rate_limits), encoding="utf-8")

    with patch("src.shared.gatekeeper._RATE_LIMITS_PATH", config_dir / "rate_limits.json"):
        gk = APIGatekeeper("test_backend")

    assert gk._retry_delay == 99
    assert gk._max_retries == 1


def test_gatekeeper_defaults_when_no_config():
    """APIGatekeeper uses sane defaults when rate_limits.json is absent."""
    with patch("src.shared.gatekeeper._RATE_LIMITS_PATH") as mock_path:
        mock_path.exists.return_value = False
        gk = APIGatekeeper("nonexistent_backend")

    assert gk._retry_delay == 5
    assert gk._max_retries == 3
    assert gk._backoff == 2.0


# ── RPM enforcement ────────────────────────────────────────────────────────


def _make_clock(start: float = 0.0):
    """Return a mutable fake monotonic clock."""
    state = [start]

    def clock():
        return state[0]

    clock.advance = lambda secs: state.__setitem__(0, state[0] + secs)  # type: ignore[attr-defined]
    return clock


def test_rpm_allows_calls_under_limit():
    """Calls within the RPM window proceed without sleeping."""
    clock = _make_clock()
    gk = APIGatekeeper.__new__(APIGatekeeper)
    from collections import deque
    gk._rpm = 3
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque()
    gk._clock = clock
    results = []
    for _ in range(3):
        results.append(gk.execute(lambda: "ok"))
    assert results == ["ok", "ok", "ok"]
    assert len(gk._window) == 3


def test_rpm_blocks_at_limit():
    """When window is full, gatekeeper sleeps before allowing the next call."""
    clock = _make_clock(start=0.0)
    from collections import deque
    gk = APIGatekeeper.__new__(APIGatekeeper)
    gk._rpm = 2
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque()
    gk._clock = clock
    # Fill the window
    gk._window.append(0.0)
    gk._window.append(0.5)
    # Advance clock to t=10 — old timestamps are still within 60 s
    clock.advance(10.0)
    slept = []
    with patch("src.shared.gatekeeper.time.sleep", side_effect=lambda s: (slept.append(s), clock.advance(s))):
        gk.execute(lambda: "ok")
    assert slept, "Expected gatekeeper to sleep when RPM window is full"


def test_rpm_evicts_old_timestamps():
    """Timestamps older than 60 s are evicted before checking the limit."""
    clock = _make_clock(start=0.0)
    from collections import deque
    gk = APIGatekeeper.__new__(APIGatekeeper)
    gk._rpm = 1
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque([0.0])  # one old timestamp
    gk._clock = clock
    clock.advance(61.0)  # now that timestamp is stale
    with patch("src.shared.gatekeeper.time.sleep") as mock_sleep:
        gk.execute(lambda: "ok")
    mock_sleep.assert_not_called()  # old timestamp evicted, no sleep needed


def test_configured_rpm_property():
    """configured_rpm returns the RPM limit set on the gatekeeper."""
    from collections import deque
    gk = APIGatekeeper.__new__(APIGatekeeper)
    gk._rpm = 5
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque()
    gk._clock = lambda: 0.0
    assert gk.configured_rpm == 5


def test_enforce_rpm_returns_immediately_when_unlimited():
    """_enforce_rpm is a no-op when rpm is 0 (unlimited)."""
    from collections import deque
    gk = APIGatekeeper.__new__(APIGatekeeper)
    gk._rpm = 0
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque()
    gk._clock = lambda: 0.0
    with patch("src.shared.gatekeeper.time.sleep") as mock_sleep:
        gk._enforce_rpm()
    mock_sleep.assert_not_called()


def test_recent_request_count():
    """recent_request_count reflects only timestamps within the 60-second window."""
    clock = _make_clock(start=100.0)
    from collections import deque
    gk = APIGatekeeper.__new__(APIGatekeeper)
    gk._rpm = 10
    gk._retry_delay = 0
    gk._max_retries = 0
    gk._backoff = 1.0
    gk._backend_type = "test"
    gk._window = deque([30.0, 50.0, 90.0])  # 30 is exactly 70s ago (outside); 50 and 90 within
    gk._clock = clock
    assert gk.recent_request_count == 2
