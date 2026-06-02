"""Unit tests for make_backend factory function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import (
    ApiBackend,
    CliBackend,
    OllamaBackend,
    OllamaOrchestratorBackend,
    make_backend,
)


def test_make_backend_api_returns_api_backend():
    """make_backend('api') returns an ApiBackend instance."""
    with patch("src.backends._api._get_anthropic", return_value=MagicMock()):
        backend = make_backend("api")
    assert isinstance(backend, ApiBackend)


def test_make_backend_claude_api_returns_api_backend():
    """make_backend('claude-api') returns an ApiBackend instance."""
    with patch("src.backends._api._get_anthropic", return_value=MagicMock()):
        backend = make_backend("claude-api")
    assert isinstance(backend, ApiBackend)


def test_make_backend_cli_returns_cli_backend():
    """make_backend('cli') returns a CliBackend instance."""
    assert isinstance(make_backend("cli"), CliBackend)


def test_make_backend_ollama_returns_ollama_backend():
    """make_backend('ollama') returns an OllamaBackend instance."""
    with patch.dict("sys.modules", {"requests": MagicMock()}):
        backend = make_backend("ollama")
    assert isinstance(backend, OllamaBackend)


def test_make_backend_ollama_cli_returns_ollama_orchestrator_backend():
    """make_backend('ollama-cli') returns an OllamaOrchestratorBackend instance."""
    assert isinstance(make_backend("ollama-cli"), OllamaOrchestratorBackend)


def test_make_backend_ollama_orchestrator_returns_orchestrator_backend():
    """make_backend('ollama-orchestrator') returns an OllamaOrchestratorBackend."""
    assert isinstance(make_backend("ollama-orchestrator"), OllamaOrchestratorBackend)


def test_make_backend_unknown_raises():
    """make_backend raises ValueError for unrecognised backend type."""
    with pytest.raises(ValueError, match="Unknown backend"):
        make_backend("grpc")


def test_make_backend_claude_cli_agents_with_output_path(tmp_path):
    """make_backend('claude-cli-agents', output_path) passes the workdir to CliBackend."""
    backend = make_backend("claude-cli-agents", output_path=tmp_path)
    assert isinstance(backend, CliBackend)


def test_make_backend_claude_cli_session_with_output_path(tmp_path):
    """make_backend('claude-cli-session', output_path) returns PersistentCliBackend."""
    from src.backends import PersistentCliBackend
    backend = make_backend("claude-cli-session", output_path=tmp_path)
    assert isinstance(backend, PersistentCliBackend)


def test_make_backend_claude_cli_session_without_output_path_raises():
    """make_backend('claude-cli-session') without output_path raises ValueError."""
    with pytest.raises(ValueError, match="output_path"):
        make_backend("claude-cli-session")


def test_make_backend_ollama_api():
    """make_backend('ollama-api') returns OllamaBackend."""
    with patch.dict("sys.modules", {"requests": MagicMock()}):
        backend = make_backend("ollama-api")
    assert isinstance(backend, OllamaBackend)


def test_make_backend_ollama_cli_agents():
    """make_backend('ollama-cli-agents') returns OllamaCliBackend."""
    from src.backends import OllamaCliBackend
    backend = make_backend("ollama-cli-agents")
    assert isinstance(backend, OllamaCliBackend)


def test_make_backend_legacy_cli_session_with_output_path(tmp_path):
    """make_backend('cli-session', output_path) returns PersistentCliBackend."""
    from src.backends import PersistentCliBackend
    backend = make_backend("cli-session", output_path=tmp_path)
    assert isinstance(backend, PersistentCliBackend)


def test_make_backend_legacy_cli_session_without_output_path_raises():
    """make_backend('cli-session') without output_path raises ValueError."""
    with pytest.raises(ValueError, match="output_path"):
        make_backend("cli-session")
