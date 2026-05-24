"""Backend factory — maps type strings to Backend instances."""

from __future__ import annotations

from src.backends._api import ApiBackend
from src.backends._base import Backend
from src.backends._cli import CliBackend, OllamaCliBackend
from src.backends._ollama import OllamaBackend


def make_backend(backend_type: str) -> Backend:
    """Instantiate the correct backend from a type string.

    Args:
        backend_type: One of ``"api"``, ``"cli"``, ``"ollama-cli"``, ``"ollama"``.

    Returns:
        Configured backend instance ready for use.

    Raises:
        ValueError: If ``backend_type`` is not one of the recognised values.
    """
    if backend_type == "api":
        return ApiBackend()
    if backend_type == "cli":
        return CliBackend()
    if backend_type == "ollama-cli":
        return OllamaCliBackend()
    if backend_type == "ollama":
        return OllamaBackend()
    raise ValueError(
        f"Unknown backend: {backend_type!r}. Choose 'api', 'cli', 'ollama-cli', or 'ollama'."
    )
