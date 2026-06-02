"""Unit tests for src/backends/_ansi.py — ANSI/VT100 terminal emulation."""

from __future__ import annotations

from src.backends._ansi import extract_response, render_ansi


def test_render_ansi_plain_text():
    """Plain text with no escape sequences passes through unchanged."""
    assert render_ansi("hello") == "hello"


def test_render_ansi_cursor_back_D():
    """CSI D (cursor back) moves the column left, allowing overwriting."""
    raw = "ab\x1b[1Dc"
    assert render_ansi(raw) == "ac"


def test_render_ansi_erase_to_eol_K():
    """CSI K (erase to end of line) truncates the current line at the cursor."""
    raw = "hello\x1b[3D\x1b[K"
    assert render_ansi(raw) == "he"


def test_render_ansi_set_column_G():
    """CSI G (set column) positions the cursor at the given column."""
    raw = "hello\x1b[1GX"
    assert render_ansi(raw) == "Xello"


def test_render_ansi_carriage_return():
    """Carriage return resets the column to 0, enabling overwrite."""
    raw = "hello\rXY"
    assert render_ansi(raw) == "XYllo"


def test_render_ansi_bare_escape():
    """A bare ESC not followed by [ is consumed with the next character."""
    raw = "a\x1bXbc"
    assert render_ansi(raw) == "abc"


def test_extract_response_strips_thinking_preamble():
    """extract_response discards everything up to and including '...done thinking.'"""
    raw = "Thinking...\n...done thinking.\n{\"answer\": 42}"
    result = extract_response(raw)
    assert '{"answer": 42}' in result
    assert "Thinking" not in result


def test_extract_response_no_preamble():
    """extract_response returns the full rendered text when no thinking block is present."""
    assert extract_response("direct response") == "direct response"
