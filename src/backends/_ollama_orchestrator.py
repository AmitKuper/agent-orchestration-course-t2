"""Ollama single-shot orchestrator — the model generates the full debate in one call."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from src.backends._ansi import render_ansi
from src.backends._orchestrator_base import OrchestratorBackend

_DONE_THINKING = "...done thinking."

if TYPE_CHECKING:
    from src.config import DebateConfig


class OllamaOrchestratorBackend(OrchestratorBackend):
    """Instructs an Ollama model to self-orchestrate a complete debate in one shot.

    Sends a single comprehensive prompt to ``ollama run <model>`` asking the
    model to generate all debate turns and a judge verdict as JSONL output.
    The model manages both sides of the argument and the scoring itself.
    """

    def run_debate(
        self,
        config: DebateConfig,
        position_a: str,
        position_b: str,
    ) -> tuple[list[dict], dict | None]:
        """Send a single prompt to Ollama and parse the full debate output.

        Returns:
            Tuple of (turns, verdict). turns may be partial; verdict is None if unparseable.
        """
        prompt = self._build_prompt(config, position_a, position_b)
        result = subprocess.run(
            ["ollama", "run", config.model_a],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        rendered = render_ansi(result.stdout)
        if _DONE_THINKING in rendered:
            rendered = rendered.split(_DONE_THINKING, 1)[1]
        return self._parse(rendered)

    def _build_prompt(self, config: DebateConfig, pos_a: str, pos_b: str) -> str:
        """Construct the single-shot debate generation prompt."""
        turns = config.turns
        a, b = config.name_a, config.name_b
        score_schema = (
            f'"{a}": {{"logic": N, "evidence": N, "clarity": N, "persuasiveness": N, "total": N}}, '
            f'"{b}": {{"logic": N, "evidence": N, "clarity": N, "persuasiveness": N, "total": N}}'
        )
        return (
            f"You will generate a complete structured debate between two agents.\n\n"
            f"Topic: {config.topic}\n"
            f"{a} argues: {pos_a}\n"
            f"{b} argues: {pos_b}\n\n"
            f"Rules:\n"
            f"- Generate exactly {turns} turns, alternating: odd turns = {a}, even turns = {b}\n"
            f"- Each agent must defend their position aggressively and rebut the previous turn\n"
            f"- Arguments must be substantive (min {config.min_response_len} chars each)\n\n"
            f"Output ONLY the following {turns + 1} JSON lines — nothing else:\n"
            f"Turns (one per line):\n"
            f'{{"agent":"name","turn":N,"argument":"...","references":["..."]}}\n\n'
            f"Then one verdict line:\n"
            f'{{"winner":"name","scores":{{{score_schema}}},'
            f'"tiebreaker":null,"explanation":"...","factcheck_flags":[]}}\n\n'
            f"Begin now. Output only raw JSON lines, no markdown, no explanation."
        )

    def _parse(self, raw: str) -> tuple[list[dict], dict | None]:
        """Extract turn and verdict dicts from rendered model output.

        Handles both one-JSON-per-line and word-wrapped output where a JSON
        object may span multiple terminal lines.
        """
        turns: list[dict] = []
        verdict: dict | None = None

        def _accept(obj: dict) -> None:
            nonlocal verdict
            if "agent" in obj and "turn" in obj and "argument" in obj:
                turns.append(obj)
            elif "winner" in obj and "scores" in obj:
                verdict = obj

        # First pass: try each line as a complete JSON object.
        remaining: list[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    _accept(json.loads(line))
                    continue
                except json.JSONDecodeError:
                    pass
            remaining.append(line)

        # Second pass: scan joined text for brace-balanced JSON objects.
        joined = " ".join(remaining)
        depth = start = 0
        in_obj = False
        for idx, ch in enumerate(joined):
            if ch == "{":
                if not in_obj:
                    start = idx
                    in_obj = True
                depth += 1
            elif ch == "}" and in_obj:
                depth -= 1
                if depth == 0:
                    try:
                        _accept(json.loads(joined[start : idx + 1]))
                    except json.JSONDecodeError:
                        pass
                    in_obj = False

        return turns, verdict
