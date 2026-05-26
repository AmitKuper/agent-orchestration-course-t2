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
    "ollama-api", "ollama-cli-agents", "ollama-cli", "ollama-orchestrator",
)


def make_backend(
    backend_type: str, output_path: Path | None = None
) -> Backend | OrchestratorBackend:
    """Instantiate the correct backend from a type string.

    Canonical names:
        claude-api             Anthropic SDK (requires ANTHROPIC_API_KEY)
        claude-cli-agents      claude --print subprocess per agent turn
        claude-cli-session     Persistent claude subprocess per agent
        ollama-api             Ollama HTTP API
        ollama-cli-agents      ollama run subprocess per agent turn
        ollama-cli             ollama run subprocess per agent turn (alias)
        ollama-orchestrator    Single-shot Ollama self-orchestrating backend

    Legacy aliases:
        api          → claude-api
        cli          → claude-cli-agents
        cli-session  → claude-cli-session
        ollama       → ollama-api

    Args:
        backend_type: One of the recognised backend identifiers (see _CHOICES).
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
    if backend_type in ("ollama-cli", "ollama-orchestrator"):
        # Single model call that self-orchestrates the entire debate
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
