"""Single source of truth for the package version."""

from __future__ import annotations

#: Semantic version — keep in sync with pyproject.toml and config/setup.json.
VERSION = "0.1.0"
MAJOR, MINOR, PATCH = (int(x) for x in VERSION.split("."))


def version_info() -> dict[str, str | int]:
    """Return structured version metadata.

    Returns:
        Dict with 'version', 'major', 'minor', 'patch' keys.
    """
    return {"version": VERSION, "major": MAJOR, "minor": MINOR, "patch": PATCH}
