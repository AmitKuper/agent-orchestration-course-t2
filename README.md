# AI Debate Platform

A multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator, and scored by a judge agent.

## Setup

```bash
pip install -r requirements.txt   # or: pip install .
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=your-key
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
| `--model-judge` | claude-sonnet-4-6 | Model for the judge |
| `--max-retries` | 3 | Retries per invalid response |
| `--outdir` | output/ | Base output directory |
| `--factcheck` | off | Enable factual accuracy checks |
| `--log-level` | INFO | DEBUG / INFO / WARNING / ERROR |
| `--config` | — | Path to YAML config file |

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
