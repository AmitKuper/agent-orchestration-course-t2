"""Debate agent: prompt builder for debate turns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent, load_agent_def

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
        return (
            f"You are {self.name}, debating the position: {self.position}\n"
            f"Opponent: {self.opponent_name} | "
            f"Turn: {turn_number} | Turns remaining after this: {turns_remaining}\n"
            f"Minimum response length: {self.config.min_response_len} characters\n\n"
            f"Conversation history:\n{self._format_history(history)}\n\n"
            f"Always defend your position — never concede. Use web search for evidence.\n"
            f"Respond with exactly one JSONL line:\n"
            f'{{"agent": "{self.name}", "turn": {turn_number}, '
            f'"argument": "...", "references": ["..."]}}'
        )

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
