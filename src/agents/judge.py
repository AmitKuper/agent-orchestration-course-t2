"""Judge agent: scores a completed debate and declares a winner."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.constants import MAX_TOKENS_JUDGE

if TYPE_CHECKING:
    from src.backends import Backend
    from src.config import DebateConfig
    from src.cost import CostTracker
    from src.state import ConversationState


class JudgeAgent(BaseAgent):
    """Evaluates a completed debate and produces a structured scoring verdict.

    Scores each debater on Logic, Evidence, Clarity, and Persuasiveness.
    No ties allowed — applies a tiebreaker criterion when totals are equal.
    """

    def __init__(
        self,
        name: str,
        model: str,
        config: DebateConfig,
        state: ConversationState,
        cost_tracker: CostTracker,
        agent_a_name: str,
        agent_b_name: str,
        backend: Backend,
    ) -> None:
        """Initialise with the display names of both debaters.

        Args:
            name: Display name for this judge instance.
            model: Claude model ID passed to the backend.
            config: Fully resolved debate configuration.
            state: Shared conversation state.
            cost_tracker: Token usage recorder.
            agent_a_name: Display name of debater A.
            agent_b_name: Display name of debater B.
            backend: Invocation backend (ApiBackend or CliBackend).
        """
        super().__init__(name, model, config, state, cost_tracker, backend)
        self.agent_a_name = agent_a_name
        self.agent_b_name = agent_b_name
        self._max_tokens = MAX_TOKENS_JUDGE

    def build_scoring_prompt(self, history: list[dict], factcheck_enabled: bool) -> str:
        """Build the judge scoring prompt from the full debate transcript.

        Args:
            history: All completed turns from the conversation state.
            factcheck_enabled: Whether to flag fabricated or unverifiable claims.

        Returns:
            Prompt string instructing Claude to score and declare a winner.
        """
        transcript = "\n\n".join(
            f"[Turn {t.get('turn')} — {t.get('agent')}]\n{t.get('argument', '')}"
            for t in history
        )
        factcheck_note = (
            "Flag fabricated or unverifiable claims in factcheck_flags."
            if factcheck_enabled
            else "Set factcheck_flags to []."
        )
        return (
            f"You are an impartial debate judge. Score {self.agent_a_name} and "
            f"{self.agent_b_name} on Logic, Evidence, Clarity, and Persuasiveness "
            f"(0–10 each). No ties — use a tiebreaker if totals are equal. "
            f"{factcheck_note}\n\n"
            f"Transcript:\n{transcript}\n\n"
            f"Return exactly one JSON object: winner, scores, tiebreaker, "
            f"explanation, factcheck_flags."
        )

    def parse_verdict(self, response: str) -> dict:
        """Extract and return the structured verdict dict from the judge response.

        Args:
            response: Raw string expected to be a valid JSON object.

        Returns:
            Parsed verdict dict with winner, scores, and explanation.

        Raises:
            ValueError: If the response cannot be parsed as valid JSON.
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Judge returned invalid JSON: {exc}") from exc
