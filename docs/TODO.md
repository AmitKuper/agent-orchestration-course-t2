# TODO: AI Debate Platform

## Phase 1 — Project Scaffold ✅ Complete
- [x] Create full directory tree (empty `__init__.py` files, placeholder stubs)
- [x] `pyproject.toml` — deps: `anthropic`, `python-dotenv`, `pyyaml`, `ruff`, `pytest`, `pytest-cov`
- [x] `.env.example` — `ANTHROPIC_API_KEY=`
- [x] `src/constants.py` — defaults, timeout values, file name constants
- [x] `src/config.py` — `DebateConfig` dataclass, `build_cli_parser()`, `load_config()`, `save_config()`
- [x] `src/logger.py` — `setup_logger()` with dual console + file handlers
- [x] `main.py` — CLI entry point, parses config, stubs orchestrator call

## Phase 2 — Infrastructure Layer ✅ Complete
- [x] `src/state.py` — `ConversationState`: `append_turn()`, `load_from_file()`, `is_complete()`, `needs_resume()`
- [x] `src/output.py` — `OutputManager`: `create_run_folder()`, `result_path()`, path properties
- [x] `src/watchdog.py` — `Watchdog`: `start()`, `cancel()`, context manager
- [x] `src/validator.py` — `ResponseValidator`: `validate()`, `ValidationResult` dataclass with `category` field
- [x] `src/cost.py` — `CostTracker`: `record_call()`, `get_run_summary()`, `append_to_cost_md()`

## Phase 3 — Agent & Skill Definitions ✅ Complete
- [x] `.claude/agents/debate-orchestrator.md` — tools: Bash, Read, Write; skills: validate_topic, validate_stance, validate_json
- [x] `.claude/agents/debate-agent.md` — tools: WebSearch; skills: web_search; outputs JSONL line
- [x] `.claude/agents/debate-judge.md` — tools: WebSearch, Bash, Read; skills: judgment, validate_json, web_search; outputs JSON object
- [x] `.claude/skills/validate_json/SKILL.md` — Python json.load check; input/output JSON
- [x] `.claude/skills/validate_topic/SKILL.md` — inline LLM call; extracts two opposing positions
- [x] `.claude/skills/validate_stance/SKILL.md` — inline LLM call; checks argument supports assigned claim
- [x] `.claude/skills/judgment/SKILL.md` — reads JSONL, invokes judge agent, saves verdict; user-invocable via `/judgment`
- [x] `.claude/skills/web_search/SKILL.md` — WebSearch tool wrapper; returns results with references
- [x] `src/agents/base.py` — `BaseAgent` ABC: `invoke_with_retry()`, `_invoke()`, `_build_format_retry_prompt()`, `_build_content_retry_prompt()`
- [x] `src/agents/debate.py` — `DebateAgent`: `build_prompt()`, `_format_history()`, `_invoke()`
- [x] `src/agents/judge.py` — `JudgeAgent`: `build_scoring_prompt()`, `parse_verdict()`, `_validate_verdict()`, `_invoke()`

## Phase 4 — Orchestrator & Debate Flow ✅ Complete
- [x] `src/exceptions.py` — `InvalidTopicError`
- [x] `src/topic_validator.py` — `validate_topic()` helper via Claude API
- [x] `orchestrator.py` — `DebateOrchestrator`: `validate_topic()`, `initialize_agents()`, `run_turn()`, `run_debate()`, `resume_debate()`
- [x] `main.py` — wired to `DebateOrchestrator`, handles new vs resume flow

## Phase 5 — Output & Cost Finalization ✅ Complete
- [x] `OutputManager.write_config()` — saves resolved config as JSON
- [x] `OutputManager.write_result()` — writes verdict to uniquely timestamped result file
- [x] `CostTracker.append_to_cost_md()` — appends markdown table row to `docs/cost.md`
- [x] `docs/cost.md` — initialized with header row
- [x] Log file flush/close on debate end or crash (atexit in `DebateOrchestrator`)

## Phase 6 — Tests ✅ Complete (aac73ea)
- [x] `tests/unit/test_config.py`
- [x] `tests/unit/test_state.py`
- [x] `tests/unit/test_validator.py`
- [x] `tests/unit/test_watchdog.py`
- [x] `tests/unit/test_output.py`
- [x] `tests/unit/test_cost.py`
- [x] `tests/unit/test_base_agent.py`
- [x] `tests/unit/test_debate_agent.py`
- [x] `tests/unit/test_judge_agent.py`
- [x] `tests/unit/test_topic_validator.py`
- [x] `tests/integration/test_full_debate.py`
- [x] `tests/integration/test_resume.py`
- [x] `tests/integration/test_judge_standalone.py`
- [x] Coverage ≥ 85% (100% achieved, 128 tests passing)

