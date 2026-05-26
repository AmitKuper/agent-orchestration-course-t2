"""Abstract base for self-orchestrating backends that run a full debate in one call."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import DebateConfig


class OrchestratorBackend(ABC):
    """Backend that manages the entire debate lifecycle autonomously.

    Unlike ``Backend`` (which executes a single prompt per call), an
    ``OrchestratorBackend`` receives the full debate configuration and
    returns all turns plus a verdict in one operation.

    The Python ``DebateOrchestrator`` detects this type via ``isinstance``
    and delegates the full debate to ``run_debate()`` instead of running
    its own turn loop.
    """

    @abstractmethod
    def run_debate(
        self,
        config: DebateConfig,
        position_a: str,
        position_b: str,
    ) -> tuple[list[dict], dict | None]:
        """Run a complete debate and return all turns and the verdict.

        Args:
            config: Fully resolved debate configuration.
            position_a: Assigned position for Agent A.
            position_b: Assigned position for Agent B.

        Returns:
            Tuple of (turns, verdict) where turns is a list of turn dicts
            (same schema as conversation.jsonl entries) and verdict is the
            judge result dict or None if judgment failed.
        """

    def close(self) -> None:
        """Release any resources. No-op by default."""
