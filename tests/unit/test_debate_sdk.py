"""Unit tests for DebateSDK."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import DebateConfig
from src.sdk.debate_sdk import DebateResult, DebateSDK


@pytest.fixture
def config(tmp_path: Path) -> DebateConfig:
    """Return a minimal DebateConfig for SDK tests."""
    return DebateConfig(
        topic="AI vs humans",
        turns=2,
        outdir=str(tmp_path / "out"),
        min_response_len=5,
        max_retries=0,
    )


def _mock_orch_run(orch_instance):
    """Patch orch.run_debate to do nothing."""
    orch_instance.run_debate = MagicMock()


def _mock_orch_resume(orch_instance):
    """Patch orch.resume_debate to do nothing."""
    orch_instance.resume_debate = MagicMock()


def test_debate_result_dataclass():
    """DebateResult can be constructed with expected fields."""
    result = DebateResult(
        run_dir=Path("/tmp/run"),
        verdict={"winner": "A"},
        cost_summary={"total_input_tokens": 0, "total_output_tokens": 0, "calls": []},
        turns_completed=4,
        errors=[],
    )
    assert result.run_dir == Path("/tmp/run")
    assert result.verdict["winner"] == "A"
    assert result.turns_completed == 4
    assert result.errors == []


def test_sdk_run_returns_debate_result(config, tmp_path):
    """DebateSDK.run returns a DebateResult after a successful run."""
    with patch("src.sdk.debate_sdk.OutputManager.create_run_folder") as mock_create, \
         patch("orchestrator.DebateOrchestrator") as mock_orch_cls:
        run_folder = tmp_path / "run"
        run_folder.mkdir(parents=True)
        mock_output = MagicMock()
        mock_output.folder = run_folder
        mock_output.conversation_path = run_folder / "conversation.jsonl"
        mock_output.result_path.return_value = run_folder / "result.json"
        mock_create.return_value = mock_output

        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        sdk = DebateSDK()
        result = sdk.run(config)

    assert isinstance(result, DebateResult)
    assert result.run_dir == run_folder
    mock_orch.run_debate.assert_called_once()


def test_sdk_run_captures_errors(config, tmp_path):
    """DebateSDK.run captures exceptions and returns them in errors list."""
    with patch("src.sdk.debate_sdk.OutputManager.create_run_folder") as mock_create, \
         patch("orchestrator.DebateOrchestrator") as mock_orch_cls:
        run_folder = tmp_path / "run"
        run_folder.mkdir(parents=True)
        mock_output = MagicMock()
        mock_output.folder = run_folder
        mock_output.conversation_path = run_folder / "conversation.jsonl"
        mock_output.result_path.return_value = run_folder / "result.json"
        mock_create.return_value = mock_output

        mock_orch = MagicMock()
        mock_orch.run_debate.side_effect = RuntimeError("debate failed")
        mock_orch_cls.return_value = mock_orch

        sdk = DebateSDK()
        result = sdk.run(config)

    assert len(result.errors) == 1
    assert "debate failed" in result.errors[0]


def test_sdk_resume_returns_debate_result(tmp_path):
    """DebateSDK.resume returns a DebateResult from an existing run folder."""
    from src.constants import FILE_CONVERSATION

    run_folder = tmp_path / "out"
    run_folder.mkdir(parents=True)
    conv_path = run_folder / FILE_CONVERSATION
    conv_path.write_text("", encoding="utf-8")

    config = DebateConfig(
        topic="AI vs humans",
        turns=2,
        outdir=str(run_folder),
        min_response_len=5,
        max_retries=0,
    )

    with patch("orchestrator.DebateOrchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch
        sdk = DebateSDK()
        result = sdk.resume(config)

    assert isinstance(result, DebateResult)
    mock_orch.resume_debate.assert_called_once()


def test_sdk_resume_captures_errors(tmp_path):
    """DebateSDK.resume captures exceptions and returns them in errors list."""
    from src.constants import FILE_CONVERSATION

    run_folder = tmp_path / "out"
    run_folder.mkdir(parents=True)
    (run_folder / FILE_CONVERSATION).write_text("", encoding="utf-8")

    config = DebateConfig(
        topic="AI vs humans",
        turns=2,
        outdir=str(run_folder),
        min_response_len=5,
        max_retries=0,
    )

    with patch("orchestrator.DebateOrchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch.resume_debate.side_effect = RuntimeError("resume failed")
        mock_orch_cls.return_value = mock_orch
        sdk = DebateSDK()
        result = sdk.resume(config)

    assert len(result.errors) == 1
    assert "resume failed" in result.errors[0]


def test_sdk_build_result_reads_verdict(tmp_path):
    """_build_result reads verdict from result.json when it exists."""
    verdict = {"winner": "Agent A", "scores": {}}
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    result_file = run_folder / "result.json"
    result_file.write_text(json.dumps(verdict), encoding="utf-8")

    from src.cost import CostTracker
    from src.output import OutputManager
    from src.state import ConversationState

    output = OutputManager(run_folder)
    state = ConversationState(run_folder / "conversation.jsonl")
    tracker = CostTracker("test")

    sdk = DebateSDK()
    with patch.object(output, "result_path", return_value=result_file):
        dr = sdk._build_result(output, state, tracker, [])

    assert dr.verdict == verdict
    assert dr.run_dir == run_folder
