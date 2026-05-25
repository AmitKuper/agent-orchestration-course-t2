# Compliance Audit — AI Debate Platform

**Date:** 2026-05-26  
**Auditor:** Claude Code (automated compliance review)  
**Branch:** fix/course-submission-compliance

---

## 1. Assignment Requirements

| # | Requirement |
|---|-------------|
| 1 | Orchestrator/parent agent controls full debate process |
| 2 | Two child debater agents (FOR and AGAINST) |
| 3 | Debaters must not communicate directly |
| 4 | All communication passes through orchestrator |
| 5 | Debates must be respectful |
| 6 | Each side produces ≥ 10 accepted arguments by default |
| 7 | Judge decides winner with explanation |
| 8 | Clear JSON/JSONL communication protocol |
| 9 | `.env`-based secrets, no committed keys |
| 10 | `uv` for project commands (not pip) |
| 11 | SDK architecture |
| 12 | API Gatekeeper for all external calls |
| 13 | Professional logging |
| 14 | Configuration files (no hardcoded runtime values) |
| 15 | Tests and documentation |
| 16 | Web search support or honest documentation of limitations |

### Professional Software Requirements

| # | Requirement |
|---|-------------|
| P1 | README.md in project root |
| P2 | docs/PRD.md |
| P3 | docs/PLAN.md |
| P4 | docs/TODO.md |
| P5 | SDK layer as main entry point |
| P6 | API Gatekeeper for all external calls |
| P7 | Configuration in config files |
| P8 | No hardcoded secrets |
| P9 | `.env.example` with placeholders only |
| P10 | pyproject.toml |
| P11 | uv.lock |
| P12 | Tests under `tests/` |
| P13 | Coverage ≥ 85% |
| P14 | Ruff linting |
| P15 | Modular code |
| P16 | Meaningful logs |
| P17 | Good error handling |

---

## 2. What the Current Project Already Implements

### Architecture ✅
- `DebateOrchestrator` class in `orchestrator.py` manages full lifecycle
- `DebateAgent` in `src/agents/debate.py` — two instances created for A and B
- `JudgeAgent` in `src/agents/judge.py` — invoked after all turns
- Debaters never communicate directly; orchestrator brokers all calls
- 20 default turns (10 per agent) — meets the ≥10 per side requirement
- Respectful language validation via `DISRESPECTFUL_PATTERNS` in `ResponseValidator`

### JSON Protocol ✅
- Conversation stored as JSONL (one line per turn)
- Turn format: `{"agent": "...", "turn": N, "argument": "...", "references": [...]}`
- Judge verdict format: `{"winner": "...", "scores": {...}, "explanation": "...", "factcheck_flags": [...]}`

### Secrets ✅
- `ANTHROPIC_API_KEY` read from environment via `python-dotenv`
- Both `.env-example` and `.env.example` present (redundant — to be consolidated)
- `.env` in `.gitignore`

### Logging ✅
- Dual console + file logger in `src/logger.py`
- Configurable log level: DEBUG, INFO, WARNING, ERROR
- All agents use hierarchical loggers under `debate.*`

### Configuration ✅
- `config/setup.json` for defaults
- `config/rate_limits.json` for per-backend rate limits
- Three-level precedence: CLI > config file > defaults
- `DebateConfig` dataclass in `src/config.py`

### SDK Layer — Partial ✅
- `DebateSDK` exists in `src/sdk/debate_sdk.py`
- BUT: `main.py` bypasses `DebateSDK` and directly constructs `DebateOrchestrator`

### API Gatekeeper — Partial ✅
- `APIGatekeeper` exists in `src/shared/gatekeeper.py`
- Reads `config/rate_limits.json`
- Implements retry with exponential back-off
- BUT: Backends (`_api.py`, `_cli.py`, `_ollama.py`) call external services **directly** without routing through the gatekeeper

### Validation ✅
- `ResponseValidator` in `src/validator.py`
- Checks: empty, length, API error markers, disrespectful language, JSON parsing
- BUT: Does not validate JSON protocol fields (agent, turn, argument, references)
- BUT: Does not validate judge verdict schema fields beyond JSON parsing

### Tests ✅
- 23 test files across `tests/unit/` and `tests/integration/`
- Good mock coverage for external services

### Documentation ✅
- README.md (344 lines)
- `docs/PRD.md`, `docs/PLAN.md`, `docs/TODO.md`, `docs/rules.md`
- Multiple PRD documents for specific subsystems

---

## 3. What Is Missing

### Critical Missing Items

| # | Item | Severity |
|---|------|----------|
| M1 | `main.py` does not use `DebateSDK` — violates SDK-first requirement | High |
| M2 | Backends bypass `APIGatekeeper` — all external calls are direct | High |
| M3 | `ResponseValidator` lacks strict JSON protocol field validation | High |
| M4 | No Python `StanceValidator` service | High |
| M5 | `uv.lock` not present | High |
| M6 | `pyproject.toml` build system broken (setuptools.backends error) | High |
| M7 | Subprocess calls lack `timeout` parameter — watchdog cannot kill processes | Medium |
| M8 | No `require_references` config flag | Medium |
| M9 | `write_result()` always writes to `result.json` — overwrites on re-run | Medium |
| M10 | `.gitignore` missing: `.venv/`, `htmlcov/`, `.coverage`, `.ruff_cache/`, `uv.lock` (no — should be tracked) | Low |
| M11 | Both `.env-example` and `.env.example` exist — redundant | Low |
| M12 | README lacks: uv commands, architecture diagram, full output file docs | Low |
| M13 | Missing docs: `AUDIT.md`, `ARCHITECTURE.md`, `PROMPTS.md`, `TESTING.md` | Low |
| M14 | Backend name confusion: `ollama-cli` returns `OllamaOrchestratorBackend` (single-shot), not a per-agent CLI | Medium |

