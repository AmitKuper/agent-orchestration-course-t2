"""Module-level helpers for debate turn execution and judge invocation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.constants import DEBATER_TIMEOUT, JUDGE_TIMEOUT
from src.watchdog import Watchdog

if TYPE_CHECKING:
    from src.agents.debate import DebateAgent
    from src.agents.judge import JudgeAgent
    from src.output import OutputManager
    from src.state import ConversationState


def execute_turn(
    agent: DebateAgent,
    turn_number: int,
    total_turns: int,
    state: ConversationState,
    logger: logging.Logger,
) -> str:
    """Run one agent turn with watchdog timeout and retry logic.

    Args:
        agent: The debater to invoke on this turn.
        turn_number: Current turn index (1-based).
        total_turns: Total turns in the debate (used to compute remaining count).
        state: Live conversation state used to build the prompt context.
        logger: Logger for progress and warning messages.

    Returns:
        Accepted JSONL response string, or empty string on failure.
    """
    turns_remaining = (total_turns // 2) - ((turn_number + 1) // 2)
    prompt = agent.build_prompt(state.get_turns(), turn_number, turns_remaining)
    timed_out = [False]

    def on_timeout() -> None:
        timed_out[0] = True
        logger.warning("Watchdog: %s timed out on turn %d.", agent.name, turn_number)

    with Watchdog(DEBATER_TIMEOUT, on_timeout):
        response = agent.invoke_with_retry(prompt)
    if not response:
        logger.error("Turn %d skipped — %s failed all retries.", turn_number, agent.name)
        return ""
    logger.info("Turn %d/%d accepted from %s.", turn_number, total_turns, agent.name)
    return response


def execute_judge(
    judge: JudgeAgent,
    state: ConversationState,
    factcheck: bool,
    output: OutputManager,
    logger: logging.Logger,
) -> None:
    """Invoke the judge agent with timeout and write the verdict file.

    Args:
        judge: Configured JudgeAgent instance.
        state: Completed conversation state providing all debate turns.
        factcheck: Whether factual accuracy checking is enabled.
        output: OutputManager for writing the verdict JSON file.
        logger: Logger for status and error messages.
    """
    timed_out = [False]

    def on_timeout() -> None:
        timed_out[0] = True

    with Watchdog(JUDGE_TIMEOUT, on_timeout):
        response = judge.invoke_with_retry(
            judge.build_scoring_prompt(state.get_turns(), factcheck)
        )
    if timed_out[0] or not response:
        logger.error("Judge failed — state preserved for resume.")
        return
    try:
        path = output.write_result(judge.parse_verdict(response))
        logger.info("Verdict written to %s.", path)
    except ValueError as exc:
        logger.error("Invalid judge verdict: %s", exc)
