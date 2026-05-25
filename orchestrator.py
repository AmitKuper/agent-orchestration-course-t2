"""Full debate lifecycle orchestration."""

from __future__ import annotations

import atexit
import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.agents.debate import DebateAgent
from src.agents.judge import JudgeAgent
from src.backends import make_backend, update_agent_file_model
from src.config import DebateConfig
from src.constants import COST_MD_PATH
from src.cost import CostTracker
from src.debate_helpers import execute_judge, execute_turn
from src.exceptions import InvalidTopicError  # re-exported for callers
from src.logger import setup_logger
from src.output import OutputManager
from src.state import ConversationState
from src.topic_validator import validate_topic

__all__ = ["DebateOrchestrator", "InvalidTopicError"]


def _flush_logger(logger: logging.Logger) -> None:
    """Flush and close all handlers on a logger."""
    for handler in logger.handlers:
        try:
            handler.flush()
            handler.close()
        except Exception:  # noqa: BLE001
            pass


class DebateOrchestrator:
    """Coordinates the full debate lifecycle without ever debating itself."""

    def __init__(self, config: DebateConfig, output_manager: OutputManager,
                 state: ConversationState, cost_tracker: CostTracker) -> None:
        """Bind all infrastructure dependencies and register atexit log flush."""
        self.config = config
        self.output = output_manager
        self.state = state
        self.cost_tracker = cost_tracker
        self._logger = setup_logger("debate.orchestrator", output_manager.log_path, config.log_level)
        self._agent_a: DebateAgent | None = None
        self._agent_b: DebateAgent | None = None
        self._judge: JudgeAgent | None = None
        self._backend = None
        atexit.register(self._flush_logs)
        atexit.register(self._close_backend)

    def validate_topic(self, topic: str) -> tuple[str, str]:
        """Check if topic is debatable; return (position_a, position_b).

        Raises:
            InvalidTopicError: If the topic cannot be split into two clear sides.
        """
        return validate_topic(topic, self.config.model_judge, make_backend(self.config.backend))

    def initialize_agents(self, position_a: str, position_b: str) -> None:
        """Construct DebateAgent A, B and JudgeAgent with assigned positions."""
        c = self.config
        self._backend = make_backend(c.backend, output_path=self.output.folder)
        if c.backend in ("cli", "ollama-cli"):
            update_agent_file_model(Path(".claude/agents/debate-agent.md"), c.model_a)
            update_agent_file_model(Path(".claude/agents/debate-judge.md"), c.model_judge)
        self._agent_a = DebateAgent(c.name_a, c.model_a, c, self.state, self.cost_tracker, position_a, c.name_b, self._backend)
        self._agent_b = DebateAgent(c.name_b, c.model_b, c, self.state, self.cost_tracker, position_b, c.name_a, self._backend)
        self._judge = JudgeAgent("Judge", c.model_judge, c, self.state, self.cost_tracker, c.name_a, c.name_b, self._backend)

    def run_turn(self, agent: DebateAgent, turn_number: int) -> str:
        """Run one turn: watchdog → retry → return response or empty string."""
        return execute_turn(agent, turn_number, self.config.turns, self.state, self._logger)

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
        self.cost_tracker.append_to_cost_md(Path(COST_MD_PATH))

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
        self.cost_tracker.append_to_cost_md(Path(COST_MD_PATH))

    def _run_judge(self) -> None:
        """Invoke the judge with timeout; write verdict to output or log failure."""
        execute_judge(self._judge, self.state, self.config.factcheck, self.output, self._logger)

    def _close_backend(self) -> None:
        """Close the backend (terminates persistent subprocesses if any)."""
        if self._backend is not None:
            self._backend.close()

    def _flush_logs(self) -> None:
        """Flush and close all handlers on the orchestrator logger."""
        _flush_logger(self._logger)
