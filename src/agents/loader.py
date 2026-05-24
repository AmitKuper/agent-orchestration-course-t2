"""Agent definition file loader with variable substitution."""

from __future__ import annotations

from pathlib import Path


def load_agent_def(path: str | Path, subs: dict[str, str]) -> str:
    """Load an agent definition file, strip YAML frontmatter, substitute variables.

    Reads the markdown file at ``path``, removes the ``---`` YAML frontmatter
    block if present, and replaces every ``$VARIABLE_NAME`` placeholder with
    the corresponding value from ``subs``.

    Args:
        path: Path to the ``.md`` agent definition file.
        subs: Mapping of VARIABLE_NAME → replacement value.
            Each key ``K`` replaces every occurrence of ``$K`` in the text.

    Returns:
        Rendered system prompt string, or empty string if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        text = text[end + 3:].lstrip()
    for key, value in subs.items():
        text = text.replace(f"${key}", str(value))
    return text
