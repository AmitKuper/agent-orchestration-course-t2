"""Output folder creation and canonical file path management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.constants import FILE_CONFIG, FILE_CONVERSATION, FILE_LOG, FILE_RESULT_PREFIX


class OutputManager:
    """Creates and manages the per-run output folder and all file paths within it.

    Each debate run gets a dedicated timestamped folder. Result files use
    unique timestamps so multiple judge runs never overwrite each other.
    A convenience ``result.json`` is also written as the latest result.
    """

    def __init__(self, run_folder: Path) -> None:
        """Bind this manager to an already-created run folder.

        Args:
            run_folder: Path to the dedicated output folder for this run.
        """
        self._folder = run_folder

    @classmethod
    def create_run_folder(cls, outdir: str) -> OutputManager:
        """Create a timestamped output folder for a new debate run.

        Args:
            outdir: Base output directory (already includes topic path).

        Returns:
            OutputManager bound to the newly created folder.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = Path(outdir) / timestamp
        folder.mkdir(parents=True, exist_ok=True)
        return cls(folder)

    @property
    def folder(self) -> Path:
        """Return the root run folder path."""
        return self._folder

    @property
    def config_path(self) -> Path:
        """Return the path for the config JSON file."""
        return self._folder / FILE_CONFIG

    @property
    def conversation_path(self) -> Path:
        """Return the path for the JSONL conversation file."""
        return self._folder / FILE_CONVERSATION

    @property
    def log_path(self) -> Path:
        """Return the path for the debate log file."""
        return self._folder / FILE_LOG

    def result_path(self) -> Path:
        """Return the convenience latest-result path (result.json)."""
        return self._folder / f"{FILE_RESULT_PREFIX}.json"

    def write_config(self, config_dict: dict) -> None:
        """Serialize config as nested JSON (matching debate-config.example.json format)."""
        nested = {
            "topic": config_dict.get("topic"),
            "turns": config_dict.get("turns"),
            "debater_a": {
                "name": config_dict.get("name_a"),
                "model": config_dict.get("model_a"),
            },
            "debater_b": {
                "name": config_dict.get("name_b"),
                "model": config_dict.get("model_b"),
            },
            "judge": {
                "model": config_dict.get("model_judge"),
                "factcheck": config_dict.get("factcheck"),
            },
            "max_retries": config_dict.get("max_retries"),
            "min_response_len": config_dict.get("min_response_len"),
            "require_references": config_dict.get("require_references"),
            "outdir": config_dict.get("outdir"),
            "backend": config_dict.get("backend"),
            "temperature": config_dict.get("temperature"),
            "log_level": config_dict.get("log_level"),
        }
        self.config_path.write_text(json.dumps(nested, indent=2), encoding="utf-8")

    def write_run_info(self, backend: str, argv: list[str]) -> None:
        """Write run metadata (backend, full command) to run_info.json.

        Args:
            backend: Backend type string used for this run.
            argv: sys.argv captured at startup.
        """
        info = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backend": backend,
            "command": " ".join(argv),
            "argv": argv,
        }
        path = self._folder / "run_info.json"
        path.write_text(json.dumps(info, indent=2), encoding="utf-8")

    def write_result(self, verdict: dict) -> Path:
        """Write a judge verdict to a unique timestamped file and update result.json.

        Always writes a timestamped file so previous verdicts are preserved.
        Also writes ``result.json`` as a convenience pointer to the latest verdict.

        Args:
            verdict: Structured judge output dict.

        Returns:
            Path to the timestamped result file that was written.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_path = self._folder / f"{FILE_RESULT_PREFIX}_{ts}.json"
        payload = json.dumps(verdict, indent=2)
        timestamped_path.write_text(payload, encoding="utf-8")
        # Also keep result.json as the latest for convenience
        self.result_path().write_text(payload, encoding="utf-8")
        return timestamped_path
