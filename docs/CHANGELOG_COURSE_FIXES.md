# Changelog — Course Assignment Fixes

Changes made to satisfy the AI Agent Orchestration Course HW2 requirements.
All items below were identified in `docs/AUDIT.md`.

---

## Build System

**pyproject.toml — build backend corrected**
- `setuptools.backends.legacy:build` → `setuptools.build_meta`
- Added `wheel` to `build-system.requires`
- Pinned `anthropic>=0.40.0,<0.100.0` to exclude broken 0.104.x on Windows

---

## SDK Entry Point

**main.py — CLI now delegates to DebateSDK**
- Removed direct `DebateOrchestrator` construction from `main.py`
- `main()` now creates `DebateSDK()` and calls `sdk.run(config)` or `sdk.resume(config)`
- All external consumers (CLI, tests, notebooks) route through the SDK layer only

---

## Backend Naming

**src/backends/_factory.py — backend identifiers clarified**
- `ollama-cli` → `OllamaCliBackend` (per-agent CLI, one process per turn)
- `ollama-orchestrator` → `OllamaOrchestratorBackend` (single-shot orchestrator mode)
- Removed ambiguous mapping that returned `OllamaOrchestratorBackend` for `ollama-cli`

---

## APIGatekeeper Integration

**src/backends/_api.py**
- Lazy `import anthropic` via `_get_anthropic()` module-level loader (Windows MAX_PATH fix)
- Deferred client creation via `_ensure_client()` called at first `invoke()`
- All API calls routed through `APIGatekeeper("anthropic")`

**src/backends/_ollama.py**
- HTTP requests wrapped through `APIGatekeeper("ollama")`

**src/backends/_cli.py**
- `subprocess.run()` wrapped through `APIGatekeeper("cli")`
- Added `timeout=DEBATER_TIMEOUT` to all subprocess calls
- `--dangerously-skip-permissions` now conditional on `CLAUDE_SKIP_PERMISSIONS` env var (default `true`)

**src/backends/_persistent_cli.py**
- Same `CLAUDE_SKIP_PERMISSIONS` env-var guard applied

---

## Strict JSON Protocol Validation

**src/validator.py — ResponseValidator extended**
- `validate()` now rejects markdown fences (`` ``` ``) before JSON parsing
- `validate()` now rejects unresolved `$PLACEHOLDER` tokens
- `validate_debate_turn()` — full JSONL protocol: validates `agent`, `turn`, `argument`, `references` fields, types, agent/turn equality, optional `require_references`
- `validate_judge_verdict()` — validates `winner` (must be one of the two debater names), `scores` (all four criteria 0–10), `explanation` (non-empty), `factcheck_flags` (list)

**src/agents/base.py — `_validate_response()` hook added**
- `invoke_with_retry()` now calls `self._validate_response(response)` instead of direct validator call
- Subclasses can override `_validate_response()` to use a different validation schema

**src/agents/judge.py — verdict validation override**
- `JudgeAgent._validate_response()` calls `validate_judge_verdict()` with `agent_a_name` / `agent_b_name`
- Fixes critical bug where judge responses were being validated against the debate-turn schema, causing all retries to exhaust and integration tests to fail

---

## StanceValidator

**src/stance_validator.py — new service**
- Rule-based concession phrase detector using regex word boundary matching
- Detected phrases include: "I agree with", "you are right", "I concede", "I changed my mind", and 10+ variants
- Returns `StanceResult(valid, reason)` including the assigned position in the failure reason

**src/agents/base.py — StanceValidator integrated**
- `BaseAgent` initializes `StanceValidator` and `_assigned_position: str | None`
- After format validation passes, stance is checked if `_assigned_position` is set
- Stance failure produces a `content`-category retry (full history re-attached)

**src/agents/debate.py**
- `DebateAgent.__init__` sets `self._assigned_position = position`

---

## Result File Preservation

**src/output.py — `write_result()` now writes two files**
- `result_YYYYMMDD_HHMMSS.json` — timestamped, never overwritten; each judge run appends a new file
- `result.json` — convenience pointer to the latest verdict

---

## Configuration

**src/config.py**
- Added `require_references: bool = False` field to `DebateConfig`
- Added `--require-references` CLI flag
- Added `ollama-orchestrator` to backend choices

---

## Repository Hygiene

**.gitignore**
- Added: `.venv/`, `.ruff_cache/`, `htmlcov/`, `.coverage`, `*.egg-info/`, `dist/`, `build/`

**.env.example**
- Consolidated `.env-example` and `.env.example` into a single `.env.example`
- Added `CLAUDE_SKIP_PERMISSIONS` entry with documentation

**uv.lock**
- Generated via `uv lock` — reproducible dependency resolution

---

## Test Suite

- All integration tests updated to patch `src.backends._api._get_anthropic` instead of `anthropic.Anthropic` (Windows MAX_PATH compatibility)
- All tests that invoke the gatekeeper patch `src.shared.gatekeeper.time.sleep` to avoid real retry delays
- New unit tests: `tests/unit/test_validator.py` (35+ tests), `tests/unit/test_stance_validator.py` (7 tests)
- **190 tests, 0 failures, 89% coverage** (target: ≥ 85%)
- **0 ruff violations**

---

## Topic Validator

**src/topic_validator.py**
- Fallback Anthropic SDK path uses `from src.backends._api import _get_anthropic` (lazy import, Windows safe)
