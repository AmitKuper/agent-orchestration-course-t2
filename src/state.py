"""JSONL-based conversation state management for the debate platform."""

from __future__ import annotations

import json
from pathlib import Path


class ConversationState:
    """Manages reading and writing the JSONL conversation state file.

    The JSONL file is the single source of truth for resume state.
    Only fully completed turns are written. Each line is one debate turn.
    Append mode writes guarantee that interruption cannot corrupt prior turns.
    """

    def __init__(self, path: Path) -> None:
        """Bind this state instance to a specific JSONL file path.

        Args:
            path: Path where the JSONL conversation file will be written.
        """
        self._path = path
        self._turns: list[dict] = []

    @classmethod
    def load_from_file(cls, path: Path) -> ConversationState:
        """Load all completed turns from an existing JSONL file.

        Args:
            path: Path to the JSONL conversation file.

        Returns:
            ConversationState with all turns populated from disk.
        """
        state = cls(path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                state._turns = [json.loads(line) for line in f if line.strip()]
        return state

    def append_turn(self, turn: dict) -> None:
        """Atomically append a completed turn to the JSONL file.

        Opens in append mode so any interruption leaves prior turns intact.
        The in-memory list is updated after a successful write.

        Args:
            turn: Dict representing one completed debate turn.
        """
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(turn) + "\n")
            f.flush()
        self._turns.append(turn)

    def get_turns(self) -> list[dict]:
        """Return all completed turns in order."""
        return list(self._turns)

    def last_turn_number(self) -> int:
        """Return the turn number of the last completed turn, or 0 if none."""
        return self._turns[-1].get("turn", 0) if self._turns else 0

    def is_complete(self, total_turns: int) -> bool:
        """Return True if the expected number of turns have been completed."""
        return len(self._turns) >= total_turns

    @staticmethod
    def needs_resume(conversation_path: Path) -> bool:
        """Return True if a non-empty conversation file exists at path.

        Args:
            conversation_path: Full path to the expected JSONL file.
        """
        return conversation_path.exists() and conversation_path.stat().st_size > 0
