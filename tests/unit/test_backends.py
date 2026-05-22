"""Unit tests for src/backends.py — ApiBackend, CliBackend, OllamaBackend, make_backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import ApiBackend, CliBackend, OllamaBackend, make_backend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


# ---------------------------------------------------------------------------
# make_backend
# ---------------------------------------------------------------------------


def test_make_backend_api_returns_api_backend():
    """make_backend('api') returns an ApiBackend instance."""
    with patch("src.backends.anthropic.Anthropic"):
        backend = make_backend("api")
    assert isinstance(backend, ApiBackend)


def test_make_backend_cli_returns_cli_backend():
    """make_backend('cli') returns a CliBackend instance."""
    assert isinstance(make_backend("cli"), CliBackend)


def test_make_backend_ollama_returns_ollama_backend():
    """make_backend('ollama') returns an OllamaBackend instance."""
    with patch.dict("sys.modules", {"requests": MagicMock()}):
        backend = make_backend("ollama")
    assert isinstance(backend, OllamaBackend)


def test_make_backend_unknown_raises():
    """make_backend raises ValueError for unrecognised backend type."""
    with pytest.raises(ValueError, match="Unknown backend"):
        make_backend("grpc")


# ---------------------------------------------------------------------------
# ApiBackend
# ---------------------------------------------------------------------------


def test_api_backend_records_tokens(cost: CostTracker):
    """ApiBackend.invoke records input/output tokens to the cost tracker."""
    mock_message = MagicMock()
    mock_message.content[0].text = "response text"
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50

    with patch("src.backends.anthropic.Anthropic"):
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

    with patch("src.backends.anthropic.Anthropic"):
        backend = ApiBackend()
        backend._client.messages.create.return_value = mock_message
        backend.invoke("Agent", "claude-test", "prompt", cost, 4096)

    backend._client.messages.create.assert_called_once()
    call_kwargs = backend._client.messages.create.call_args
    assert call_kwargs.kwargs.get("max_tokens") == 4096


# ---------------------------------------------------------------------------
# CliBackend
# ---------------------------------------------------------------------------


def test_cli_backend_returns_stdout(cost: CostTracker):
    """CliBackend.invoke returns stripped stdout from the claude CLI."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = '{"agent":"A","turn":1,"argument":"ok","references":[]}\n'

    with patch("src.backends.subprocess.run", return_value=mock_result):
        result = CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)

    assert result == '{"agent":"A","turn":1,"argument":"ok","references":[]}'


def test_cli_backend_records_zero_tokens(cost: CostTracker):
    """CliBackend.invoke records zero tokens (not available from CLI)."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"

    with patch("src.backends.subprocess.run", return_value=mock_result):
        CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)

    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0


def test_cli_backend_raises_on_nonzero_exit(cost: CostTracker):
    """CliBackend.invoke raises RuntimeError when claude CLI exits non-zero."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some error"

    with patch("src.backends.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="claude CLI failed"):
            CliBackend().invoke("Agent", "any-model", "prompt", cost, 2048)


# ---------------------------------------------------------------------------
# OllamaBackend
# ---------------------------------------------------------------------------


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
    with patch.dict("sys.modules", {"requests": None}):
        with pytest.raises(ImportError, match="requests"):
            OllamaBackend()
