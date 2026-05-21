"""Unit tests for src/state.py — JSONL read/write and resume detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.state import ConversationState


@pytest.fixture
def path(tmp_path: Path) -> Path:
    """Return a path inside tmp_path for the conversation JSONL file."""
    return tmp_path / "conversation.jsonl"


def _turn(n: int, agent: str = "A") -> dict:
    return {"agent": agent, "turn": n, "argument": f"arg {n}", "references": []}


def test_append_creates_file(path: Path):
    """append_turn writes the file if it does not yet exist."""
    state = ConversationState(path)
    state.append_turn(_turn(1))
    assert path.exists()


def test_append_writes_valid_jsonl(path: Path):
    """Each appended turn is a parseable JSON line."""
    state = ConversationState(path)
    state.append_turn(_turn(1))
    state.append_turn(_turn(2))
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(lines) == 2
    assert lines[0]["turn"] == 1
    assert lines[1]["turn"] == 2


def test_load_from_file_roundtrip(path: Path):
    """Turns appended then loaded from disk match the originals."""
    state = ConversationState(path)
    state.append_turn(_turn(1, "A"))
    state.append_turn(_turn(2, "B"))

    loaded = ConversationState.load_from_file(path)
    turns = loaded.get_turns()
    assert len(turns) == 2
    assert turns[0]["agent"] == "A"
    assert turns[1]["agent"] == "B"


def test_load_from_missing_file(path: Path):
    """load_from_file on a non-existent path returns an empty state."""
    state = ConversationState.load_from_file(path)
    assert state.get_turns() == []


def test_last_turn_number_empty(path: Path):
    """last_turn_number returns 0 when no turns have been recorded."""
    assert ConversationState(path).last_turn_number() == 0


def test_last_turn_number(path: Path):
    """last_turn_number returns the turn field of the last appended turn."""
    state = ConversationState(path)
    state.append_turn(_turn(1))
    state.append_turn(_turn(2))
    assert state.last_turn_number() == 2


def test_is_complete_false(path: Path):
    """is_complete is False when fewer turns exist than the total."""
    state = ConversationState(path)
    state.append_turn(_turn(1))
    assert not state.is_complete(4)


def test_is_complete_true(path: Path):
    """is_complete is True when the required number of turns are present."""
    state = ConversationState(path)
    for i in range(1, 5):
        state.append_turn(_turn(i))
    assert state.is_complete(4)


def test_needs_resume_false_missing(path: Path):
    """needs_resume is False when the file does not exist."""
    assert not ConversationState.needs_resume(path)


def test_needs_resume_false_empty(path: Path):
    """needs_resume is False for an empty file."""
    path.write_text("")
    assert not ConversationState.needs_resume(path)


def test_needs_resume_true(path: Path):
    """needs_resume is True when the file exists and is non-empty."""
    state = ConversationState(path)
    state.append_turn(_turn(1))
    assert ConversationState.needs_resume(path)