## Phase 7 — Polish & Documentation ✅ Complete (2a6a1e5)
- [x] Zero Ruff violations (`ruff check` + `ruff format`)
- [x] All docstrings complete (every class, method, function)
- [x] `README.md` — setup, `.env` config, usage examples
- [x] Final `docs/TODO.md` update — all phases complete

## Phase 8 — Post-Polish Improvements ✅ Complete (6151f77)
- [x] `src/backends/` package — split `src/backends.py` into `_base.py`, `_api.py`, `_cli.py`, `_ollama.py`, `_factory.py`
- [x] `src/backends/_ansi.py` — VT100 terminal emulator; strips ANSI escape codes and Qwen3 thinking preambles from CLI output
- [x] `src/agents/loader.py` — extracted `load_agent_def` from `base.py` to dedicated module
- [x] `src/debate_helpers.py` — extracted turn-execution helpers from orchestrator
- [x] `src/sdk/debate_sdk.py` — `DebateSDK` high-level API wrapper
- [x] `src/shared/gatekeeper.py` — `APIGatekeeper` rate-limit / concurrency guard
- [x] `src/shared/version.py` — package version constant
- [x] Logger hierarchy fix — handlers attached to root `debate` logger so all child loggers write to file
- [x] Retry categorisation — `ValidationResult.category` (`"format"` vs `"content"`) controls retry prompt strategy
- [x] Judge verdict schema enforcement — `parse_verdict` validates all four criteria, normalises key case, recomputes totals
- [x] Turn-skip log level raised from `WARNING` to `ERROR` (unrecoverable debate content loss)
- [x] Test files split to comply with 150-line limit (13 unit + 5 integration files, 160 tests passing)
- [x] `tests/unit/test_backend_factory.py`, `test_api_backend.py`, `test_cli_backend.py`, `test_ollama_backend.py`, `test_ollama_cli_backend.py`
- [x] `tests/unit/test_agent_file_model.py`, `test_orchestrator_core.py`, `test_orchestrator_judge.py`
- [x] `tests/unit/test_debate_sdk.py`, `test_gatekeeper.py`, `test_version.py`
- [x] `tests/integration/test_debate_config_file.py`, `test_resume_complete.py`
- [x] `examples/` restructured to topic-first layout (`examples/<topic>/output-<backend>/`)
- [x] Example debates: `iran-nuclear`, `ai-jobs`, `messi-ronaldo` (all via ollama-cli / Qwen3:14b)

## Phase 9 — Course Compliance Fixes ✅ Complete (759a380)
- [x] Build system corrected (`setuptools.build_meta`, `uv.lock`)
- [x] `main.py` delegates to `DebateSDK` — SDK layer as sole entry point
- [x] `APIGatekeeper` wraps all external calls (Anthropic SDK, Ollama HTTP, subprocess)
- [x] `StanceValidator` — 19 concession phrases, integrated into `BaseAgent` validation chain
- [x] `validate_debate_turn()` and `validate_judge_verdict()` — strict JSON protocol validation
- [x] `--require-references` flag; `require_references` field in `DebateConfig`
- [x] `write_result()` — timestamped result files (`result_YYYYMMDD_HHMMSS.json` + `result.json` pointer)
- [x] `JudgeAgent._validate_response()` override — uses `validate_judge_verdict()` schema
- [x] `.env.example` consolidated; `.gitignore` updated; `docs/AUDIT.md` + `docs/CHANGELOG_COURSE_FIXES.md`
- [x] 190 tests, 0 failures, ≥ 85% coverage

## Phase 10 — Novelty Validation & Ollama Orchestrator ✅ Complete (ef35e99, 4f9ac4a)
- [x] `OllamaOrchestratorBackend` — single-call backend; Qwen3 thinking-mode output parsed with brace-balanced scanner
- [x] `validate_novelty()` in `ResponseValidator` — SequenceMatcher threshold 0.75
- [x] `_extra_validate()` hook in `BaseAgent`; `DebateAgent` overrides to run novelty check
- [x] `NOVELTY_THRESHOLD = 0.75` constant in `src/constants.py`
- [x] "Never repeat arguments" rule added to `.claude/agents/debate-agent.md` skill definition
- [x] `tests/integration/test_novelty_from_outputs.py` — parametrized tests against real debate outputs
- [x] 9-run sweep (3 topics × 3 backends): all 20/20 turns, zero post-novelty repeats in 8/9 runs
- [x] `examples/analysis.md` — cross-backend quality analysis; `analyze_results.py` helper
- [x] 202 tests, 0 failures, 100% coverage
