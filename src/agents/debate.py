"""Debate agent: prompt builder and Claude API invocation for debate turns."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.config import DebateConfig
    from src.cost import CostTracker
    from src.state import ConversationState


class DebateAgent(BaseAgent):
    """Argues an assigned position in a structured debate.

    Builds a turn prompt from history, position, and turn metadata,
    then calls the Claude API and parses the JSONL response.
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
    ) -> None:
        """Initialise with assigned debate position and opponent identity.

        Args:
            name: This agent's display name.
            model: Claude model ID for API calls.
            config: Fully resolved debate configuration.
            state: Shared conversation state.
            cost_tracker: Token usage recorder.
            position: The side this agent must always defend.
            opponent_name: Display name of the opposing debater.
        """
        super().__init__(name, model, config, state, cost_tracker)
        self.position = position
        self.opponent_name = opponent_name
        self._client = anthropic.Anthropic()

    def build_prompt(
        self, history: list[dict], turn_number: int, turns_remaining: int
    ) -> str:
        """Construct the full turn prompt for this debate agent.

        Args:
            history: All completed turns from the conversation state.
            turn_number: Current 1-based turn number.
            turns_remaining: How many turns this agent has left after this one.

        Returns:
            Formatted prompt string ready to send to Claude.
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

    def _invoke(self, prompt: str) -> str:
        """Call the Claude API and return the raw response text.

        Records input/output token usage to the cost tracker after each call.

        Args:
            prompt: Full prompt to send to Claude.

        Returns:
            Raw string response from the model.
        """
        message = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        self.cost_tracker.record_call(
            self.name,
            message.usage.input_tokens,
            message.usage.output_tokens,
        )
        return message.content[0].text
