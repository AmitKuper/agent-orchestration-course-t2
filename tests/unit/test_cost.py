"""Unit tests for src/cost.py — CostTracker accumulation and cost.md writing."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cost import CostTracker


@pytest.fixture
def tracker() -> CostTracker:
    """Return a fresh CostTracker for each test."""
    return CostTracker(run_id="test-run-001")


def test_record_call_accumulates(tracker: CostTracker):
    """Multiple calls sum into the run summary."""
    tracker.record_call("AgentA", 100, 200)
    tracker.record_call("AgentB", 300, 400)
    summary = tracker.get_run_summary()
    assert summary["total_input_tokens"] == 400
    assert summary["total_output_tokens"] == 600
    assert summary["calls"] == 2


def test_run_summary_fields(tracker: CostTracker):
    """get_run_summary returns all required keys."""
    tracker.record_call("Judge", 500, 100)
    summary = tracker.get_run_summary()
    for key in (
        "run_id",
        "calls",
        "total_input_tokens",
        "total_output_tokens",
        "estimated_cost_usd",
    ):
        assert key in summary


def test_run_id_in_summary(tracker: CostTracker):
    """run_id in summary matches the one passed at construction."""
    assert tracker.get_run_summary()["run_id"] == "test-run-001"


def test_estimated_cost_positive(tracker: CostTracker):
    """estimated_cost_usd is non-negative for any token counts."""
    tracker.record_call("A", 1000, 1000)
    assert tracker.get_run_summary()["estimated_cost_usd"] >= 0


def test_empty_tracker_summary(tracker: CostTracker):
    """Zero calls yields zero tokens and zero cost."""
    summary = tracker.get_run_summary()
    assert summary["calls"] == 0
    assert summary["total_input_tokens"] == 0
    assert summary["estimated_cost_usd"] == 0.0


def test_append_creates_file_with_header(tmp_path: Path, tracker: CostTracker):
    """append_to_cost_md creates the file with a header if it does not exist."""
    cost_md = tmp_path / "cost.md"
    tracker.record_call("A", 100, 50)
    tracker.append_to_cost_md(cost_md)
    content = cost_md.read_text()
    assert "Cost Tracking" in content
    assert "test-run-001" in content


def test_append_does_not_duplicate_header(tmp_path: Path):
    """Calling append_to_cost_md twice does not double the header."""
    cost_md = tmp_path / "cost.md"
    t1 = CostTracker("run-1")
    t1.record_call("A", 10, 10)
    t1.append_to_cost_md(cost_md)

    t2 = CostTracker("run-2")
    t2.record_call("B", 20, 20)
    t2.append_to_cost_md(cost_md)

    content = cost_md.read_text()
    assert content.count("Cost Tracking") == 1
    assert "run-1" in content
    assert "run-2" in content


def test_append_adds_row(tmp_path: Path, tracker: CostTracker):
    """Each call to append_to_cost_md adds exactly one data row."""
    cost_md = tmp_path / "cost.md"
    tracker.record_call("A", 100, 200)
    tracker.append_to_cost_md(cost_md)
    rows = [line for line in cost_md.read_text().splitlines() if "test-run-001" in line]
    assert len(rows) == 1
