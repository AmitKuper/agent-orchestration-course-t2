"""Unit tests for src/config.py — CLI parsing, merging, and validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml

from src.config import DebateConfig, build_cli_parser, load_config, save_config
from src.constants import DEFAULT_TURNS, MAX_RETRIES, MIN_RESPONSE_LEN


def _parse(args: list[str]) -> argparse.Namespace:
    """Helper to parse a list of arg strings."""
    return build_cli_parser().parse_args(args)


def test_required_topic_from_cli():
    """load_config raises ValueError when topic is missing."""
    ns = _parse([])
    with pytest.raises(ValueError, match="--topic"):
        load_config(ns)


def test_topic_from_cli():
    """Topic provided via CLI is accepted."""
    ns = _parse(["--topic", "AI vs humans"])
    config = load_config(ns)
    assert config.topic == "AI vs humans"


def test_cli_overrides_defaults():
    """CLI flags override built-in defaults."""
    ns = _parse(["--topic", "T", "--turns", "6", "--max-retries", "5"])
    config = load_config(ns)
    assert config.turns == 6
    assert config.max_retries == 5


def test_default_values():
    """DebateConfig uses module-level defaults when no overrides provided."""
    config = DebateConfig(topic="test")
    assert config.turns == DEFAULT_TURNS
    assert config.max_retries == MAX_RETRIES
    assert config.min_response_len == MIN_RESPONSE_LEN


def test_yaml_config_file(tmp_path: Path):
    """Topic from YAML config file is loaded when no CLI topic given."""
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(yaml.dump({"topic": "from yaml", "turns": 4}))
    ns = _parse(["--config", str(cfg_file)])
    config = load_config(ns)
    assert config.topic == "from yaml"
    assert config.turns == 4


def test_cli_overrides_yaml(tmp_path: Path):
    """CLI flag takes precedence over same key in YAML config file."""
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(yaml.dump({"topic": "yaml topic", "turns": 10}))
    ns = _parse(["--config", str(cfg_file), "--turns", "2"])
    config = load_config(ns)
    assert config.turns == 2


def test_save_config(tmp_path: Path):
    """save_config writes valid JSON that round-trips back to the same topic."""
    config = DebateConfig(topic="save test", turns=8)
    path = tmp_path / "config.json"
    save_config(config, path)
    data = json.loads(path.read_text())
    assert data["topic"] == "save test"
    assert data["turns"] == 8


def test_factcheck_flag():
    """--factcheck sets factcheck=True on the config."""
    ns = _parse(["--topic", "T", "--factcheck"])
    config = load_config(ns)
    assert config.factcheck is True


def test_log_level_choices():
    """Invalid log level is rejected by argparse."""
    with pytest.raises(SystemExit):
        _parse(["--topic", "T", "--log-level", "INVALID"])
