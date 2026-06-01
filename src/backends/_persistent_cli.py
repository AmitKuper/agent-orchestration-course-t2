"""Persistent CLI backend — keeps a claude subprocess alive per agent.

EXPERIMENTAL: this backend is not part of the default recommended workflow
and is not exercised in CI against a real Claude CLI process. Use
``claude-cli-agents`` (per-turn subprocess) for the recommended CLI path.

Limitations:
- Does not route calls through APIGatekeeper (subprocess stdin/stdout pattern
  does not map cleanly to the gatekeeper callable model).
- Timeout is enforced at the Watchdog level (debate_helpers.py), not inside
  the backend itself.
- Requires Claude Code CLI installed and a Pro subscription.
- Set ``CLAUDE_SKIP_PERMISSIONS=false`` to disable --dangerously-skip-permissions.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from src.backends._base import Backend

if TYPE_CHECKING:
    from src.cost import CostTracker

_CLAUDE_SKIP_PERMS = os.getenv("CLAUDE_SKIP_PERMISSIONS", "true").lower() == "true"


class PersistentCliBackend(Backend):
    """Keeps one ``claude`` subprocess alive per agent for the full debate.

    Each agent gets its own persistent session so its system prompt and
    conversation context accumulate naturally without reloading on every turn.

    Uses ``--output-format stream-json`` so end-of-response is detected
    by the ``result`` event rather than process exit.

    An empty ``.claude/`` directory is created inside ``workdir`` so the
    subprocess cannot walk up and load the project's CLAUDE.md or docs.
    """

    uses_memory: bool = False

    def __init__(self, workdir: Path) -> None:
        """Prepare isolated workdir and stripped environment.

        Args:
            workdir: Run output folder used as subprocess cwd. An empty
                ``.claude/`` subdirectory is created here to prevent the
                subprocess from scanning parent project directories.
        """
        self._workdir = workdir
        self._sessions: dict[str, subprocess.Popen] = {}
        self._env = {
            k: v for k, v in os.environ.items()
            if not k.startswith("CLAUDE") and not k.startswith("ANTHROPIC")
        }
        (workdir / ".claude").mkdir(parents=True, exist_ok=True)

    def _start_session(self, name: str, model: str, system: str) -> None:
        """Spawn a persistent claude subprocess for one agent.

        Args:
            name: Agent name, used as session key.
            model: Claude model ID.
            system: System prompt text injected via ``--system-prompt``.
        """
        cmd = [
            "claude", "--model", model,
            "--output-format", "stream-json",
            "--system-prompt", system,
        ]
        if _CLAUDE_SKIP_PERMS:
            cmd.append("--dangerously-skip-permissions")
        self._sessions[name] = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=self._workdir,
            env=self._env,
        )

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
        """Send prompt to the agent's persistent session and return the response.

        Starts the session on first call using the provided system prompt.
        Reads stream-json events until a ``result`` event signals turn completion.

        Args:
            name: Agent name — selects or starts the right session.
            model: Model ID, used only when starting the session.
            prompt: User-turn text for this debate round.
            cost_tracker: Receives zero token counts (CLI gives none).
            max_tokens: Unused.
            temperature: Unused.
            system: System prompt; only used when the session is first started.

        Returns:
            Extracted assistant text from the response.

        Raises:
            RuntimeError: If the subprocess has died unexpectedly.
        """
        if name not in self._sessions:
            self._start_session(name, model, system or "")
        proc = self._sessions[name]
        if proc.poll() is not None:
            raise RuntimeError(
                f"Session for {name!r} has died (rc={proc.returncode})"
            )
        proc.stdin.write(prompt + "\n")
        proc.stdin.flush()
        response = ""
        for line in iter(proc.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        response += block["text"]
            elif event.get("type") == "result":
                break
        cost_tracker.record_call(name, 0, 0)
        return response.strip()

    def close(self) -> None:
        """Terminate all active agent sessions."""
        for proc in self._sessions.values():
            try:
                proc.stdin.close()
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()
        self._sessions.clear()
