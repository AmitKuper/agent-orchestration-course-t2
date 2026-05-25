"""Invocation backends for the AI Debate Platform.

Public API — import from here, never from submodules directly:

    from src.backends import Backend, ApiBackend, CliBackend, make_backend
"""

from src.backends._api import ApiBackend
from src.backends._base import Backend, update_agent_file_model
from src.backends._cli import CliBackend, OllamaCliBackend
from src.backends._factory import make_backend
from src.backends._ollama import OllamaBackend
from src.backends._ollama_orchestrator import OllamaOrchestratorBackend
from src.backends._orchestrator_base import OrchestratorBackend
from src.backends._persistent_cli import PersistentCliBackend

__all__ = [
    "Backend",
    "OrchestratorBackend",
    "ApiBackend",
    "CliBackend",
    "OllamaCliBackend",
    "OllamaBackend",
    "OllamaOrchestratorBackend",
    "PersistentCliBackend",
    "make_backend",
    "update_agent_file_model",
]
