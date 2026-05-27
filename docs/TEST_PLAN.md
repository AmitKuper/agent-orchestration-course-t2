# Test Plan — AI Debate Platform

## 1. Test Strategy

The platform uses a **two-tier test suite**: unit tests for every class and function in
isolation, and integration tests for multi-component flows that exercise the full
orchestration pipeline.

All external I/O (Anthropic API, Ollama CLI, subprocess) is replaced with mocks in
both tiers. The only exception is `tests/integration/test_novelty_from_outputs.py`,
which validates real debate output files from `examples/` to catch regressions against
actual model behaviour.

**Coverage target:** ≥ 85% (currently **87%** — `uv run pytest --cov=src --cov=orchestrator`)

**Test runner:** pytest | **Coverage:** pytest-cov | **Reports:** pytest-html

---

## 2. Test Suite at a Glance

| Layer | Files | Tests | Coverage |
|-------|-------|-------|----------|
| Unit | 20 files | 179 tests | 87% |
| Integration | 6 files | 21 tests | — |
| **Total** | **26 files** | **200 tests** | **87%** |

---

## 3. Module Coverage

| Module | Tests File | Key Scenarios |
|--------|-----------|---------------|
| `src/config.py` | `test_config.py` | CLI override, YAML merge, missing topic, nested/flat format |
| `src/state.py` | `test_state.py` | Append/load roundtrip, `is_complete`, `needs_resume`, empty file |
| `src/validator.py` | `test_validator.py` | Empty, short, disrespectful, API error, placeholder, novelty |
| `src/protocol_validator.py` | `test_protocol_validator.py` | Missing fields, type errors, agent/turn mismatch, references |
| `src/verdict_validator.py` | `test_protocol_validator.py` | Winner, score range 0-10, empty explanation, markdown fences |
| `src/watchdog.py` | `test_watchdog.py` | Fires on timeout, cancel prevents fire, context manager |
| `src/output.py` | `test_output.py` | Folder creation, timestamped result, no overwrite |
| `src/cost.py` | `test_cost.py` | Record/accumulate, cost.md append, header on first write |
| `src/agents/base.py` | `test_base_agent.py` | Retry loop, format vs content retry, max retries exhausted |
| `src/agents/debate.py` | `test_debate_agent.py` | Prompt construction, history injection, novelty rejection |
| `src/agents/judge.py` | `test_judge_agent.py` | Verdict parsing, score normalisation, tiebreaker handling |
| `src/topic_validator.py` | `test_topic_validator.py` | Valid topic, invalid topic, fence stripping |
| `src/stance_validator.py` | `test_stance_validator.py` | Concession phrases detected, clean arguments pass |
| `src/backends/_api.py` | `test_api_backend.py` | Invoke, token recording, lazy client init |
| `src/backends/_cli.py` | `test_cli_backend.py` | Subprocess call, ANSI stripping, env var isolation |
| `src/backends/_ollama.py` | `test_ollama_backend.py` | HTTP post, response parse, timeout |
| `src/backends/_cli.py (Ollama)` | `test_ollama_cli_backend.py` | Subprocess, model arg, non-zero exit |
| `src/backends/_factory.py` | `test_backend_factory.py` | All 7 backend types, unknown raises ValueError |
| `src/shared/gatekeeper.py` | `test_gatekeeper.py` | Retry on exception, exhausted raises RuntimeError |
| `orchestrator.py` | `test_orchestrator_core.py`, `test_orchestrator_judge.py` | Turn sequencing, fallback backend, resume guard |
| `src/sdk/debate_sdk.py` | `test_debate_sdk.py` | run() returns DebateResult, resume() loads state |

---

## 4. Integration Test Scenarios

### 4.1 Full Debate — `test_full_debate.py`

A complete 4-turn debate is run via `DebateOrchestrator` with the Anthropic API
mocked at the SDK client level. Verifies the full orchestration loop: topic
validation → agent init → 4 turns alternating A/B → judge verdict → file output.

**Assertions:**
- `conversation.jsonl` contains exactly 4 entries in turn order
- `result.json` is written and contains a valid winner field
- Token usage is accumulated across all agent calls

### 4.2 Resume — `test_resume.py`

Two turns are pre-written to a JSONL file. The orchestrator is started in resume
mode and must continue from turn 3 without re-running turns 1 or 2.

**Assertions:**
- Final turn count is the configured total (not doubled)
- Turns 1 and 2 in state are identical to the pre-seeded content
- Turns 3 and 4 are added correctly

### 4.3 Resume Already Complete — `test_resume_complete.py`

