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
