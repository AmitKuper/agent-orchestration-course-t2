"""Unit tests for src/topic_validator.py — validate_topic."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import InvalidTopicError
from src.topic_validator import validate_topic


def _mock_backend(text: str) -> MagicMock:
    """Return a mock backend whose invoke() returns the given text."""
    backend = MagicMock()
    backend.invoke.return_value = text
    return backend


# ── with backend ─────────────────────────────────────────────────────────────


def test_valid_topic_returns_positions():
    """validate_topic returns (position_a, position_b) for a debatable topic."""
    payload = json.dumps({"valid": True, "position_a": "FOR", "position_b": "AGAINST"})
    backend = _mock_backend(payload)
    pos_a, pos_b = validate_topic("test topic", "model", backend)
    assert pos_a == "FOR"
    assert pos_b == "AGAINST"


def test_invalid_topic_raises():
    """validate_topic raises InvalidTopicError when model says not debatable."""
    payload = json.dumps({"valid": False, "reason": "not debatable"})
    backend = _mock_backend(payload)
    with pytest.raises(InvalidTopicError, match="not debatable"):
        validate_topic("bad topic", "model", backend)


def test_invalid_topic_default_reason():
    """InvalidTopicError falls back to a default reason when none is given."""
    payload = json.dumps({"valid": False})
    backend = _mock_backend(payload)
    with pytest.raises(InvalidTopicError, match="not debatable"):
        validate_topic("bad topic", "model", backend)


def test_strips_markdown_code_fence():
    """validate_topic strips ```json ... ``` fences before parsing."""
    inner = json.dumps({"valid": True, "position_a": "A", "position_b": "B"})
    payload = f"```json\n{inner}\n```"
    backend = _mock_backend(payload)
    pos_a, pos_b = validate_topic("topic", "model", backend)
    assert pos_a == "A"
    assert pos_b == "B"


def test_strips_plain_code_fence():
    """validate_topic strips ``` fences without a language tag."""
    inner = json.dumps({"valid": True, "position_a": "X", "position_b": "Y"})
    payload = f"```\n{inner}\n```"
    backend = _mock_backend(payload)
    pos_a, pos_b = validate_topic("topic", "model", backend)
    assert pos_a == "X"
    assert pos_b == "Y"


# ── without backend (Anthropic SDK fallback) ──────────────────────────────────


def test_fallback_to_anthropic_sdk():
    """Without a backend, validate_topic uses the Anthropic SDK via _get_anthropic."""
    payload = json.dumps({"valid": True, "position_a": "SDK_A", "position_b": "SDK_B"})
    mock_msg = MagicMock()
    mock_msg.content[0].text = payload
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

    with patch("src.backends._api._get_anthropic", return_value=mock_anthropic):
        pos_a, pos_b = validate_topic("topic", "claude-test")

    assert pos_a == "SDK_A"
    assert pos_b == "SDK_B"
