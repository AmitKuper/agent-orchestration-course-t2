"""Configuration loading, CLI parsing, and persistence for the debate platform."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from src.constants import (
    DEFAULT_BACKEND,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MODEL,
    DEFAULT_NAME_A,
    DEFAULT_NAME_B,
    DEFAULT_OUTDIR,
    DEFAULT_TEMPERATURE,
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
    config_file: str | None = None
    backend: str = DEFAULT_BACKEND
    temperature: float | None = DEFAULT_TEMPERATURE


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
        choices=["api", "cli", "cli-session", "ollama-cli", "ollama"],
        default=None,
        help=(
            "Invocation backend: 'api' (Anthropic SDK), 'cli' (claude --print per turn), "
            "'cli-session' (persistent claude subprocess), "
            "'ollama-cli' (ollama run <model>), or 'ollama' (Ollama HTTP API)"
        ),
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (0.0–1.0). Supported by api and ollama backends.",
    )
    return p


def _load_yaml(path: str) -> dict:
    """Load and return the contents of a YAML config file."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _flatten_nested(raw: dict) -> dict:
    """Convert nested config format to flat DebateConfig keys.

    Accepts both the nested format (debater_a.name, judge.model, …) and
    the flat format (name_a, model_judge, …) so either works as input.
    """
    out = {k: v for k, v in raw.items() if not isinstance(v, dict)}
    if "debater_a" in raw:
        out.setdefault("name_a", raw["debater_a"].get("name"))
        out.setdefault("model_a", raw["debater_a"].get("model"))
    if "debater_b" in raw:
        out.setdefault("name_b", raw["debater_b"].get("name"))
        out.setdefault("model_b", raw["debater_b"].get("model"))
    if "judge" in raw:
        out.setdefault("model_judge", raw["judge"].get("model"))
        out.setdefault("factcheck", raw["judge"].get("factcheck"))
    if "orchestrator" in raw:
        # orchestrator.model is not a separate field — no-op for now
        pass
    return {k: v for k, v in out.items() if v is not None}


def load_config(args: argparse.Namespace) -> DebateConfig:
    """Merge YAML/JSON config file with CLI overrides and return a DebateConfig.

    CLI flags always take precedence. Topic is required from either source.
    Accepts both nested (debater_a/debater_b/judge) and flat key formats.
    """
    base: dict = _flatten_nested(_load_yaml(args.config_file)) if args.config_file else {}
    cli = {k: v for k, v in vars(args).items() if v is not None and k != "config_file"}
    merged = {**base, **cli}

    if "topic" not in merged:
        raise ValueError("--topic is required (or provide it in the config file).")

    valid = DebateConfig.__dataclass_fields__.keys()
    return DebateConfig(**{k: v for k, v in merged.items() if k in valid})


def save_config(config: DebateConfig, path: Path) -> None:
    """Write the resolved DebateConfig as a JSON file to path."""
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
