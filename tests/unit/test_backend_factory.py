"""Unit tests for make_backend factory function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import (
    ApiBackend,
    CliBackend,
    OllamaBackend,
    OllamaCliBackend,
    make_backend,
)


def test_make_backend_api_returns_api_backend():
    """make_backend('api') returns an ApiBackend instance."""
    with patch("src.backends._api.anthropic.Anthropic"):
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


def test_make_backend_ollama_cli_returns_ollama_cli_backend():
    """make_backend('ollama-cli') returns an OllamaCliBackend instance."""
    assert isinstance(make_backend("ollama-cli"), OllamaCliBackend)


def test_make_backend_unknown_raises():
    """make_backend raises ValueError for unrecognised backend type."""
    with pytest.raises(ValueError, match="Unknown backend"):
        make_backend("grpc")
