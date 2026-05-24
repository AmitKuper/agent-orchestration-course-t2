"""Unit tests for OllamaBackend (HTTP API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import OllamaBackend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


@pytest.fixture
def ollama_backend() -> OllamaBackend:
    """Return an OllamaBackend with a mocked requests module."""
    mock_requests = MagicMock()
    with patch.dict("sys.modules", {"requests": mock_requests}):
        backend = OllamaBackend()
    backend._requests = mock_requests
    return backend


def test_ollama_backend_returns_response_content(ollama_backend, cost):
    """OllamaBackend.invoke returns the message content from Ollama's response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ollama reply"}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 40},
    }
    ollama_backend._requests.post.return_value = mock_response

    result = ollama_backend.invoke("Agent", "llama3.2", "prompt", cost, 2048)

    assert result == "ollama reply"


def test_ollama_backend_records_tokens(ollama_backend, cost):
    """OllamaBackend.invoke records prompt/completion token counts."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "reply"}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 40},
    }
    ollama_backend._requests.post.return_value = mock_response

    ollama_backend.invoke("Agent", "llama3.2", "prompt", cost, 2048)

    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 80
    assert summary["total_output_tokens"] == 40


def test_ollama_backend_uses_model_name(ollama_backend, cost):
    """OllamaBackend.invoke passes the model name to the Ollama API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {},
    }
    ollama_backend._requests.post.return_value = mock_response

    ollama_backend.invoke("Agent", "mistral", "prompt", cost, 2048)

    call_kwargs = ollama_backend._requests.post.call_args
    assert call_kwargs.kwargs["json"]["model"] == "mistral"


def test_ollama_backend_missing_requests_raises():
    """OllamaBackend raises ImportError when requests is not installed."""
    with (
        patch.dict("sys.modules", {"requests": None}),
        pytest.raises(ImportError, match="requests"),
    ):
        OllamaBackend()


def test_ollama_backend_passes_temperature(ollama_backend, cost):
    """OllamaBackend.invoke adds temperature to options when provided."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {},
    }
    ollama_backend._requests.post.return_value = mock_response

    ollama_backend.invoke("A", "llama3", "prompt", cost, 256, temperature=0.5)

    payload = ollama_backend._requests.post.call_args.kwargs["json"]
    assert payload["options"]["temperature"] == 0.5


def test_ollama_backend_passes_system(ollama_backend, cost):
    """OllamaBackend.invoke prepends a system message when system is provided."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {},
    }
    ollama_backend._requests.post.return_value = mock_response

    ollama_backend.invoke("A", "llama3", "prompt", cost, 256, system="Be concise.")

    payload = ollama_backend._requests.post.call_args.kwargs["json"]
    assert payload["messages"][0] == {"role": "system", "content": "Be concise."}
