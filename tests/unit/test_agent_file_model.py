"""Unit tests for update_agent_file_model utility."""

from __future__ import annotations

from src.backends import update_agent_file_model


def test_update_agent_file_model_rewrites_model_field(tmp_path):
    """update_agent_file_model replaces the model: line in frontmatter."""
    agent_file = tmp_path / "debate-agent.md"
    agent_file.write_text(
        "---\nname: debate-agent\nmodel: sonnet\ncolor: orange\n---\nBody text.\n",
        encoding="utf-8",
    )

    update_agent_file_model(agent_file, "claude-sonnet-4-6")

    content = agent_file.read_text(encoding="utf-8")
    assert "model: claude-sonnet-4-6" in content
    assert "model: sonnet\n" not in content


def test_update_agent_file_model_preserves_body(tmp_path):
    """update_agent_file_model does not alter content outside the model: line."""
    agent_file = tmp_path / "debate-agent.md"
    original = "---\nname: debate-agent\nmodel: haiku\n---\nYou are a debater.\n"
    agent_file.write_text(original, encoding="utf-8")

    update_agent_file_model(agent_file, "claude-haiku-4-5-20251001")

    content = agent_file.read_text(encoding="utf-8")
    assert "You are a debater." in content
    assert "name: debate-agent" in content


def test_update_agent_file_model_missing_file_is_noop(tmp_path):
    """update_agent_file_model silently skips files that do not exist."""
    missing = tmp_path / "nonexistent.md"
    update_agent_file_model(missing, "claude-sonnet-4-6")  # must not raise
