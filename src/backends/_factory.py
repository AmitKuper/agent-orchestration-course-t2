"""Backend factory — maps type strings to Backend instances."""

from __future__ import annotations

from pathlib import Path

from src.backends._api import ApiBackend
from src.backends._base import Backend
from src.backends._cli import CliBackend, OllamaCliBackend
from src.backends._ollama import OllamaBackend
from src.backends._persistent_cli import PersistentCliBackend


def make_backend(backend_type: str, output_path: Path | None = None) -> Backend:
    """Instantiate the correct backend from a type string.

    Args:
        backend_type: One of ``"api"``, ``"cli"``, ``"cli-session"``,
            ``"ollama-cli"``, ``"ollama"``.
        output_path: Required for ``"cli-session"``; the run output folder
            used as the subprocess working directory.

    Returns:
        Configured backend instance ready for use.

    Raises:
        ValueError: If ``backend_type`` is unrecognised or ``output_path``
            is missing for ``"cli-session"``.
    """
    if backend_type == "api":
        return ApiBackend()
    if backend_type == "cli":
        return CliBackend()
    if backend_type == "cli-session":
        if output_path is None:
            raise ValueError("cli-session backend requires output_path")
        return PersistentCliBackend(output_path)
    if backend_type == "ollama-cli":
        return OllamaCliBackend()
    if backend_type == "ollama":
        return OllamaBackend()
    raise ValueError(
        f"Unknown backend: {backend_type!r}. "
        "Choose 'api', 'cli', 'cli-session', 'ollama-cli', or 'ollama'."
    )
