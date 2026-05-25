"""Backend factory — maps type strings to Backend/OrchestratorBackend instances."""

from __future__ import annotations

from pathlib import Path

from src.backends._api import ApiBackend
from src.backends._base import Backend
from src.backends._cli import CliBackend, OllamaCliBackend
from src.backends._ollama import OllamaBackend
from src.backends._ollama_orchestrator import OllamaOrchestratorBackend
from src.backends._orchestrator_base import OrchestratorBackend
from src.backends._persistent_cli import PersistentCliBackend

_CHOICES = (
    "claude-api", "claude-cli-agents", "claude-cli-session",
    "ollama-api", "ollama-cli-agents", "ollama-cli",
)


def make_backend(
    backend_type: str, output_path: Path | None = None
) -> Backend | OrchestratorBackend:
    """Instantiate the correct backend from a type string.

    Args:
        backend_type: One of the recognised backend identifiers (see _CHOICES).
            Legacy aliases ``api``, ``cli``, ``cli-session``, ``ollama``,
            ``ollama-cli`` are still accepted for backwards compatibility.
        output_path: Required for ``"claude-cli-session"``; the run output
            folder used as the subprocess working directory.

    Returns:
        Configured backend instance ready for use.

    Raises:
        ValueError: If ``backend_type`` is unrecognised or a required
            argument is missing.
    """
    # Canonical names
    if backend_type == "claude-api":
        return ApiBackend()
    if backend_type == "claude-cli-agents":
        return CliBackend()
    if backend_type == "claude-cli-session":
        if output_path is None:
            raise ValueError("claude-cli-session backend requires output_path")
        return PersistentCliBackend(output_path)
    if backend_type == "ollama-api":
        return OllamaBackend()
    if backend_type == "ollama-cli-agents":
        return OllamaCliBackend()
    if backend_type == "ollama-cli":
        return OllamaOrchestratorBackend()

    # Legacy aliases
    if backend_type == "api":
        return ApiBackend()
    if backend_type == "cli":
        return CliBackend()
    if backend_type == "cli-session":
        if output_path is None:
            raise ValueError("cli-session backend requires output_path")
        return PersistentCliBackend(output_path)
    if backend_type == "ollama":
        return OllamaBackend()

    raise ValueError(
        f"Unknown backend: {backend_type!r}. Choose one of: {', '.join(_CHOICES)}"
    )
