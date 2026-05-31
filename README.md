# AI Debate Platform

A multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator, and scored by a judge agent.

## Table of Contents
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Environment Variables](#environment-variables)
- [Sample Run](#sample-run)
- [JSON Communication Protocol](#json-communication-protocol)
- [Backends](#backends)
- [Running with Ollama (free local backend)](#running-with-ollama-free-local-backend)
- [Configuration](#configuration)
- [Output](#output)
- [Running Tests](#running-tests)
- [Linting](#linting)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture

```
main.py
  └── DebateSDK              # public entry point; CLI delegates here
        └── DebateOrchestrator
              ├── TopicValidator     # rejects non-debatable topics
              ├── DebateAgent (A)    # argues FOR position
              ├── DebateAgent (B)    # argues AGAINST position
              └── JudgeAgent         # scores completed debate
```

Every agent call passes through **APIGatekeeper** — a centralized router that enforces per-backend retry/backoff and logs every call. Backends are swappable (`api`, `cli`, `ollama-cli`, `ollama`); the rest of the system is backend-agnostic.

**Validation pipeline** (applied to every response before acceptance):

1. Empty / too-short check
2. API error marker detection
3. Disrespectful language filter
4. Markdown fence rejection (raw JSON only)
5. Unresolved placeholder rejection
6. JSON schema check (debate turn or judge verdict, depending on agent type)
7. **StanceValidator** — rejects concession phrases; agents may never agree with or yield to each other

---

## Installation

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — the project package manager

Install uv if you don't have it:
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

```bash
git clone https://github.com/AmitKuper/agent-orchestration-course-t2.git
cd agent-orchestration-course-t2
uv sync --extra dev    # installs all dependencies including dev tools
cp .env.example .env   # Windows: copy .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY for --backend api
```

> **Note:** `pip` is not the course workflow. Use `uv` for all dependency management.

---

## Quick Start

```bash
# Run a short 4-turn debate (uses Anthropic API by default)
uv run python main.py --topic "AI will replace most jobs" --turns 4

# Run with a free local model (no API key needed)
uv run python main.py --topic "AI will replace most jobs" --turns 4 \
  --backend ollama-cli --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2

# Resume an interrupted debate
uv run python main.py --resume --outdir outputs/my-run-folder
```

---

## Usage

### New debate

```bash
uv run python main.py --topic "AI will replace most jobs" --turns 4
```

### Resume an interrupted debate

```bash
uv run python main.py --resume --outdir path/to/run/folder
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
| `--require-references` | off | Reject turns with empty references list |
| `--log-level` | INFO | DEBUG / INFO / WARNING / ERROR |
| `--config` | — | Path to YAML/JSON config file |
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
uv run python main.py --config debate.yaml --turns 6   # CLI overrides YAML
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For `--backend api` | Your Anthropic API key |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default: `http://localhost:11434`) |
| `CLAUDE_SKIP_PERMISSIONS` | No | Set to `false` to disable `--dangerously-skip-permissions` in CLI backend (default: `true`) |

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

---

## Sample Run

The following shows a real 20-turn debate run using the Ollama CLI backend (Qwen3:14b).
No API tokens are consumed.

```
$ uv run python main.py --config examples/ai-jobs/output-ollama/config.json

[INFO]  debate.orchestrator: Debate starting: Will AI automation destroy more jobs than it creates...
[INFO]  debate.orchestrator: Positions — A: AI automation will destroy more jobs... | B: AI will generate new industries...
[INFO]  debate.orchestrator: Turn 1/20 — Pessimist
[WARNING] debate.agent.Pessimist: Attempt 1/3 failed for Pessimist: Invalid JSON: Expecting ',' delimiter
[INFO]  debate.orchestrator: Turn 1/20 accepted from Pessimist.
[INFO]  debate.orchestrator: Turn 2/20 — Optimist
[INFO]  debate.orchestrator: Turn 2/20 accepted from Optimist.
...
[INFO]  debate.orchestrator: Turn 20/20 accepted from Optimist.
[INFO]  debate.orchestrator: Verdict written to outputs/ai-jobs/20260524_220438/result.json.
```

The `WARNING` on turn 1 shows the retry system catching a JSON formatting error from the model
and recovering automatically. The debate completes all 20 turns in ~8 minutes.

**Resulting `result.json`:**

```json
{
  "winner": "Pessimist",
  "scores": {
    "Pessimist": { "logic": 9, "evidence": 9, "clarity": 8, "persuasiveness": 9, "total": 35 },
    "Optimist":  { "logic": 8, "evidence": 8, "clarity": 7, "persuasiveness": 8, "total": 31 }
  },
  "tiebreaker": "Pessimist presented more compelling evidence on displacement scale (McKinsey 800M jobs lost)...",
  "explanation": "Pessimist used more specific, recent data (ILO 2024, McKinsey 2030) to highlight displacement scale...",
  "factcheck_flags": []
}
```

**Output files produced:**

```
outputs/ai-jobs/20260524_220438/
  config.json          ← resolved configuration used for this run
  conversation.jsonl   ← one JSON line per accepted turn with token usage
  debate.log           ← full execution log (INFO + WARNING + ERROR)
  result.json          ← latest judge verdict (convenience pointer)
  result_YYYYMMDD_HHMMSS.json  ← timestamped copy, never overwritten
  run_info.json        ← timestamp, backend, command used
```

Complete example outputs for three debates are available in [`examples/`](examples/).

---

## JSON Communication Protocol

All agent-to-orchestrator communication uses strict JSON. Responses not matching the schema are rejected and retried.

**Debate turn** (debater agents):

```json
{
  "agent": "Agent A",
  "turn": 3,
  "argument": "Solar energy adoption has accelerated dramatically...",
  "references": ["https://iea.org/reports/solar-2024"]
}
```

**Judge verdict** (judge agent):

```json
{
  "winner": "Agent A",
  "scores": {
    "Agent A": { "logic": 9, "evidence": 8, "clarity": 8, "persuasiveness": 9, "total": 34 },
    "Agent B": { "logic": 7, "evidence": 7, "clarity": 7, "persuasiveness": 7, "total": 28 }
  },
  "tiebreaker": null,
  "explanation": "Agent A cited more recent empirical data...",
  "factcheck_flags": []
}
```

Use `--require-references` to reject any turn where `references` is an empty list.

---

## Backends

Four backends are available via `--backend`:

| Backend | Flag | Requires | Token tracking |
|---------|------|----------|---------------|
| Anthropic API | `--backend api` (default) | `ANTHROPIC_API_KEY` in `.env` | Yes |
| Claude Code CLI | `--backend cli` | Claude Code installed + Pro subscription | No |
| Ollama CLI | `--backend ollama-cli` | Ollama installed with target model | No |
| Ollama API | `--backend ollama` | Ollama running locally + requests package | Yes |

### api — Anthropic SDK (default)

```bash
uv run python main.py --topic "..." --backend api
```

Requires `ANTHROPIC_API_KEY` in `.env`.

### cli — Claude Code CLI

```bash
uv run python main.py --topic "..." --backend cli --model-a claude-sonnet-4-6
```

Uses `claude --model <model> --print`. Requires Claude Code and a Pro subscription.
Also updates `.claude/agents/*.md` model fields to match config.

### ollama-cli — Ollama CLI

```bash
ollama pull llama3.2
uv run python main.py --topic "..." --backend ollama-cli \
  --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

### ollama — Ollama HTTP API

```bash
uv sync --extra ollama    # installs requests package
uv run python main.py --topic "..." --backend ollama \
  --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

Override the Ollama server URL:

```bash
OLLAMA_BASE_URL=http://192.168.1.10:11434 uv run python main.py --topic "..." --backend ollama
```

---

## Running with Ollama (free local backend)

During development and testing, running every debate turn against the Anthropic API burns real tokens quickly — a 20-turn debate with a judge call can cost $0.05–$0.20 per run. [Ollama](https://ollama.com) lets you run open-source models locally at zero cost.

### 1. Install Ollama

**Windows / macOS:** download the installer from [ollama.com/download](https://ollama.com/download) and run it.

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull a model

```bash
ollama pull qwen3:14b       # good balance of quality and speed on a modern GPU
ollama pull llama3.2        # lighter option for slower machines
```

### 3. Run a debate with Ollama

```bash
uv run python main.py \
  --topic "Will AI automation destroy more jobs than it creates?" \
  --backend ollama-cli \
  --model-a qwen3:14b --model-b qwen3:14b --model-judge qwen3:14b \
  --turns 20
```

### 4. Which backend to choose

| Situation | Recommended backend |
|-----------|-------------------|
| Production / best quality | `api` (Anthropic Claude) |
| Development, cost-free iteration | `ollama-cli` |
| Ollama on a remote server | `ollama` (HTTP API) |
| You have Claude Code + Pro subscription | `cli` |

> **Note:** Ollama models follow instructions less reliably than Claude and may occasionally produce malformed JSON. The platform's retry logic handles this automatically.

### 5. Example debates run with Ollama

See [`examples/`](examples/) for complete run outputs using `qwen3:14b` via `ollama-cli`:
- `examples/iran-nuclear/output-ollama/` — diplomatic vs military approach
- `examples/ai-jobs/output-ollama/` — AI job displacement debate
- `examples/messi-ronaldo/output-ollama/` — GOAT debate

---

## Configuration

All config is externalised — no hard-coded values in source code.

| File | Purpose |
|------|---------|
| `config/setup.json` | Application defaults (turns, timeouts, token limits) |
| `config/rate_limits.json` | Per-backend rate limits and retry config |
| `.env` | Secrets (API keys) — never committed |
| `.env.example` | Template for `.env` |

---

## Output

Each run creates a timestamped folder under `--outdir`:

```
outputs/20260101_120000/
  config.json                    # resolved configuration for this run
  conversation.jsonl             # one line per completed turn
  debate.log                     # full execution log
  result.json                    # latest judge verdict (convenience pointer)
  result_20260101_120500.json    # timestamped copy — never overwritten
  run_info.json                  # backend, argv, run timestamp
```

Running the judge multiple times on the same debate appends new `result_<timestamp>.json` files without overwriting previous verdicts.

---

## Running Tests

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests (quick)
uv run pytest -q

# Run with coverage report
uv run pytest --cov=src --cov=orchestrator --cov-report=term-missing

# Run a specific test file
uv run pytest tests/unit/test_validator.py -v
```

Coverage target: ≥ 85% (current: ~89%).

---

## Linting

```bash
uv run ruff check .        # check for violations
uv run ruff check . --fix  # auto-fix fixable violations
```

Zero violations expected.

---

## Known Limitations

- **`--backend cli`** requires Claude Code installed and a Pro subscription. It is not tested in CI.
- **`--backend ollama` / `ollama-cli`** requires Ollama running locally. Install separately via [ollama.com](https://ollama.com).
- **Web search** (`web_search` skill) is available to debater agents only when using the `cli` backend and only if the agent definition requests it. It is not available via the `api` backend.
- **Token cost tracking** is only accurate for the `api` and `ollama` backends. CLI backends do not report token usage.
- **Windows MAX_PATH**: if your working directory path exceeds ~200 characters (e.g. deeply nested Hebrew-character paths), the `api` backend uses lazy imports to work around Windows path-length limits.
- **Judge timeout**: if the judge exhausts all retries, the debate state is preserved and can be resumed to re-run the judgment.

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Follow the code rules in `docs/rules.md` (150-line limit, ruff, docstrings)
3. Write tests first (TDD) — coverage must stay ≥ 85%
4. Run `uv run ruff check .` and ensure zero violations before committing
5. Use semantic commit messages: `Feature:`, `BugFix:`, `Refactor:`, `Docs:`
6. Update `docs/TODO.md` in the same commit as the work it describes
7. Open a pull request with a clear description of the change

---

## License

MIT License — see [LICENSE](LICENSE) for details.

**Credits:** Built as coursework for the AI Agent Orchestration Course. Uses the [Anthropic Claude API](https://anthropic.com) and [Ollama](https://ollama.ai).
