"""Token usage recording and cost estimation for all agent calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Approximate USD cost per million tokens (claude-sonnet-4-6)
_COST_PER_M_INPUT = 3.0
_COST_PER_M_OUTPUT = 15.0

_COST_MD_HEADER = (
    "# Cost Tracking\n\n"
    "| Timestamp | Run ID | Input Tokens | Output Tokens | Est. Cost (USD) |\n"
    "|-----------|--------|-------------|--------------|----------------|\n"
)


@dataclass
class CallRecord:
    """Token usage for a single agent API call."""

    agent_name: str
    input_tokens: int
    output_tokens: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def estimated_cost_usd(self) -> float:
        """Return the estimated USD cost for this call based on token counts."""
        return (
            self.input_tokens / 1_000_000 * _COST_PER_M_INPUT
            + self.output_tokens / 1_000_000 * _COST_PER_M_OUTPUT
        )


class CostTracker:
    """Accumulates token usage across all agent calls in one debate run."""

    def __init__(self, run_id: str) -> None:
        """Initialise the tracker for a specific debate run.

        Args:
            run_id: Unique identifier for this run, used in cost.md rows.
        """
        self._run_id = run_id
        self._records: list[CallRecord] = []

    def record_call(self, agent_name: str, input_tokens: int, output_tokens: int) -> None:
        """Record token counts for one completed agent call.

        Args:
            agent_name: Name of the agent that made the call.
            input_tokens: Input token count from the API response.
            output_tokens: Output token count from the API response.
        """
        self._records.append(CallRecord(agent_name, input_tokens, output_tokens))

    def get_run_summary(self) -> dict:
        """Return aggregated token totals and estimated cost for this run."""
        total_in = sum(r.input_tokens for r in self._records)
        total_out = sum(r.output_tokens for r in self._records)
        total_cost = sum(r.estimated_cost_usd() for r in self._records)
        return {
            "run_id": self._run_id,
            "calls": len(self._records),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "estimated_cost_usd": round(total_cost, 6),
        }

    def append_to_cost_md(self, cost_md_path: Path) -> None:
        """Append a summary row for this run to docs/cost.md.

        Creates the file with a header if it does not yet exist.

        Args:
            cost_md_path: Path to the docs/cost.md file.
        """
        summary = self.get_run_summary()
        if not cost_md_path.exists():
            cost_md_path.write_text(_COST_MD_HEADER, encoding="utf-8")
        row = (
            f"| {datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"| {summary['run_id']} "
            f"| {summary['total_input_tokens']} "
            f"| {summary['total_output_tokens']} "
            f"| ${summary['estimated_cost_usd']:.6f} |\n"
        )
        with open(cost_md_path, "a", encoding="utf-8") as f:
            f.write(row)