---

## 4. What Is Buggy

| # | Bug | File | Impact |
|---|-----|------|--------|
| B1 | `pyproject.toml` uses `setuptools.backends.legacy:build` which fails with newer setuptools | `pyproject.toml` | Build fails with `uv sync` |
| B2 | `ollama-cli` backend string maps to `OllamaOrchestratorBackend` (self-orchestrating single call), contradicting the name which implies per-agent CLI | `src/backends/_factory.py` | Confusing; test expectations may be wrong |
| B3 | `write_result()` writes to fixed `result.json` path, overwriting any previous verdict if judge is re-invoked | `src/output.py` | Data loss on re-judge |
| B4 | `subprocess.run()` in `_cli.py` and `_ollama_orchestrator.py` has no `timeout` argument — watchdog fires callback but process is not killed | `src/backends/_cli.py` | Processes can hang indefinitely |
| B5 | `CliBackend` hardcodes `--dangerously-skip-permissions` in every invocation without config opt-out | `src/backends/_cli.py` | Security default concern |
| B6 | `_build_format_retry_prompt` says "no history re-attach" but `prompt` arg still includes history from the calling site | `src/agents/base.py` | Minor inconsistency |

---

## 5. What Is Unclear / Should Be Asked

1. **Debate history memory files**: The `.claude/agents/debate-agent.md` references `$TURN_NUMBER` and `$TURNS_REMAINING` as placeholders. These are resolved dynamically in `debate.py:build_prompt()`. This is correct — but the agent file itself acts only as a system prompt template. Is there an expectation that the agent file also be used for Claude Code skill invocations?

2. **Web search requirement**: The `debate-agent.md` skill specifies `WebSearch` tool availability, but this only works when running inside Claude Code. For API/Ollama backends, web search is unavailable. The assignment mentions "web search or research requirements" — should the system validate that references are non-empty (require_references flag), or is it acceptable to document this limitation?

3. **`--dangerously-skip-permissions`**: The `claude-cli-agents` backend unconditionally passes this flag. For a production/course submission, should this require explicit opt-in?

4. **OllamaOrchestratorBackend**: The `ollama-cli` self-orchestrating mode generates the entire debate in a single model call. Should this be preserved for demonstration or removed?

---

## 6. What Will Be Fixed Now

1. **[B1]** Fix `pyproject.toml` build backend to use standard `setuptools`
2. **[B2][M14]** Rename `ollama-cli` → `ollama-orchestrator`; make `ollama-cli` map to `OllamaCliBackend`
3. **[M1]** Rewrite `main.py` to delegate to `DebateSDK`
4. **[M2]** Route backend calls through `APIGatekeeper` (API, Ollama HTTP, CLI backends)
5. **[M3]** Add strict JSON field validation to `ResponseValidator`
6. **[M4]** Add `StanceValidator` Python service
7. **[B4]** Add `timeout` parameter to `subprocess.run()` calls in CLI backends
8. **[B5]** Make `--dangerously-skip-permissions` configurable via env var / config
9. **[M8]** Add `require_references` field to `DebateConfig`
10. **[B3][M9]** Fix `write_result()` to write both timestamped + `result.json` (latest)
11. **[M10][M11]** Improve `.gitignore`, consolidate to `.env.example`
12. **[M5][M12][M13]** Generate `uv.lock`, upgrade README, add missing docs

---

## 7. Known Limitations After Fixes

1. **Web search**: Only available when running inside Claude Code environment with `claude-cli-agents` or `claude-cli-session` backends. API and Ollama backends cannot perform real web search. References will be empty or agent-generated unless web search environment is active. Document honestly in README.

2. **Token cost for CLI backends**: Claude CLI and Ollama CLI backends record 0 tokens (CLI does not expose token counts). Cost tracking for these backends is approximate.

3. **`--dangerously-skip-permissions`**: Required for `claude-cli-agents` to run non-interactively. Documented as a necessary flag for this use case, configurable via `CLAUDE_SKIP_PERMISSIONS=true`.

4. **Ollama self-orchestrator**: `OllamaOrchestratorBackend` (now `ollama-orchestrator`) generates the entire debate in one model call. This is a demo mode, not a true multi-agent orchestration. Document clearly.

5. **Model availability**: API backend requires `ANTHROPIC_API_KEY`. Ollama backends require local Ollama installation. Claude CLI requires Claude Code Pro subscription.

6. **Stance validation**: The implemented `StanceValidator` uses deterministic rule-based checks (concession phrase detection). Model-assisted stance classification is available behind `STANCE_MODEL_ASSIST=true` env var but requires additional API calls.
