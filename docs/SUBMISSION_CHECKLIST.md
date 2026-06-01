# Submission Checklist

Run these commands in order to verify the project before grading.

## Setup

```bash
git clone https://github.com/AmitKuper/agent-orchestration-course-t2.git
cd agent-orchestration-course-t2
git checkout fix/course-submission-compliance
uv sync --extra dev
```

## Verification commands

```bash
# 1. Tests
uv run pytest -q
# Expected: 202 passed, 10 skipped (skipped = tests that require live Ollama/Claude CLI)

# 2. Coverage
uv run pytest --cov=src --cov=orchestrator --cov-report=term-missing
# Expected: Total coverage ≥ 85%

# 3. Lint
uv run ruff check .
# Expected: All checks passed

# 4. Syntax check
uv run python -m compileall -q .
# Expected: no output (clean)

# 5. Lock file present
ls uv.lock
# Expected: file exists
```

## Course requirements checklist

| Requirement | Where | Status |
|-------------|-------|--------|
| Parent orchestrator controls debate | `orchestrator.py`, `DebateOrchestrator` | ✓ |
| Two child agents argue opposite sides | `src/agents/debate.py`, `DebateAgent` | ✓ |
| Agents do not talk to each other directly | orchestrator routes all turns | ✓ |
| JSON/JSONL communication protocol | `src/protocol_validator.py`, `src/validator.py` | ✓ |
| ≥ 10 accepted arguments per side (default 20 turns) | `config/setup.json`, `DebateConfig.turns=20` | ✓ |
| Respectful language enforced | `ResponseValidator._contains_disrespectful_language` | ✓ |
| Stance enforced | `StanceValidator`, `src/stance_validator.py` | ✓ |
| Judge gives structured verdict | `src/agents/judge.py`, `src/verdict_validator.py` | ✓ |
| No ties in judge verdict | `JudgeAgent.parse_verdict` raises on equal totals with no tiebreaker | ✓ |
| SDK is main entry point | `main.py` → `DebateSDK` → `DebateOrchestrator` | ✓ |
| API Gatekeeper controls external calls | `src/shared/gatekeeper.py`, RPM sliding window | ✓ |
| Configuration externalized | `src/config.py`, `config/setup.json`, CLI flags | ✓ |
| No secrets in repo | `.env` gitignored, only placeholder in `.env.example` | ✓ |
| uv is the package workflow | `pyproject.toml`, `uv.lock` present | ✓ |
| `uv.lock` exists | repo root | ✓ |
| README accurate | `README.md` — uv-first, known limitations section | ✓ |
| Tests pass | `uv run pytest -q` → 202 passed | ✓ |
| Coverage ≥ 85% | `uv run pytest --cov` → ~89% | ✓ |
| Ruff zero violations | `uv run ruff check .` → All checks passed | ✓ |
| Outputs documented | `README.md` Output section, `docs/CHANGELOG_COURSE_FIXES.md` | ✓ |
| Limitations documented honestly | `README.md` Known Limitations, CHANGELOG Submission Readiness | ✓ |

## Known limitations (honest)

- `--backend claude-api` requires `ANTHROPIC_API_KEY` — not available in CI
- `--backend claude-cli-agents` / `claude-cli-session` require Claude Code CLI + Pro subscription
- `--backend ollama*` require local Ollama installation (`ollama pull <model>`)
- `web_search` skill is available only via CLI backends that include it in the agent definition
- Token cost tracking only accurate for `api` and `ollama-api` backends
- `PersistentCliBackend` is experimental and does not route through APIGatekeeper
- 10 tests are skipped in CI because they require live external services

## Branch and PR

- **Branch**: `fix/course-submission-compliance`
- **Target**: `master`
- **PR**: https://github.com/AmitKuper/agent-orchestration-course-t2/pull/new/fix/course-submission-compliance
