"""Unit tests for ApiBackend."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.backends import ApiBackend
from src.cost import CostTracker


def _make_backend_with_mock_client() -> tuple[ApiBackend, MagicMock]:
    """Return an ApiBackend with a pre-injected mock client."""
    backend = ApiBackend()
    mock_client = MagicMock()
    backend._client = mock_client
    return backend, mock_client


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def test_api_backend_records_tokens(cost: CostTracker):
    """ApiBackend.invoke records input/output tokens to the cost tracker."""
    backend, client = _make_backend_with_mock_client()
    mock_message = MagicMock()
    mock_message.content[0].text = "response text"
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50
    client.messages.create.return_value = mock_message

    result = backend.invoke("Agent", "claude-test", "prompt", cost, 2048)

    assert result == "response text"
    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 100
    assert summary["total_output_tokens"] == 50


def test_api_backend_passes_max_tokens(cost: CostTracker):
    """ApiBackend.invoke forwards max_tokens to the API call."""
    backend, client = _make_backend_with_mock_client()
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5
    client.messages.create.return_value = mock_message

    backend.invoke("Agent", "claude-test", "prompt", cost, 4096)

    client.messages.create.assert_called_once()
    call_kwargs = client.messages.create.call_args
    assert call_kwargs.kwargs.get("max_tokens") == 4096


def test_api_backend_passes_temperature(cost: CostTracker):
    """ApiBackend.invoke includes temperature in the API call when provided."""
    backend, client = _make_backend_with_mock_client()
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 5
    mock_message.usage.output_tokens = 5
    client.messages.create.return_value = mock_message

    backend.invoke("A", "model", "prompt", cost, 256, temperature=0.7)

    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs.get("temperature") == 0.7


def test_api_backend_creates_client_lazily():
    """ApiBackend._ensure_client creates the Anthropic client on first call."""
    from unittest.mock import patch
    from src.backends._api import ApiBackend
    backend = ApiBackend()
    mock_ant = MagicMock()
    mock_ant.Anthropic.return_value = MagicMock()
    with patch("src.backends._api._get_anthropic", return_value=mock_ant):
        backend._ensure_client()
    assert backend._client is not None
    mock_ant.Anthropic.assert_called_once()


def test_api_backend_passes_system(cost: CostTracker):
    """ApiBackend.invoke includes system prompt in the API call when provided."""
    backend, client = _make_backend_with_mock_client()
    mock_message = MagicMock()
    mock_message.content[0].text = "ok"
    mock_message.usage.input_tokens = 5
    mock_message.usage.output_tokens = 5
    client.messages.create.return_value = mock_message

    backend.invoke("A", "model", "prompt", cost, 256, system="You are helpful.")

    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs.get("system") == "You are helpful."
