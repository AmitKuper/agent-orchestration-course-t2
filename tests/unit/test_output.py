"""Unit tests for src/output.py — OutputManager folder, paths, and file writing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.constants import FILE_CONFIG, FILE_CONVERSATION, FILE_LOG, FILE_RESULT_PREFIX
from src.output import OutputManager


@pytest.fixture
def manager(tmp_path: Path) -> OutputManager:
    """Return an OutputManager bound to a tmp folder."""
    folder = tmp_path / "run"
    folder.mkdir()
    return OutputManager(folder)


def test_create_run_folder_creates_directory(tmp_path: Path):
    """create_run_folder creates a subdirectory inside outdir."""
    om = OutputManager.create_run_folder(str(tmp_path), "test topic")
    assert om.folder.exists()
    assert om.folder.is_dir()


def test_create_run_folder_slug_in_name(tmp_path: Path):
    """Folder name includes a slug derived from the topic."""
    om = OutputManager.create_run_folder(str(tmp_path), "Messi vs Ronaldo")
    assert "messi" in om.folder.name.lower()


def test_config_path(manager: OutputManager):
    """config_path points to FILE_CONFIG inside the run folder."""
    assert manager.config_path == manager.folder / FILE_CONFIG


def test_conversation_path(manager: OutputManager):
    """conversation_path points to FILE_CONVERSATION inside the run folder."""
    assert manager.conversation_path == manager.folder / FILE_CONVERSATION


def test_log_path(manager: OutputManager):
    """log_path points to FILE_LOG inside the run folder."""
    assert manager.log_path == manager.folder / FILE_LOG


def test_result_path_fixed(manager: OutputManager):
    """result_path() always returns the same fixed path (folder has the timestamp)."""
    p1 = manager.result_path()
    p2 = manager.result_path()
    assert p1 == p2


def test_result_path_prefix(manager: OutputManager):
    """result_path() filename starts with FILE_RESULT_PREFIX."""
    assert manager.result_path().name.startswith(FILE_RESULT_PREFIX)


def test_write_config_creates_file(manager: OutputManager):
    """write_config writes a JSON file that can be parsed back."""
    manager.write_config({"topic": "test", "turns": 4})
    assert manager.config_path.exists()
    data = json.loads(manager.config_path.read_text())
    assert data["topic"] == "test"


def test_write_result_creates_file(manager: OutputManager):
    """write_result writes the verdict dict as JSON and returns its path."""
    verdict = {"winner": "A", "scores": {}, "explanation": "good"}
    path = manager.write_result(verdict)
    assert path.exists()
    assert json.loads(path.read_text())["winner"] == "A"


def test_write_result_overwrites(manager: OutputManager):
    """Two write_result calls write to the same file (latest verdict wins)."""
    p1 = manager.write_result({"winner": "A", "scores": {}, "explanation": ""})
    p2 = manager.write_result({"winner": "B", "scores": {}, "explanation": ""})
    assert p1 == p2
    assert json.loads(p1.read_text())["winner"] == "B"
