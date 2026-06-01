"""Debate agent: prompt builder and novelty validation for debate turns."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent, load_agent_def
from src.validator import ValidationResult

if TYPE_CHECKING:
    from src.backends import Backend
    from src.config import DebateConfig
    from src.cost import CostTracker
    from src.state import ConversationState


class DebateAgent(BaseAgent):
    """Argues an assigned position in a structured debate.

    Builds a turn prompt from history, position, and turn metadata,
    then delegates invocation to the configured backend.
    """

    def __init__(
        self,
        name: str,
        model: str,
        config: DebateConfig,
        state: ConversationState,
        cost_tracker: CostTracker,
        position: str,
        opponent_name: str,
        backend: Backend,
    ) -> None:
        """Initialise with assigned debate position and opponent identity.

        Args:
            name: This agent's display name.
            model: Claude model ID passed to the backend.
            config: Fully resolved debate configuration.
            state: Shared conversation state.
            cost_tracker: Token usage recorder.
            position: The side this agent must always defend.
            opponent_name: Display name of the opposing debater.
            backend: Invocation backend (ApiBackend or CliBackend).
        """
        system = load_agent_def(".claude/agents/debate-agent.md", {
            "AGENT_NAME": name,
            "OPPONENT_NAME": opponent_name,
            "POSITION": position,
            "MIN_RESPONSE_LEN": str(config.min_response_len),
        })
        super().__init__(name, model, config, state, cost_tracker, backend, system or None)
        self.position = position
        self.opponent_name = opponent_name
        self._assigned_position = position
        self._current_turn: int | None = None

    def build_prompt(
        self, history: list[dict], turn_number: int, turns_remaining: int
    ) -> str:
        """Construct the full turn prompt for this debate agent.

        Args:
            history: All completed turns from the conversation state.
            turn_number: Current 1-based turn number.
            turns_remaining: How many turns this agent has left after this one.

        Returns:
            Formatted prompt string ready to send to the backend.
        """
        self._current_turn = turn_number
        history_section = (
            "" if self._backend.uses_memory
            else f"Debate so far:\n{self._format_history(history)}\n\n"
        )
        return (
            f"You are {self.name}. Your position: {self.position}\n"
            f"You are debating directly against {self.opponent_name}. "
            f"Turn: {turn_number} | Your turns remaining after this: {turns_remaining}\n"
            f"Minimum response length: {self.config.min_response_len} characters\n\n"
            f"{history_section}"
            f"Address {self.opponent_name} directly. Never concede. Use web search for evidence.\n"
            f"Respond with exactly one JSONL line:\n"
            f'{{"agent": "{self.name}", "turn": {turn_number}, '
            f'"argument": "...", "references": ["..."]}}'
        )

    def _validate_response(self, response: str) -> ValidationResult:
        """Validate debate-turn JSON, enforcing expected agent name and turn number."""
        return self._validator.validate(
            response,
            self.config.min_response_len,
            expected_agent=self.name,
            expected_turn=self._current_turn,
            require_references=getattr(self.config, "require_references", False),
        )

    def _extra_validate(self, response: str) -> ValidationResult:
        """Reject responses that are too similar to this agent's prior turns."""
        try:
            argument = json.loads(response).get("argument", response)
        except (json.JSONDecodeError, AttributeError):
            argument = response
        prior = [
            t.get("argument", "")
            for t in self.state.get_turns()
            if t.get("agent") == self.name
        ]
        return self._validator.validate_novelty(argument, prior)

    def _format_history(self, turns: list[dict]) -> str:
        """Format conversation turns as readable text for prompt injection.

        Args:
            turns: List of turn dicts with keys: agent, turn, argument.

        Returns:
            Multiline string with each turn labelled and separated.
        """
        if not turns:
            return "(No prior turns — this is the opening argument.)"
        lines = []
        for t in turns:
            lines.append(f"[Turn {t.get('turn', '?')} — {t.get('agent', 'unknown')}]")
            lines.append(t.get("argument", ""))
            lines.append("")
        return "\n".join(lines)
