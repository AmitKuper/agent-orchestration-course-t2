"""CLI backends: Claude Code CLI and Ollama CLI.

Both backends route subprocess calls through the APIGatekeeper for retry
and logging. Subprocess timeouts are enforced via ``subprocess.run(...,
timeout=...)``.

``--dangerously-skip-permissions`` for the Claude CLI is opt-in via the
``CLAUDE_SKIP_PERMISSIONS`` environment variable (default: ``true`` for
non-interactive use, but can be set to ``false`` to disable).
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from src.backends._ansi import extract_response
from src.backends._base import Backend
from src.constants import DEBATER_TIMEOUT
from src.shared.gatekeeper import APIGatekeeper

if TYPE_CHECKING:
    from src.cost import CostTracker

_CLAUDE_SKIP_PERMS = os.getenv("CLAUDE_SKIP_PERMISSIONS", "true").lower() == "true"


class CliBackend(Backend):
    """Shells out to ``claude --model <m> --print`` via Pro OAuth.

    Token counts are unavailable; records zeros to the cost tracker.
    Strips CLAUDE*/ANTHROPIC* env vars to prevent recursive invocation.
    Routes each subprocess call through APIGatekeeper for retry logic.
    """

    uses_memory: bool = True

    def __init__(self) -> None:
        """Initialise gatekeeper for CLI backend."""
        self._gatekeeper = APIGatekeeper("cli")

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
        """Run ``claude --model <model> --print`` with prompt on stdin.

        Args:
            name: Agent display name for cost tracking.
            model: Claude model ID passed as ``--model`` flag.
            prompt: Input piped to claude's stdin.
            cost_tracker: Receives zero token counts (CLI gives none).
            max_tokens: Unused by CLI; present for interface compatibility.
            temperature: Unused by CLI.
            system: Unused by CLI.

        Returns:
            Stripped stdout from the claude subprocess.

        Raises:
            RuntimeError: If the claude CLI exits with a non-zero code or times out.
        """
        env = {
            k: v for k, v in os.environ.items()
            if not k.startswith("CLAUDE") and not k.startswith("ANTHROPIC")
        }
        cmd = ["claude", "--model", model, "--print"]
        if _CLAUDE_SKIP_PERMS:
            cmd.append("--dangerously-skip-permissions")

        def _run() -> str:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=DEBATER_TIMEOUT,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"claude CLI failed (rc={result.returncode}): {result.stderr[:200]}"
                )
            return extract_response(result.stdout)

        output = self._gatekeeper.execute(_run)
        cost_tracker.record_call(name, 0, 0)
        return output


class OllamaCliBackend(Backend):
    """Shells out to ``ollama run <model>`` per agent turn.

    Requires the target model to be installed locally (``ollama pull <model>``).
    Temperature, system prompts, and token counts are unavailable.
    Routes each subprocess call through APIGatekeeper for retry logic.
    """

    def __init__(self) -> None:
        """Initialise gatekeeper for Ollama CLI backend."""
        self._gatekeeper = APIGatekeeper("ollama")

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
        """Run ``ollama run <model>`` with prompt on stdin.

        Args:
            name: Agent display name for cost tracking.
            model: Ollama model name (e.g. 'llama3.2').
            prompt: Input piped to ollama's stdin.
            cost_tracker: Receives zero token counts.
            max_tokens: Unused.
            temperature: Unused.
            system: Unused.

        Returns:
            Stripped stdout from the ollama subprocess.

        Raises:
            RuntimeError: If the ollama CLI exits with a non-zero code or times out.
        """
        def _run() -> str:
            result = subprocess.run(
                ["ollama", "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=DEBATER_TIMEOUT,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"ollama CLI failed (rc={result.returncode}): {result.stderr[:200]}"
                )
            return extract_response(result.stdout)

        output = self._gatekeeper.execute(_run)
        cost_tracker.record_call(name, 0, 0)
        return output
