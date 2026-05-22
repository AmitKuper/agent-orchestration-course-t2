# AI Debate Platform

A multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator, and scored by a judge agent.

## Setup

```bash
pip install -r requirements.txt   # or: pip install .
cp .env.example .env
# edit .env — only required for --backend api (see Backends below)
```

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
| `--outdir` | output/ | Base output directory |
| `--factcheck` | off | Enable factual accuracy checks |
| `--log-level` | INFO | DEBUG / INFO / WARNING / ERROR |
| `--config` | — | Path to YAML config file |
| `--backend` | api | Invocation backend — see below |

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

## Backends

Three backends are available via `--backend`:

| Backend | Flag | Requires | Token tracking |
|---------|------|----------|---------------|
| Anthropic API | `--backend api` (default) | `ANTHROPIC_API_KEY` in `.env` | Yes |
| Claude Code CLI | `--backend cli` | Claude Code installed + Pro subscription | No (records 0) |
| Ollama | `--backend ollama` | Ollama running locally + `pip install requests` | Yes |

### api — Anthropic SDK (default)

Calls the Anthropic Messages API directly. Requires a paid API key in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### cli — Claude Code CLI

Shells out to `claude --print` for each agent call, using your Pro OAuth session.
No API key needed.

```bash
python main.py --topic "..." --backend cli
```

To route CLI calls through a local Ollama model, run `ollama launch claude` in a
separate terminal before starting the debate — Claude Code will pick it up automatically.

### ollama — Direct Ollama API

Calls Ollama's OpenAI-compatible REST endpoint directly.
Install the extra dependency first:

```bash
pip install ".[ollama]"   # installs requests
```

Set `--model-a`, `--model-b`, and `--model-judge` to your Ollama model names:

```bash
python main.py --topic "..." --backend ollama --model-a llama3.2 --model-b llama3.2 --model-judge llama3.2
```

Override the default base URL if Ollama is not on localhost:

```bash
OLLAMA_BASE_URL=http://192.168.1.10:11434 python main.py --topic "..." --backend ollama --model-a llama3.2
```

## Output

Each run creates a timestamped folder under `--outdir`:

```
output/20260101_120000_nuclear_energy.../
  config.json          # resolved configuration
  conversation.jsonl   # one line per completed turn
  debate.log           # full execution log
  result_<ts>.json     # judge verdict and scores
```

## Running tests

```bash
pytest tests/ --cov=src --cov=orchestrator
```

Coverage target: ≥ 85% (currently 96%).
