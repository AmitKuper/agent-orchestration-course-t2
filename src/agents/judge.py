"""Judge agent: scores a completed debate and declares a winner."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent, load_agent_def
from src.constants import MAX_TOKENS_JUDGE
from src.validator import ValidationResult

_SCORE_KEYS = ("logic", "evidence", "clarity", "persuasiveness")

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
        system = load_agent_def(".claude/agents/debate-judge.md", {
            "AGENT_A_NAME": agent_a_name,
            "AGENT_B_NAME": agent_b_name,
            "FACTCHECK_ENABLED": str(config.factcheck).lower(),
        })
        super().__init__(name, model, config, state, cost_tracker, backend, system or None)
        self.agent_a_name = agent_a_name
        self.agent_b_name = agent_b_name
        self._max_tokens = MAX_TOKENS_JUDGE

    def _validate_response(self, response: str) -> ValidationResult:
        """Validate a judge verdict using the verdict schema instead of debate-turn schema.

        Args:
            response: Raw JSON string from the judge backend.

        Returns:
            ValidationResult from validate_judge_verdict().
        """
        return self._validator.validate_judge_verdict(
            response, self.agent_a_name, self.agent_b_name
        )

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
        """Parse and validate the judge response against the required schema.

        Accepts score keys in any case (e.g. 'Logic' or 'logic') and
        normalises them to lowercase. Computes 'total' from the four criteria
        so the model never needs to sum correctly itself.

        Args:
            response: Raw JSON string from the judge backend.

        Returns:
            Validated, normalised verdict dict.

        Raises:
            ValueError: If JSON is invalid or the schema is not satisfied.
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Judge returned invalid JSON: {exc}") from exc
        return self._validate_verdict(data)

    def _validate_verdict(self, data: dict) -> dict:
        """Enforce the verdict schema and normalise score keys to lowercase.

        Args:
            data: Parsed JSON dict from the judge.

        Returns:
            Normalised verdict dict with computed totals.

        Raises:
            ValueError: On any missing or incorrectly typed field.
        """
        if not isinstance(data.get("winner"), str) or not data["winner"].strip():
            raise ValueError("'winner' must be a non-empty string.")
        scores = data.get("scores")
        if not isinstance(scores, dict):
            raise ValueError("'scores' must be a dict keyed by agent name.")
        for agent in (self.agent_a_name, self.agent_b_name):
            if agent not in scores:
                raise ValueError(f"'scores' missing entry for '{agent}'.")
            entry = scores[agent]
            if not isinstance(entry, dict):
                raise ValueError(f"scores['{agent}'] must be a dict of criteria.")
            normed: dict = {}
            for key in _SCORE_KEYS:
                val = entry.get(key, entry.get(key.capitalize()))
                if val is None:
                    raise ValueError(f"scores['{agent}'] missing '{key}'.")
                if not isinstance(val, (int, float)) or not 0 <= val <= 10:
                    raise ValueError(f"scores['{agent}']['{key}'] must be 0–10.")
                normed[key] = int(val)
            normed["total"] = sum(normed.values())
            scores[agent] = normed
        if not isinstance(data.get("explanation"), str) or not data["explanation"].strip():
            raise ValueError("'explanation' must be a non-empty string.")
        data.setdefault("tiebreaker", None)
        data.setdefault("factcheck_flags", [])
        return data
