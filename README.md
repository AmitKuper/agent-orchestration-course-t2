# AI Debate Platform

A multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator, and scored by a judge agent.

## Table of Contents
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Sample Run](#sample-run)
- [JSON Communication Protocol](#json-communication-protocol)
- [Backends](#backends)
- [Running with Ollama (free local backend)](#running-with-ollama-free-local-backend)
- [Configuration](#configuration)
- [Output](#output)
- [Running Tests](#running-tests)
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

Every agent call passes through **APIGatekeeper** — a centralized router that enforces per-backend retry/backoff and logs every call. Backends are swappable; the rest of the system is backend-agnostic.

**Validation pipeline** (applied to every response before acceptance):

1. Empty / too-short check
2. API error marker detection
3. Disrespectful language filter
4. Markdown fence rejection (raw JSON only)
5. Unresolved placeholder rejection
6. JSON schema check (debate turn or judge verdict, depending on agent type)
7. **StanceValidator** — rejects concession phrases; agents may never agree with or yield to each other
8. **Novelty check** — rejects arguments too similar (SequenceMatcher > 0.75) to any prior turn by the same agent

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
copy .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY for --backend api
```

### macOS / Linux

```bash
git clone <repo-url>
cd HW2
uv sync
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY for --backend api
```

### With pip (alternative)

```bash
pip install -e .
pip install -e ".[dev]"      # includes ruff, pytest, pytest-cov
pip install -e ".[ollama]"   # adds requests for Ollama API backend
cp .env.example .env
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

## Sample Run

The following shows a real 20-turn debate run using the Ollama CLI backend (Qwen3:14b).
No API tokens are consumed.

```
$ python main.py --config examples/ai-jobs/config-ollama-api.json

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
  result.json          ← judge verdict, scores, explanation, factcheck flags
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

Seven backends are available via `--backend`:

| Backend | Flag | Requires | Token tracking | Description |
|---------|------|----------|---------------|-------------|
| Anthropic API | `claude-api` (default) | `ANTHROPIC_API_KEY` in `.env` | Yes | Anthropic SDK — best quality |
| Claude CLI per-turn | `claude-cli-agents` | Claude Code + Pro subscription | No | `claude --print` subprocess per turn |
| Claude CLI session | `claude-cli-session` | Claude Code + Pro subscription | No | Persistent `claude` subprocess per agent |
| Ollama HTTP API | `ollama-api` | Ollama running locally | Yes | OpenAI-compatible HTTP endpoint |
| Ollama CLI per-turn | `ollama-cli-agents` | Ollama + model pulled | No | `ollama run` subprocess per turn |
| Ollama single-shot | `ollama-cli` | Ollama + model pulled | No | One model call generates entire debate |
| Ollama orchestrator | `ollama-orchestrator` | Ollama + model pulled | No | Alias for `ollama-cli` |

Legacy aliases still accepted: `api` → `claude-api`, `cli` → `claude-cli-agents`, `ollama` → `ollama-api`.

### claude-api — Anthropic SDK (default)

```bash
python main.py --topic "..." --backend claude-api
```

Requires `ANTHROPIC_API_KEY` in `.env`.

### claude-cli-agents — Claude Code CLI

```bash
python main.py --topic "..." --backend claude-cli-agents --model-a claude-sonnet-4-6
```

Uses `claude --model <model> --print`. Requires Claude Code and a Pro subscription.
Also updates `.claude/agents/*.md` model fields to match config.

### ollama-cli-agents — Ollama CLI per-turn

```bash
ollama pull llama3.2
python main.py --topic "..." --backend ollama-cli-agents --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

### ollama-api — Ollama HTTP API

```bash
pip install ".[ollama]"
python main.py --topic "..." --backend ollama-api --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

Override the Ollama server URL:

```bash
OLLAMA_BASE_URL=http://192.168.1.10:11434 python main.py --topic "..." --backend ollama-api --model-a llama3.2
```

---

## Running with Ollama (free local backend)

During development and testing, running every debate turn against the Anthropic API burns real tokens quickly — a 20-turn debate with a judge call can cost $0.05–$0.20 per run. [Ollama](https://ollama.com) lets you run open-source models locally at zero cost, making it practical to iterate freely without watching your API bill.

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
ollama pull mistral         # alternative if you prefer Mistral
```

Check what you have installed:
```bash
ollama list
```

### 3. Run a debate with Ollama

Use a JSON config file (recommended for multi-model setups):

```json
{
  "topic": "Will AI automation destroy more jobs than it creates?",
  "turns": 20,
  "backend": "ollama-cli-agents",
  "debater_a": { "name": "Pessimist", "model": "qwen3:14b" },
  "debater_b": { "name": "Optimist",  "model": "qwen3:14b" },
  "judge":     { "model": "qwen3:14b", "factcheck": true },
  "outdir": "outputs/ai-jobs"
}
```

```bash
python main.py --config my-debate.json
```

Or inline via CLI flags:

```bash
python main.py \
  --topic "Will AI automation destroy more jobs than it creates?" \
  --backend ollama-cli-agents \
  --model-a qwen3:14b --model-b qwen3:14b --model-judge qwen3:14b \
  --turns 20
```

### 4. Which backend to choose

| Situation | Recommended backend |
|-----------|-------------------|
| Production / best quality | `claude-api` (Anthropic Claude) |
| Development, cost-free, per-turn | `ollama-cli-agents` |
| Ollama on a remote server | `ollama-api` (HTTP API) |
| You have Claude Code + Pro subscription | `claude-cli-agents` |

> **Note:** Ollama models follow instructions less reliably than Claude and may occasionally produce malformed JSON. The platform's retry logic handles this automatically — you may see more `WARNING` retry log lines than with the API backend.

### 5. Example debates run with Ollama

See [`examples/`](examples/) for complete run outputs using `qwen3:14b` via Ollama. Each topic has outputs for three backends:
- `examples/ai-jobs/output-ollama-api/` — AI job displacement, per-turn API backend
- `examples/ai-jobs/output-ollama-cli-agents/` — same topic, per-turn CLI backend
- `examples/ai-jobs/output-ollama-cli/` — same topic, single-shot orchestrator
- `examples/iran-nuclear/` and `examples/messi-ronaldo/` — same three backends each

See [`examples/analysis.md`](examples/analysis.md) for a cross-backend quality comparison.

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
  config.json                    # resolved configuration for this run
  conversation.jsonl             # one line per completed turn
  debate.log                     # full execution log
  result.json                    # latest judge verdict (convenience pointer)
  result_20260101_120500.json    # timestamped copy — never overwritten
```

Running the judge multiple times on the same debate appends new `result_<timestamp>.json` files without overwriting previous verdicts.

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
