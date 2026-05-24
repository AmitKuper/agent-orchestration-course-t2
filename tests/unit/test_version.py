"""Unit tests for src/shared/version.py."""

from __future__ import annotations

from src.shared.version import MAJOR, MINOR, PATCH, VERSION, version_info


def test_version_string_format():
    """VERSION is a semantic version string with three numeric parts."""
    parts = VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_major_minor_patch_match_version():
    """MAJOR, MINOR, PATCH integers match the VERSION string."""
    major, minor, patch = (int(p) for p in VERSION.split("."))
    assert major == MAJOR
    assert minor == MINOR
    assert patch == PATCH


def test_version_info_returns_dict():
    """version_info() returns a dict with version, major, minor, patch keys."""
    info = version_info()
    assert info["version"] == VERSION
    assert info["major"] == MAJOR
    assert info["minor"] == MINOR
    assert info["patch"] == PATCH
