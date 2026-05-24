"""ANSI/VT100 terminal emulator for cleaning ollama CLI streaming output.

Ollama CLI streams responses with cursor-movement escape sequences
(e.g. \x1b[9D\x1b[K to back up and correct a typo mid-word).
Simple regex stripping leaves orphaned newlines inside JSON strings.
This module simulates the terminal screen state to produce clean text.
"""

from __future__ import annotations

import re

_CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")
_DONE_THINKING = "...done thinking."


def render_ansi(raw: str) -> str:
    """Simulate a VT100 terminal and return the final rendered text.

    Handles cursor-back (D), erase-to-end-of-line (K), and column (G)
    commands. All other CSI sequences and private-mode toggles are ignored.

    Args:
        raw: Raw byte string from ollama CLI stdout.

    Returns:
        Plain-text rendering of the terminal screen after all sequences applied.
    """
    lines: list[list[str]] = [[]]
    row = col = 0

    def _ensure() -> None:
        while len(lines) <= row:
            lines.append([])

    i = 0
    while i < len(raw):
        m = _CSI_RE.match(raw, i)
        if m:
            params, cmd = m.group(1), m.group(2)
            private = "?" in params
            if cmd == "D" and not private:
                col = max(0, col - int(params or "1"))
            elif cmd == "K" and not private:
                _ensure()
                lines[row] = lines[row][:col]
            elif cmd == "G" and not private:
                col = max(0, int(params or "1") - 1)
            i = m.end()
        elif raw[i] == "\n":
            row += 1
            _ensure()
            col = 0
            i += 1
        elif raw[i] == "\r":
            col = 0
            i += 1
        elif raw[i] == "\x1b":
            i += 2
        else:
            _ensure()
            while len(lines[row]) <= col:
                lines[row].append(" ")
            lines[row][col] = raw[i]
            col += 1
            i += 1

    return "\n".join("".join(line) for line in lines)


def extract_response(raw: str) -> str:
    """Render ANSI output and strip the thinking preamble if present.

    For reasoning models (e.g. Qwen3) that emit a 'Thinking...' /
    '...done thinking.' block before the real response, discards that
    section entirely and returns only the final response text.

    Args:
        raw: Raw stdout captured from an ollama CLI subprocess.

    Returns:
        Clean response string ready for JSON parsing or direct use.
    """
    rendered = render_ansi(raw)
    if _DONE_THINKING in rendered:
        rendered = rendered.split(_DONE_THINKING, 1)[1]
    # Collapse terminal word-wrap newlines to spaces so JSON stays on one line.
    rendered = " ".join(line.strip() for line in rendered.splitlines() if line.strip())
    return rendered.strip()
