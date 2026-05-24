# AI Debate Platform

A multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator, and scored by a judge agent.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Backends](#backends)
- [Configuration](#configuration)
- [Output](#output)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Windows

```powershell
git clone <repo-url>
cd HW2
uv sync            # installs all dependencies
copy .env-example .env
# Edit .env — add your ANTHROPIC_API_KEY for --backend api
```

### macOS / Linux

```bash
git clone <repo-url>
cd HW2
uv sync
cp .env-example .env
# Edit .env — add your ANTHROPIC_API_KEY for --backend api
```

### With pip (alternative)

```bash
pip install -e .
pip install -e ".[dev]"      # includes ruff, pytest, pytest-cov
pip install -e ".[ollama]"   # adds requests for Ollama API backend
cp .env-example .env
```

---

## Usage

### New debate

```bash
python main.py --topic "AI will replace most jobs" --turns 4
```

### Resume an interrupted debate

```bash
python main.py --resume --outdir path/to/run/folder
```

### Common options

| Flag | Default | Description |
|------|---------|-------------|
| `--topic` | required | Debate topic |
| `--turns` | 20 | Total turns (split evenly between agents) |
| `--name-a` | Agent A | Name for debater A |
| `--name-b` | Agent B | Name for debater B |
| `--model-a` | claude-sonnet-4-6 | Model for debater A |
| `--model-b` | claude-sonnet-4-6 | Model for debater B |
| `--model-judge` | claude-sonnet-4-6 | Model for the judge |
| `--max-retries` | 3 | Retries per invalid response |
| `--outdir` | outputs/ | Base output directory |
| `--factcheck` | off | Enable factual accuracy checks |
| `--log-level` | INFO | DEBUG / INFO / WARNING / ERROR |
| `--config` | — | Path to YAML config file |
| `--backend` | api | Invocation backend — see [Backends](#backends) |

### YAML config file

```yaml
topic: "Nuclear energy is essential for climate goals"
turns: 10
name_a: "Dr. Green"
name_b: "Prof. Red"
factcheck: true
```

```bash
python main.py --config debate.yaml --turns 6   # CLI overrides YAML
```

---

## Backends

Four backends are available via `--backend`:

| Backend | Flag | Requires | Token tracking |
|---------|------|----------|---------------|
| Anthropic API | `--backend api` (default) | `ANTHROPIC_API_KEY` in `.env` | Yes |
| Claude Code CLI | `--backend cli` | Claude Code installed + Pro subscription | No |
| Ollama CLI | `--backend ollama-cli` | Ollama installed with target model | No |
| Ollama API | `--backend ollama` | Ollama running locally + `pip install requests` | Yes |

### api — Anthropic SDK (default)

```bash
python main.py --topic "..." --backend api
```

Requires `ANTHROPIC_API_KEY` in `.env`.

### cli — Claude Code CLI

```bash
python main.py --topic "..." --backend cli --model-a claude-sonnet-4-6
```

Uses `claude --model <model> --print`. Requires Claude Code and a Pro subscription.
Also updates `.claude/agents/*.md` model fields to match config.

### ollama-cli — Ollama CLI

```bash
ollama pull llama3.2
python main.py --topic "..." --backend ollama-cli --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

### ollama — Ollama HTTP API

```bash
pip install ".[ollama]"
python main.py --topic "..." --backend ollama --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

Override the Ollama server URL:

```bash
OLLAMA_BASE_URL=http://192.168.1.10:11434 python main.py --topic "..." --backend ollama --model-a llama3.2
```

---

## Configuration

All config is externalised — no hard-coded values in source code.

| File | Purpose |
|------|---------|
| `config/setup.json` | Application defaults (turns, timeouts, token limits) |
| `config/rate_limits.json` | Per-backend rate limits and retry config |
| `.env` | Secrets (API keys) — never committed |
| `.env-example` | Template for `.env` |

---

## Output

Each run creates a timestamped folder under `--outdir`:

```
outputs/20260101_120000/
  config.json          # resolved configuration for this run
  conversation.jsonl   # one line per completed turn
  debate.log           # full execution log
  result.json          # judge verdict and scores
```

---

## Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov=orchestrator

# Or with pip
pytest tests/ --cov=src --cov=orchestrator

# Lint check
uv run ruff check .
```

Coverage target: ≥ 85% (currently 100%).

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Follow the code rules in `docs/rules.md` (150-line limit, ruff, docstrings)
3. Write tests first (TDD) — coverage must stay ≥ 85%
4. Run `ruff check .` and ensure zero violations before committing
5. Use semantic commit messages: `Feature:`, `BugFix:`, `Refactor:`, `Docs:`
6. Update `docs/TODO.md` in the same commit as the work it describes
7. Open a pull request with a clear description of the change

---

## License

MIT License — see [LICENSE](LICENSE) for details.

**Credits:** Built as coursework for the AI Agent Orchestration Course. Uses the [Anthropic Claude API](https://anthropic.com) and [Ollama](https://ollama.ai).