An orchestrator with a fully completed state (all turns present) must raise
`RuntimeError` when `resume_debate()` is called.

### 4.4 Judge Standalone — `test_judge_standalone.py`

A `JudgeAgent` is invoked directly against a pre-built conversation state
without running any debate turns. Verifies verdict parsing and schema compliance
independently of the debate loop.

### 4.5 Config File Loading — `test_debate_config_file.py`

A JSON config file with nested `debater_a`/`debater_b`/`judge` format is loaded
via `DebateSDK`. Verifies that the nested format is flattened and CLI overrides
take precedence over file values.

### 4.6 Novelty Validation Against Real Outputs — `test_novelty_from_outputs.py`

Parametrized test that reads every `conversation.jsonl` under `examples/` and
validates that no agent repeated an argument above the 0.75 SequenceMatcher
threshold. This test uses real model output — it is the only test that touches
uncontrolled data.

---

## 5. Edge Cases and Boundary Conditions

| Scenario | Where Tested |
|----------|-------------|
| Response is empty string | `test_validator.py` |
| Response shorter than `min_response_len` | `test_validator.py` |
| Response contains disrespectful language | `test_validator.py` |
| Response is an API error message | `test_validator.py` |
| Response wrapped in markdown fences | `test_validator.py`, `test_protocol_validator.py` |
| Agent concedes or agrees with opponent | `test_stance_validator.py` |
| Argument identical to prior turn | `test_debate_agent.py` |
| Argument 76% similar to prior turn (above threshold) | `test_validator.py` |
| `references` field missing (treated as empty list) | `test_protocol_validator.py` |
| `references` required but empty | `test_protocol_validator.py` |
| Winner field not one of the two agent names | `test_protocol_validator.py` |
| Score value outside 0-10 range | `test_protocol_validator.py` |
| Judge verdict wrapped in markdown fences | `test_protocol_validator.py` |
| Max retries exhausted — turn skipped | `test_base_agent.py` |
| Watchdog fires before response arrives | `test_watchdog.py` |
| Watchdog cancelled before timeout | `test_watchdog.py` |
| Resume called on completed debate | `test_resume_complete.py`, `test_orchestrator_core.py` |
| Topic cannot be split into two sides | `test_topic_validator.py` |
| Unknown backend type | `test_backend_factory.py` |
| OrchestratorBackend uses correct fallback | `test_orchestrator_core.py` |
| JSONL file interrupted mid-write | `test_state.py` (empty-line tolerance) |
| CLI subprocess exits non-zero | `test_cli_backend.py`, `test_ollama_cli_backend.py` |
| `config/rate_limits.json` missing | `test_gatekeeper.py` |
| Nested vs flat JSON config format | `test_config.py`, `test_debate_config_file.py` |

---

## 6. Golden Run Smoke Test

`tests/integration/test_full_debate.py` is the canonical smoke test. It runs a
complete 4-turn debate through `DebateOrchestrator` with the Anthropic SDK mocked
at the lowest available level (`src.backends._api._get_anthropic`). The mock
returns structurally valid responses that pass all validation checks.

This test is the closest automated equivalent of running:

```bash
python main.py --topic "AI will replace humans" --turns 4 --backend claude-api
```

Without consuming real API tokens or requiring a network connection.

**Golden run output verified:**
```
outputs/<run>/
  config.json          ← resolved config written at debate start
  conversation.jsonl   ← 4 turn entries, schema-valid
  debate.log           ← INFO/WARNING log lines
  result.json          ← judge verdict, winner="Agent A"
  result_<ts>.json     ← timestamped copy
```

---

## 7. Running Tests and Generating Reports

### Run all tests with coverage (terminal report)

```bash
uv run pytest --cov=src --cov=orchestrator --cov-report=term
```

### Run all tests with HTML test report + HTML coverage report

```bash
uv run pytest --cov=src --cov=orchestrator --cov-report=html
```

HTML reports are written to:
- `reports/test_report.html` — test results (pass/fail, duration, failure details)
- `reports/coverage/index.html` — line-by-line coverage browser

The `addopts` setting in `pyproject.toml` automatically adds `--html=reports/test_report.html`
to every pytest invocation, so running `uv run pytest` alone generates the HTML test report.

### Run only unit tests

```bash
uv run pytest tests/unit/
```

### Run only integration tests

```bash
uv run pytest tests/integration/
```

### Run a specific module's tests

```bash
uv run pytest tests/unit/test_validator.py -v
```

### Lint check (must return 0 violations)

```bash
uv run ruff check .
```
