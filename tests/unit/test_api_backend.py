"""Unit tests for ApiBackend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import ApiBackend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def test_api_backend_records_tokens(cost: CostTracker):
    """ApiBackend.invoke records input/output tokens to the cost tracker."""
    mock_message = MagicMock()
    mock_message.content[0].text = "response text"
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50

    with patch("src.backends._api.anthropic.Anthropic"):
        backend = ApiBackend()
        backend._client.messages.create.return_value = mock_message
        result = backend.invoke("Agent", "claude-test", "prompt", cost, 2048)

    assert result == "response text"
    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 100
    assert summary["total_output_tokens"] == 50


def test_api_backend_passes_max_tokens(cost: CostTracker):
    """ApiBackend.invoke forwards max_tokens to the API call."""
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    with patch("src.backends._api.anthropic.Anthropic"):
        backend = ApiBackend()
        backend._client.messages.create.return_value = mock_message
        backend.invoke("Agent", "claude-test", "prompt", cost, 4096)

    backend._client.messages.create.assert_called_once()
    call_kwargs = backend._client.messages.create.call_args
    assert call_kwargs.kwargs.get("max_tokens") == 4096


def test_api_backend_passes_temperature(cost: CostTracker):
    """ApiBackend.invoke includes temperature in the API call when provided."""
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 5
    mock_message.usage.output_tokens = 5

    with patch("src.backends._api.anthropic.Anthropic"):
        backend = ApiBackend()
        backend._client.messages.create.return_value = mock_message
        backend.invoke("A", "model", "prompt", cost, 256, temperature=0.7)

    call_kwargs = backend._client.messages.create.call_args.kwargs
    assert call_kwargs.get("temperature") == 0.7


def test_api_backend_passes_system(cost: CostTracker):
    """ApiBackend.invoke includes system prompt in the API call when provided."""
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 5
    mock_message.usage.output_tokens = 5

    with patch("src.backends._api.anthropic.Anthropic"):
        backend = ApiBackend()
        backend._client.messages.create.return_value = mock_message
        backend.invoke("A", "model", "prompt", cost, 256, system="You are helpful.")

    call_kwargs = backend._client.messages.create.call_args.kwargs
    assert call_kwargs.get("system") == "You are helpful."
