"""DebateSDK — unified entry point for running and resuming AI debates.

External consumers (CLI, tests, notebooks) interact with this class only;
they never call DebateOrchestrator directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import DebateConfig
from src.constants import FILE_CONVERSATION
from src.cost import CostTracker
from src.output import OutputManager
from src.state import ConversationState


@dataclass
class DebateResult:
    """Structured result returned by DebateSDK after a completed run.

    Attributes:
        run_dir: Path to the output folder for this run.
        verdict: Parsed judge verdict dict, or None if judge failed.
        cost_summary: Token usage summary across all agents.
        turns_completed: Number of turns successfully recorded.
        errors: Non-fatal errors encountered during the run.
    """

    run_dir: Path
    verdict: dict[str, Any] | None
    cost_summary: dict[str, Any]
    turns_completed: int
    errors: list[str] = field(default_factory=list)


class DebateSDK:
    """Single entry point for all debate platform operations.

    Hides orchestration internals from callers; provides run() and resume().
    """

    def run(self, config: DebateConfig, argv: list[str] | None = None) -> DebateResult:
        """Run a full debate from scratch and return structured results.

        Args:
            config: Fully resolved debate configuration.
            argv: sys.argv to record in run_info.json; defaults to empty list.

        Returns:
            DebateResult with output path, verdict, and cost summary.
        """
        import sys  # noqa: PLC0415
        from orchestrator import DebateOrchestrator  # noqa: PLC0415

        output = OutputManager.create_run_folder(config.outdir)
        output.write_run_info(config.backend, argv or sys.argv)
        state = ConversationState(output.conversation_path)
        tracker = CostTracker(output.folder.name)
        orch = DebateOrchestrator(config, output, state, tracker)
        errors: list[str] = []
        try:
            orch.run_debate()
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
        return self._build_result(output, state, tracker, errors)

    def resume(self, config: DebateConfig) -> DebateResult:
        """Resume an interrupted debate from the last completed turn.

        Args:
            config: Configuration with outdir pointing to the existing run folder.

        Returns:
            DebateResult with updated verdict and cost summary.
        """
        from orchestrator import DebateOrchestrator

        folder = Path(config.outdir)
        output = OutputManager(folder)
        state = ConversationState.load_from_file(folder / FILE_CONVERSATION)
        tracker = CostTracker(folder.name)
        orch = DebateOrchestrator(config, output, state, tracker)
        errors: list[str] = []
        try:
            orch.resume_debate()
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
        return self._build_result(output, state, tracker, errors)

    def _build_result(
        self,
        output: OutputManager,
        state: ConversationState,
        tracker: CostTracker,
        errors: list[str],
    ) -> DebateResult:
        """Assemble a DebateResult from the post-run infrastructure state."""
        verdict = None
        result_path = output.result_path()
        if result_path.exists():
            verdict = json.loads(result_path.read_text(encoding="utf-8"))
        return DebateResult(
            run_dir=output.folder,
            verdict=verdict,
            cost_summary=tracker.get_run_summary(),
            turns_completed=state.last_turn_number(),
            errors=errors,
        )
