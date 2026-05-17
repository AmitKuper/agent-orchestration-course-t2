# TODO: AI Debate Platform

## Phase 1 — Project Scaffold ✅ Complete
- [x] Create full directory tree (empty `__init__.py` files, placeholder stubs)
- [x] `pyproject.toml` — deps: `anthropic`, `python-dotenv`, `pyyaml`, `ruff`, `pytest`, `pytest-cov`
- [x] `.env.example` — `ANTHROPIC_API_KEY=`
- [x] `src/constants.py` — defaults, timeout values, file name constants
- [x] `src/config.py` — `DebateConfig` dataclass, `build_cli_parser()`, `load_config()`, `save_config()`
- [x] `src/logger.py` — `setup_logger()` with dual console + file handlers
- [x] `main.py` — CLI entry point, parses config, stubs orchestrator call

## Phase 2 — Infrastructure Layer
- [ ] `src/state.py` — `ConversationState`: `append_turn()`, `load_from_file()`, `is_complete()`, `needs_resume()`
- [ ] `src/output.py` — `OutputManager`: `create_run_folder()`, `result_path()`, path properties
- [ ] `src/watchdog.py` — `Watchdog`: `start()`, `cancel()`, context manager
- [ ] `src/validator.py` — `ResponseValidator`: `validate()`, `ValidationResult` dataclass
- [ ] `src/cost.py` — `CostTracker`: `record_call()`, `get_run_summary()`, `append_to_cost_md()`

## Phase 3 — Agent & Skill Definitions
- [ ] `.claude/agents/orchestrate/AGENT.md` — tools: Bash, Agent, Read, Write; skills: validate_topic, validate_stance, validate_json
- [ ] `.claude/agents/debate/AGENT.md` — tools: WebSearch; skills: web_search; outputs JSONL line
- [ ] `.claude/agents/judge/AGENT.md` — tools: WebSearch; skills: judgment, validate_json, web_search; outputs JSON object
- [ ] `.claude/skills/validate_json/SKILL.md` — Python json.load check; input/output JSON
- [ ] `.claude/skills/validate_topic/SKILL.md` — inline LLM call; extracts two opposing positions
- [ ] `.claude/skills/validate_stance/SKILL.md` — inline LLM call; checks argument supports assigned claim
- [ ] `.claude/skills/judgment/SKILL.md` — reads JSONL, invokes judge agent, saves verdict; user-invocable via `/judgment`
- [ ] `.claude/skills/web_search/SKILL.md` — WebSearch tool wrapper; returns results with references

## Phase 4 — Orchestrator & Debate Flow
- [ ] `src/agents/base.py` — `BaseAgent` ABC: `invoke_with_retry()`, `_invoke()`, `_build_retry_prompt()`
- [ ] `src/agents/debate.py` — `DebateAgent`: `_build_prompt()`, `_format_history()`, `_invoke()`
- [ ] `src/agents/judge.py` — `JudgeAgent`: `_build_scoring_prompt()`, `_parse_verdict()`, `_invoke()`
- [ ] `orchestrator.py` — `DebateOrchestrator`: `validate_topic()`, `initialize_agents()`, `run_turn()`, `run_debate()`, `resume_debate()`
- [ ] `InvalidTopicError` — raised when topic cannot be split into two opposing sides

## Phase 5 — Output & Cost Finalization
- [ ] `OutputManager.write_config()` — saves resolved config as JSON
- [ ] `OutputManager.write_result()` — writes verdict to uniquely timestamped result file
- [ ] `CostTracker.append_to_cost_md()` — appends markdown table row to `docs/cost.md`
- [ ] `docs/cost.md` — initialize with header row
- [ ] Log file flush/close on debate end or crash (`atexit` or context manager)

## Phase 6 — Tests
- [ ] `tests/unit/test_config.py`
- [ ] `tests/unit/test_state.py`
- [ ] `tests/unit/test_validator.py`
- [ ] `tests/unit/test_watchdog.py`
- [ ] `tests/unit/test_output.py`
- [ ] `tests/unit/test_cost.py`
- [ ] `tests/unit/test_base_agent.py`
- [ ] `tests/unit/test_debate_agent.py`
- [ ] `tests/unit/test_judge_agent.py`
- [ ] `tests/unit/test_orchestrator.py`
- [ ] `tests/integration/test_full_debate.py`
- [ ] `tests/integration/test_resume.py`
- [ ] `tests/integration/test_judge_standalone.py`
- [ ] Coverage ≥ 85%

## Phase 7 — Polish & Documentation
- [ ] Zero Ruff violations (`ruff check` + `ruff format`)
- [ ] All docstrings complete (every class, method, function)
- [ ] `README.md` — setup, `.env` config, usage examples
- [ ] Final `docs/TODO.md` update — mark all phases complete with commit hashes
