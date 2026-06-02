"""Unit tests for OllamaCliBackend (ollama run subprocess)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.backends import OllamaCliBackend
from src.backends._ollama_orchestrator import OllamaOrchestratorBackend
from src.cost import CostTracker


@pytest.fixture
def cost() -> CostTracker:
    """Return a fresh CostTracker."""
    return CostTracker("test")


def test_ollama_cli_backend_returns_stdout(cost: CostTracker):
    """OllamaCliBackend.invoke returns stripped stdout from the ollama CLI."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ollama response\n"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        result = OllamaCliBackend().invoke("Agent", "llama3.2", "prompt", cost, 2048)

    assert result == "ollama response"


def test_ollama_cli_backend_uses_model_in_command(cost: CostTracker):
    """OllamaCliBackend.invoke passes the model name to the ollama command."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "response"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result) as mock_run:
        OllamaCliBackend().invoke("Agent", "mistral", "prompt", cost, 2048)

    cmd = mock_run.call_args.args[0]
    assert cmd == ["ollama", "run", "mistral"]


def test_ollama_cli_backend_records_zero_tokens(cost: CostTracker):
    """OllamaCliBackend.invoke records zero tokens (CLI gives no usage info)."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "reply"

    with patch("src.backends._cli.subprocess.run", return_value=mock_result):
        OllamaCliBackend().invoke("Agent", "llama3", "prompt", cost, 2048)

    summary = cost.get_run_summary()
    assert summary["total_input_tokens"] == 0
    assert summary["total_output_tokens"] == 0


def test_ollama_orchestrator_fallback_backend_type():
    """OllamaOrchestratorBackend falls back to ollama-cli-agents for per-turn calls."""
    assert OllamaOrchestratorBackend.fallback_backend_type == "ollama-cli-agents"


def test_ollama_cli_backend_raises_on_nonzero_exit(cost: CostTracker):
    """OllamaCliBackend.invoke raises RuntimeError when ollama exits non-zero."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "model not found"

    with (
        patch("src.backends._cli.subprocess.run", return_value=mock_result),
        pytest.raises(RuntimeError, match="ollama CLI failed"),
    ):
        OllamaCliBackend().invoke("Agent", "nomodel", "prompt", cost, 2048)


# ── OllamaOrchestratorBackend ─────────────────────────────────────────────────


def test_ollama_orchestrator_parse_jsonl_turns():
    """_parse extracts turns and verdict from one-JSON-per-line output."""
    backend = OllamaOrchestratorBackend()
    raw = (
        '{"agent":"A","turn":1,"argument":"hello","references":[]}\n'
        '{"agent":"B","turn":2,"argument":"world","references":[]}\n'
        '{"winner":"A","scores":{"A":{"logic":8},"B":{"logic":7}},'
        '"explanation":"A wins","factcheck_flags":[]}'
    )
    turns, verdict = backend._parse(raw)
    assert len(turns) == 2
    assert turns[0]["agent"] == "A"
    assert verdict is not None
    assert verdict["winner"] == "A"


def test_ollama_orchestrator_parse_no_verdict():
    """_parse returns (turns, None) when no verdict object is present."""
    backend = OllamaOrchestratorBackend()
    raw = '{"agent":"A","turn":1,"argument":"hello","references":[]}'
    turns, verdict = backend._parse(raw)
    assert len(turns) == 1
    assert verdict is None


def test_ollama_orchestrator_parse_word_wrapped():
    """_parse handles JSON objects word-wrapped across terminal lines."""
    backend = OllamaOrchestratorBackend()
    raw = '{"agent":"A","turn":1,\n"argument":"hello","references":[]}'
    turns, verdict = backend._parse(raw)
    assert len(turns) == 1
    assert turns[0]["turn"] == 1


def test_ollama_orchestrator_parse_nested_braces():
    """_parse depth-tracks nested braces when reassembling word-wrapped objects."""
    backend = OllamaOrchestratorBackend()
    raw = '{"agent":"A","data":\n{"nested":true},"turn":1,"argument":"test","references":[]}'
    turns, verdict = backend._parse(raw)
    assert len(turns) == 1


def test_ollama_orchestrator_build_prompt_contains_topic():
    """_build_prompt includes the debate topic and agent names."""
    backend = OllamaOrchestratorBackend()
    config = MagicMock()
    config.turns = 4
    config.name_a = "AgentA"
    config.name_b = "AgentB"
    config.topic = "Is AI beneficial?"
    config.min_response_len = 100
    prompt = backend._build_prompt(config, "FOR", "AGAINST")
    assert "Is AI beneficial?" in prompt
    assert "AgentA" in prompt
    assert "AgentB" in prompt
    assert "FOR" in prompt


def test_ollama_orchestrator_run_debate_returns_parsed_output():
    """run_debate calls subprocess and returns parsed turns and verdict."""
    backend = OllamaOrchestratorBackend()
    config = MagicMock()
    config.turns = 2
    config.model_a = "Qwen3:14b"
    config.name_a = "A"
    config.name_b = "B"
    config.topic = "test"
    config.min_response_len = 50
    raw_output = (
        '{"agent":"A","turn":1,"argument":"arg1","references":[]}\n'
        '{"agent":"B","turn":2,"argument":"arg2","references":[]}\n'
        '{"winner":"A","scores":{},"explanation":"A wins","factcheck_flags":[]}'
    )
    mock_result = MagicMock()
    mock_result.stdout = raw_output
    with patch("src.backends._ollama_orchestrator.subprocess.run", return_value=mock_result):
        turns, verdict = backend.run_debate(config, "FOR", "AGAINST")
    assert len(turns) == 2
    assert verdict["winner"] == "A"


def test_ollama_orchestrator_run_debate_strips_thinking_preamble():
    """run_debate discards text before '...done thinking.' in model output."""
    backend = OllamaOrchestratorBackend()
    config = MagicMock()
    config.turns = 1
    config.model_a = "Qwen3:14b"
    config.name_a = "A"
    config.name_b = "B"
    config.topic = "test"
    config.min_response_len = 50
    raw_output = (
        "Thinking deeply...\n...done thinking.\n"
        '{"agent":"A","turn":1,"argument":"arg","references":[]}'
    )
    mock_result = MagicMock()
    mock_result.stdout = raw_output
    with patch("src.backends._ollama_orchestrator.subprocess.run", return_value=mock_result):
        turns, verdict = backend.run_debate(config, "FOR", "AGAINST")
    assert len(turns) == 1
