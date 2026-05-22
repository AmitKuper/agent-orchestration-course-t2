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
    """

    def __init__(self, run_folder: Path) -> None:
        """Bind this manager to an already-created run folder.

        Args:
            run_folder: Path to the dedicated output folder for this run.
        """
        self._folder = run_folder

    @classmethod
    def create_run_folder(cls, outdir: str, topic: str) -> OutputManager:
        """Create a timestamped output folder for a new debate run.

        Args:
            outdir: Base output directory from config.
            topic: Debate topic, used to name the folder for readability.

        Returns:
            OutputManager bound to the newly created folder.
        """
        slug = topic[:40].lower().replace(" ", "_").replace("/", "-").replace(":", "").replace("?", "").replace("\\", "-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = Path(outdir) / f"{timestamp}_{slug}"
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
        """Return a unique timestamped path for a judge result file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self._folder / f"{FILE_RESULT_PREFIX}_{timestamp}.json"

    def write_config(self, config_dict: dict) -> None:
        """Serialize and write a config dict as JSON to the config file."""
        self.config_path.write_text(json.dumps(config_dict, indent=2), encoding="utf-8")

    def write_result(self, verdict: dict) -> Path:
        """Write a judge verdict to a unique timestamped result file.

        Args:
            verdict: Structured judge output dict.

        Returns:
            Path to the written result file.
        """
        path = self.result_path()
        path.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
        return path
