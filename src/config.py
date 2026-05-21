"""Configuration loading, CLI parsing, and persistence for the debate platform."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from src.constants import (
    DEFAULT_BACKEND,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MODEL,
    DEFAULT_NAME_A,
    DEFAULT_NAME_B,
    DEFAULT_OUTDIR,
    DEFAULT_TURNS,
    MAX_RETRIES,
    MIN_RESPONSE_LEN,
)


@dataclass
class DebateConfig:
    """Fully resolved configuration for a single debate run."""

    topic: str
    turns: int = DEFAULT_TURNS
    model_a: str = DEFAULT_MODEL
    model_b: str = DEFAULT_MODEL
    model_judge: str = DEFAULT_MODEL
    name_a: str = DEFAULT_NAME_A
    name_b: str = DEFAULT_NAME_B
    max_retries: int = MAX_RETRIES
    min_response_len: int = MIN_RESPONSE_LEN
    outdir: str = DEFAULT_OUTDIR
    factcheck: bool = False
    log_level: str = DEFAULT_LOG_LEVEL
    resume: bool = False
    config_file: Optional[str] = None
    backend: str = DEFAULT_BACKEND


def build_cli_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for the debate platform."""
    p = argparse.ArgumentParser(
        description="AI Debate Platform — structured debate between two Claude agents."
    )
    p.add_argument("--topic", type=str, help="Debate topic")
    p.add_argument("--turns", type=int, help=f"Total turns (default: {DEFAULT_TURNS})")
    p.add_argument("--model-a", dest="model_a", type=str, help="Model for Agent A")
    p.add_argument("--model-b", dest="model_b", type=str, help="Model for Agent B")
    p.add_argument(
        "--model-judge", dest="model_judge", type=str, help="Model for Judge"
    )
    p.add_argument("--name-a", dest="name_a", type=str, help="Name for Agent A")
    p.add_argument("--name-b", dest="name_b", type=str, help="Name for Agent B")
    p.add_argument(
        "--max-retries", dest="max_retries", type=int, help="Max retries per turn"
    )
    p.add_argument("--min-response-len", dest="min_response_len", type=int)
    p.add_argument("--outdir", type=str, help="Output directory")
    p.add_argument(
        "--factcheck", action="store_true", default=None, help="Enable factcheck"
    )
    p.add_argument(
        "--log-level", dest="log_level", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    p.add_argument(
        "--resume", action="store_true", default=None, help="Resume interrupted debate"
    )
    p.add_argument(
        "--config", dest="config_file", type=str, help="Path to YAML config file"
    )
    p.add_argument(
        "--backend",
        choices=["api", "cli"],
        default=None,
        help="Invocation backend: 'api' (Anthropic SDK) or 'cli' (claude --print)",
    )
    return p


def _load_yaml(path: str) -> dict:
    """Load and return the contents of a YAML config file."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(args: argparse.Namespace) -> DebateConfig:
    """Merge YAML config file with CLI overrides and return a DebateConfig.

    CLI flags always take precedence. Topic is required from either source.
    """
    base: dict = _load_yaml(args.config_file) if args.config_file else {}
    cli = {k: v for k, v in vars(args).items() if v is not None and k != "config_file"}
    merged = {**base, **cli}

    if "topic" not in merged:
        raise ValueError("--topic is required (or provide it in the config file).")

    valid = DebateConfig.__dataclass_fields__.keys()
    return DebateConfig(**{k: v for k, v in merged.items() if k in valid})


def save_config(config: DebateConfig, path: Path) -> None:
    """Write the resolved DebateConfig as a JSON file to path."""
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
