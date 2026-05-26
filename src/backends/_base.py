"""Abstract Backend interface and agent-file helper."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.cost import CostTracker


def update_agent_file_model(path: Path, model: str) -> None:
    """Rewrite the ``model:`` field in a .claude/agents/*.md YAML frontmatter.

    Args:
        path: Path to the agent markdown file.
        model: Model identifier to write (e.g. 'claude-sonnet-4-6').
    """
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^(model:\s*).*$", rf"\g<1>{model}", text, count=1, flags=re.MULTILINE)
    path.write_text(text, encoding="utf-8")


class Backend(ABC):
    """Abstract invocation backend — decouples agents from the transport layer."""

    uses_memory: bool = False
    """True for CLI backends that rely on project memory for conversation history."""

    def close(self) -> None:  # noqa: B027
        """Release any resources held by this backend. No-op by default."""

    @abstractmethod
    def invoke(
        self,
        name: str,
        model: str,
        prompt: str,
        cost_tracker: CostTracker,
        max_tokens: int,
        temperature: float | None = None,
        system: str | None = None,
    ) -> str:
        """Send prompt and return raw response text.

        Args:
            name: Agent display name (for cost tracking).
            model: Model identifier used by API/Ollama backends.
            prompt: Full prompt string to send.
            cost_tracker: Records token usage after the call.
            max_tokens: Maximum tokens allowed in the response.
            temperature: Sampling temperature; None = model default.
            system: Optional system prompt injected before the user message.

        Returns:
            Raw response string from the model.
        """
