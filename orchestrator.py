"""Full debate lifecycle orchestration."""

from __future__ import annotations

import atexit
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from src.agents.debate import DebateAgent
from src.agents.judge import JudgeAgent
from src.backends import make_backend
from src.config import DebateConfig
from src.constants import DEBATER_TIMEOUT, JUDGE_TIMEOUT
from src.cost import CostTracker
from src.exceptions import InvalidTopicError  # re-exported for callers
from src.logger import setup_logger
from src.output import OutputManager
from src.state import ConversationState
from src.topic_validator import validate_topic
from src.validator import ResponseValidator
from src.watchdog import Watchdog

__all__ = ["DebateOrchestrator", "InvalidTopicError"]

_COST_MD = Path("docs/cost.md")


class DebateOrchestrator:
    """Coordinates the full debate lifecycle without ever debating itself.

    Owns topic validation, agent initialization, turn sequencing, state
    persistence, and judge invocation.
    """

    def __init__(
        self,
        config: DebateConfig,
        output_manager: OutputManager,
        state: ConversationState,
        cost_tracker: CostTracker,
    ) -> None:
        """Bind all infrastructure dependencies and register atexit log flush."""
        self.config = config
        self.output = output_manager
        self.state = state
        self.cost_tracker = cost_tracker
        self._validator = ResponseValidator()
        self._logger = setup_logger(
            "debate.orchestrator", output_manager.log_path, config.log_level
        )
        self._agent_a: Optional[DebateAgent] = None
        self._agent_b: Optional[DebateAgent] = None
        self._judge: Optional[JudgeAgent] = None
        atexit.register(self._flush_logs)

    def validate_topic(self, topic: str) -> tuple[str, str]:
        """Check if topic is debatable; return (position_a, position_b).

        Raises:
            InvalidTopicError: If the topic cannot be split into two clear sides.
        """
        backend = make_backend(self.config.backend)
        return validate_topic(topic, self.config.model_judge, backend)

    def initialize_agents(self, position_a: str, position_b: str) -> None:
        """Construct DebateAgent A, B and JudgeAgent with assigned positions."""
        c = self.config
        backend = make_backend(c.backend)
        self._agent_a = DebateAgent(
            c.name_a, c.model_a, c, self.state, self.cost_tracker,
            position_a, c.name_b, backend,
        )
        self._agent_b = DebateAgent(
            c.name_b, c.model_b, c, self.state, self.cost_tracker,
            position_b, c.name_a, backend,
        )
        self._judge = JudgeAgent(
            "Judge", c.model_judge, c, self.state, self.cost_tracker,
            c.name_a, c.name_b, backend,
        )

    def run_turn(self, agent: DebateAgent, turn_number: int) -> str:
        """Run one turn: watchdog → retry → validate JSON → return or skip.

        Returns:
            Accepted JSONL response string, or empty string if the turn failed.
        """
        turns_remaining = (self.config.turns // 2) - ((turn_number + 1) // 2)
        prompt = agent.build_prompt(
            self.state.get_turns(), turn_number, turns_remaining
        )
        timed_out = [False]

        def on_timeout() -> None:
            timed_out[0] = True
            self._logger.warning(
                "Watchdog: %s timed out on turn %d.", agent.name, turn_number
            )

        with Watchdog(DEBATER_TIMEOUT, on_timeout):
            response = agent.invoke_with_retry(prompt)

        if not response:
            self._logger.warning(
                "Turn %d skipped — %s failed all retries.", turn_number, agent.name
            )
            return ""
        self._logger.info(
            "Turn %d/%d accepted from %s.", turn_number, self.config.turns, agent.name
        )
        return response

    def _run_turns(self, start_turn: int) -> None:
        """Alternate A/B from start_turn to config.turns, appending each to state."""
        agents = [self._agent_a, self._agent_b]
        for turn in range(start_turn, self.config.turns + 1):
            agent = agents[(turn - 1) % 2]
            self._logger.info("Turn %d/%d — %s", turn, self.config.turns, agent.name)
            response = self.run_turn(agent, turn)
            if response:
                self.state.append_turn(json.loads(response))

    def run_debate(self) -> None:
        """Full lifecycle: validate topic → init agents → all turns → judge → cost."""
        self._logger.info("Debate starting: %s", self.config.topic)
        pos_a, pos_b = self.validate_topic(self.config.topic)
        self._logger.info("Positions — A: %s | B: %s", pos_a, pos_b)
        self.initialize_agents(pos_a, pos_b)
        self.output.write_config(asdict(self.config))
        self._run_turns(1)
        self._run_judge()
        self.cost_tracker.append_to_cost_md(_COST_MD)

    def resume_debate(self) -> None:
        """Continue from the last completed turn.

        Raises:
            RuntimeError: If the debate is already complete.
        """
        if self.state.is_complete(self.config.turns):
            raise RuntimeError("Debate is already complete — cannot resume.")
        start = self.state.last_turn_number() + 1
        self._logger.info("Resuming from turn %d.", start)
        pos_a, pos_b = self.validate_topic(self.config.topic)
        self.initialize_agents(pos_a, pos_b)
        self._run_turns(start)
        self._run_judge()
        self.cost_tracker.append_to_cost_md(_COST_MD)

    def _run_judge(self) -> None:
        """Invoke the judge with timeout; write verdict to output or log failure."""
        timed_out = [False]

        def on_timeout() -> None:
            timed_out[0] = True

        with Watchdog(JUDGE_TIMEOUT, on_timeout):
            response = self._judge.invoke_with_retry(
                self._judge.build_scoring_prompt(
                    self.state.get_turns(), self.config.factcheck
                )
            )
        if timed_out[0] or not response:
            self._logger.error("Judge failed — state preserved for resume.")
            return
        try:
            path = self.output.write_result(self._judge.parse_verdict(response))
            self._logger.info("Verdict written to %s.", path)
        except ValueError as exc:
            self._logger.error("Invalid judge verdict: %s", exc)

    def _flush_logs(self) -> None:
        """Flush and close all handlers on the orchestrator logger."""
        for handler in self._logger.handlers:
            try:
                handler.flush()
                handler.close()
            except Exception:  # noqa: BLE001
                pass
