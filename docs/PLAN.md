# Implementation Plan: AI Debate Platform

## Architecture Overview

The system has three layers:

1. **Claude Code Agents** (`.claude/agents/`) — `orchestrate`, `debate`, `judge`; each has a defined role, tool set, and skill set
2. **Claude Code Skills** (`.claude/skills/`) — reusable capabilities invoked by agents: `validate_json`, `validate_topic`, `validate_stance`, `judgment`, `web_search`
3. **Python helper modules** (`src/`) — pure logic: config, state, validation, output, cost; no agent calls; invoked via Bash

**Invocation flow:**
```
user → /agents → orchestrate agent
                    ├─ validate_topic skill   (once, at start)
                    ├─ Bash → src/ scripts    (config, state, output)
                    ├─ debate agent           (turn 1, Agent A)
                    │    └─ web_search skill
                    ├─ validate_json skill    (after each turn)
                    ├─ validate_stance skill  (after each turn)
                    ├─ debate agent           (turn 2, Agent B)
                    │    └─ web_search skill
                    ├─ ... repeat for all turns
                    └─ judge agent            (after final turn)
                          ├─ judgment skill
                          ├─ web_search skill
                          └─ validate_json skill

user → /judgment  (standalone judge run)
    └─ judgment skill
         └─ judge agent
               ├─ web_search skill
               └─ validate_json skill
```

---

## Directory Structure

```
.claude/
  agents/
    orchestrate/
      AGENT.md            # Orchestrator — full debate lifecycle, spawns debate & judge
    debate/
      AGENT.md            # Debate agent — argues assigned position, uses web_search
    judge/
      AGENT.md            # Judge agent — scores debate, uses judgment & web_search
  skills/
    validate_json/
      SKILL.md            # Validates agent response is well-formed JSON (json.load)
    validate_topic/
      SKILL.md            # LLM call: checks topic is debatable, extracts two positions
    validate_stance/
      SKILL.md            # LLM call: checks argument supports assigned position
    judgment/
      SKILL.md            # Reads JSONL, invokes judge agent, saves verdict
    web_search/
      SKILL.md            # Web search for references and fact verification

src/
  constants.py            # All defaults and magic values
  config.py               # Config dataclass + argparse CLI + file loader/saver
  logger.py               # Dual console+file logger factory
  state.py                # JSONL read/write, turn tracking, resume detection
  validator.py            # Response validation rules + ValidationResult
  watchdog.py             # Threading-based per-agent timeout wrapper
  output.py               # Run folder creation, canonical file paths
  cost.py                 # Per-call token recording + docs/cost.md appender
  agents/
    __init__.py
    base.py               # BaseAgent ABC: invoke_with_retry(), abstract _invoke()
    debate.py             # DebateAgent: prompt builder, history formatter, Agent invocation
    judge.py              # JudgeAgent: scoring prompt builder, verdict parser

orchestrator.py           # DebateOrchestrator: full debate lifecycle
main.py                   # argparse entry point → Config → Orchestrator.run()

tests/
  unit/
    test_config.py
    test_state.py
    test_validator.py
    test_watchdog.py
    test_output.py
    test_cost.py
    test_base_agent.py
    test_debate_agent.py
    test_judge_agent.py
    test_orchestrator.py
  integration/
    test_full_debate.py   # 4-turn smoke test (reduced turns)
    test_resume.py        # Interrupt after turn 2, resume, complete
    test_judge_standalone.py

docs/
  PRD.md
  PLAN.md
  TODO.md
  rules.md
  cost.md                 # Token/cost log appended after every run

.env.example
.gitignore
pyproject.toml
README.md
```

---

## Phase 1 — Project Scaffold

**Goal:** Runnable skeleton; `python main.py --help` works; config loads; logger writes to file.

- [ ] Create full directory tree above (empty `__init__.py` files, placeholder stubs)
- [ ] `pyproject.toml` — deps: `anthropic`, `python-dotenv`, `pyyaml`, `ruff`, `pytest`, `pytest-cov`
- [ ] `.env.example` — `ANTHROPIC_API_KEY=`
- [ ] `.gitignore` — `.env`, `__pycache__`, `*.pyc`, `outputs/`, `.pytest_cache/`
- [ ] `src/constants.py`
  - Default values: `DEFAULT_TURNS = 20`, `DEFAULT_MODEL = "claude-sonnet-4-6"`, `MIN_RESPONSE_LEN = 50`, `MAX_RETRIES = 3`, `DEFAULT_OUTDIR = "outputs"`, agent timeout values, log level default
  - File name constants: `FILE_CONFIG`, `FILE_CONVERSATION`, `FILE_LOG`, `FILE_RESULT_PREFIX`
- [ ] `src/config.py`
  - `DebateConfig` dataclass: all configurable fields (topic, turns, model_a, model_b, model_judge, name_a, name_b, max_retries, min_response_len, outdir, factcheck, log_level)
  - `build_cli_parser() → ArgumentParser`
  - `load_config(args) → DebateConfig` — merges config file + CLI overrides
  - `save_config(config, path)` — writes resolved config to output folder
- [ ] `src/logger.py`
  - `setup_logger(name, log_file, level) → Logger` — attaches StreamHandler + FileHandler
- [ ] `main.py`
  - Parses CLI, builds config, stubs `Orchestrator.run(config)` call

---

## Phase 2 — Infrastructure Layer

**Goal:** State can be saved/loaded; output folders are managed; watchdog fires correctly; responses can be validated; tokens are tracked.

- [ ] `src/state.py` — `ConversationState`
  - `append_turn(turn: dict)` — writes single JSON line to JSONL file (atomic)
  - `load_from_file(path) → ConversationState` — reads all completed turns
  - `get_turns() → list[dict]`
  - `last_turn_number() → int`
  - `is_complete(total_turns: int) → bool`
  - `needs_resume(outdir) → bool` — checks for existing partial JSONL
- [ ] `src/output.py` — `OutputManager`
  - `create_run_folder(outdir, topic) → Path` — timestamped subfolder
  - Properties: `config_path`, `conversation_path`, `log_path`, `result_path()`
  - `result_path()` — generates unique timestamped filename (never overwrites)
- [ ] `src/watchdog.py` — `Watchdog`
  - `__init__(timeout_seconds, on_timeout: Callable)`
  - `start()` / `cancel()`
  - Context manager support (`__enter__` / `__exit__`)
- [ ] `src/validator.py` — `ResponseValidator`
  - `ValidationResult` dataclass: `valid: bool`, `reason: str`
  - `validate(response: str, min_len: int) → ValidationResult`
  - Checks: not empty, meets min length, no disrespectful language, not an API error string
- [ ] `src/cost.py` — `CostTracker`
  - `record_call(agent_name, input_tokens, output_tokens)`
  - `get_run_summary() → dict`
  - `append_to_cost_md(path, run_summary)` — appends markdown table row to `docs/cost.md`

---

## Phase 3 — Agent & Skill Definitions

**Goal:** All Claude Code agents and skills defined; each agent has the correct tool set and skill set; invocation chain works end-to-end.

### Agent-Skill Tree

```
orchestrate (agent)
├── validate_topic (skill)
├── validate_stance (skill)
├── validate_json (skill)
└── spawns →
    ├── debate (agent)
    │   └── web_search (skill)
    └── judge (agent)
        ├── judgment (skill)
        ├── validate_json (skill)
        └── web_search (skill)

judgment (skill)             ← also user-invocable directly via /judgment
└── invokes →
    └── judge (agent)
        ├── judgment (skill)
        ├── validate_json (skill)
        └── web_search (skill)
```

### Claude Code Agents (`.claude/agents/`)

- [ ] `.claude/agents/orchestrate/AGENT.md`
  - **Tools:** `Bash`, `Agent`, `Read`, `Write`
  - **Skills:** `validate_topic`, `validate_stance`, `validate_json`
  - **Parameters:** `$TOPIC`, `$TURNS`, `$MODEL_A`, `$MODEL_B`, `$MODEL_JUDGE`, `$NAME_A`, `$NAME_B`, `$MAX_RETRIES`, `$MIN_RESPONSE_LEN`, `$OUTDIR`, `$FACTCHECK_ENABLED`, `$LOG_LEVEL`, `$RESUME`
  - **Behavior:**
    - Call `python -m src.config` via Bash to load and save resolved config
    - Invoke `validate_topic` skill — reject with explanation if invalid
    - If `$RESUME=true`: call `python -m src.state load` via Bash to reconstruct history and determine start turn
    - Loop turns: spawn `debate` agent (inject `$HISTORY`, `$POSITION`, `$TURN_NUMBER`, `$TURNS_REMAINING`), collect JSONL response
    - After each turn: invoke `validate_json` skill, invoke `validate_stance` skill; on failure explain violation and retry up to `$MAX_RETRIES`; on max retries exceeded skip turn and log
    - Call `python -m src.state append` via Bash to persist each completed turn
    - After final turn: spawn `judge` agent, collect JSON verdict, call `python -m src.output write_result` via Bash
    - Call `python -m src.cost append` via Bash to update `docs/cost.md`

- [ ] `.claude/agents/debate/AGENT.md`
  - **Tools:** `WebSearch`
  - **Skills:** `web_search`
  - **Parameters:** `$AGENT_NAME`, `$POSITION`, `$OPPONENT_NAME`, `$TURN_NUMBER`, `$TURNS_REMAINING`, `$HISTORY`, `$MIN_RESPONSE_LEN`
  - **Behavioral rules:**
    - Always argue `$POSITION` — never concede, agree with, or validate the opponent
    - Use `web_search` skill to find supporting references, statistics, and citations
    - Build explicitly on prior turns from `$HISTORY`
    - Inform argumentation strategy using `$TURNS_REMAINING`
    - Minimum response length: `$MIN_RESPONSE_LEN` characters
    - All arguments in English regardless of topic language
  - **Output format:** single JSONL line
    ```json
    {"agent": "$AGENT_NAME", "turn": $TURN_NUMBER, "argument": "...", "references": ["..."]}
    ```

- [ ] `.claude/agents/judge/AGENT.md`
  - **Tools:** `WebSearch`
  - **Skills:** `judgment`, `validate_json`, `web_search`
  - **Parameters:** `$HISTORY`, `$AGENT_A_NAME`, `$AGENT_B_NAME`, `$FACTCHECK_ENABLED`
  - **Behavioral rules:**
    - Use `judgment` skill to perform scoring and declare winner
    - Use `web_search` skill to verify factual claims when `$FACTCHECK_ENABLED=true`
    - Use `validate_json` skill to verify own output before returning
    - Score each agent on Logic, Evidence, Clarity, Persuasiveness (0–10 per criterion)
    - No ties — if totals are equal, apply tiebreaker criterion and state it explicitly
    - If `$FACTCHECK_ENABLED=false`: set `factcheck_flags` to `[]`
  - **Output format:** single JSON object
    ```json
    {
      "winner": "$AGENT_NAME",
      "scores": {
        "$AGENT_A_NAME": {"logic": 0, "evidence": 0, "clarity": 0, "persuasiveness": 0, "total": 0},
        "$AGENT_B_NAME": {"logic": 0, "evidence": 0, "clarity": 0, "persuasiveness": 0, "total": 0}
      },
      "tiebreaker": null,
      "explanation": "...",
      "factcheck_flags": []
    }
    ```

### Claude Code Skills (`.claude/skills/`)

- [ ] `.claude/skills/validate_json/SKILL.md`
  - **Used by:** `orchestrate` agent (after each debate turn), `judge` agent (self-check before returning)
  - **How:** runs `python -c "import json, sys; json.loads(sys.stdin.read())"` via Bash
  - **Input:** `{"text": "...raw response string..."}`
  - **Output:** `{"valid": true}` or `{"valid": false, "error": "..."}`

- [ ] `.claude/skills/validate_topic/SKILL.md`
  - **Used by:** `orchestrate` agent (once, before debate starts)
  - **How:** inline LLM call
  - **Input:** `{"topic": "..."}`
  - **Output:** `{"valid": true, "position_a": "...", "position_b": "..."}` or `{"valid": false, "reason": "..."}`

- [ ] `.claude/skills/validate_stance/SKILL.md`
  - **Used by:** `orchestrate` agent (after each debate turn)
  - **How:** inline LLM call
  - **Input:** `{"text": "...", "claim": "..."}`
  - **Output:** `{"supports_claim": true, "confidence": "high|medium|low", "reason": "..."}`

- [ ] `.claude/skills/judgment/SKILL.md`
  - **Used by:** `judge` agent; user directly via `/judgment`
  - **How:** reads JSONL conversation file, validates debate is complete, invokes `judge` agent, saves verdict to timestamped result file
  - **Input:** `{"conversation_path": "...", "agent_a_name": "...", "agent_b_name": "...", "factcheck_enabled": true}`
  - **Output:** judge JSON verdict (same format as judge agent output)

- [ ] `.claude/skills/web_search/SKILL.md`
  - **Used by:** `debate` agent (find supporting evidence), `judge` agent (verify factual claims)
  - **How:** uses `WebSearch` tool
  - **Input:** `{"query": "..."}`
  - **Output:** `{"results": [{"title": "...", "url": "...", "snippet": "..."}]}`

### Python Agent Classes

- [ ] `src/agents/base.py` — `BaseAgent` (ABC)
  - `__init__(name, model, config, state, cost_tracker)`
  - `invoke_with_retry(prompt, context) → str` — calls `_invoke()`, validates, retries up to `max_retries`; on each failure passes violation explanation back into retry prompt
  - `_invoke(prompt) → str` — abstract; implemented by subclasses
  - `_build_retry_prompt(original_prompt, violation_reason) → str`
- [ ] `src/agents/debate.py` — `DebateAgent(BaseAgent)`
  - `_build_prompt(history, turn_number, turns_remaining) → str`
  - `_format_history(turns: list[dict]) → str` — formats JSONL turns as readable text for prompt injection
  - `_invoke(prompt) → str` — spawns `debate` agent, parses JSONL response
- [ ] `src/agents/judge.py` — `JudgeAgent(BaseAgent)`
  - `_build_scoring_prompt(history, factcheck_enabled) → str`
  - `_parse_verdict(response: str) → dict` — extracts structured scores and winner
  - `_invoke(prompt) → str` — spawns `judge` agent via `judgment` skill

---

## Phase 4 — Orchestrator & Debate Flow

**Goal:** Full debate runs end-to-end; resume works; topic validation rejects bad topics.

- [ ] `orchestrator.py` — `DebateOrchestrator`
  - `__init__(config, output_manager, state, cost_tracker)`
  - `validate_topic(topic) → tuple[str, str]` — calls Claude to check debatability; returns (position_a, position_b) or raises `InvalidTopicError`
  - `initialize_agents(position_a, position_b)` — constructs `DebateAgent` A, B and `JudgeAgent` with assigned positions/names
  - `run_turn(agent, turn_number, history) → str` — single turn: start watchdog → invoke agent → validate → record to state; returns accepted response
  - `run_debate()` — full lifecycle:
    1. Validate topic
    2. Create output folder, save config
    3. Determine start turn (0 for new, `state.last_turn_number()` for resume)
    4. Loop turns: alternate A/B, call `run_turn()`, append to state
    5. Invoke judge, write result
    6. Append cost summary
  - `resume_debate()` — loads state from JSONL, validates debate is incomplete, calls `run_debate()` from correct turn
- [ ] `.claude/agents/orchestrate/AGENT.md` — defined in Phase 3; wired up here to full Python layer
- [ ] `InvalidTopicError` — raised when topic cannot be split into two clear opposing sides

---

## Phase 5 — Output & Cost Finalization

**Goal:** All output files are written correctly; cost.md is updated; result files never overwrite.

- [ ] Complete `OutputManager.write_config(config)` — saves `DebateConfig` as JSON
- [ ] `OutputManager.write_result(verdict: dict)` — writes to uniquely timestamped result file
- [ ] Result file format: YAML or JSON with fields: `timestamp`, `winner`, `scores_a`, `scores_b`, `criteria_breakdown`, `factcheck_flags` (if enabled), `explanation`
- [ ] `CostTracker.append_to_cost_md()` — markdown table: `| timestamp | run_id | agent | input_tokens | output_tokens | est_cost_usd |`
- [ ] `docs/cost.md` — initialize with header row
- [ ] Ensure log file is flushed/closed cleanly on debate end or crash (via `atexit` or context manager)

---

## Phase 6 — Tests

**Goal:** ≥85% coverage; all edge cases covered for validation, retry, resume, and watchdog.

- [ ] `tests/unit/test_config.py` — CLI override precedence, missing required fields, type coercion
- [ ] `tests/unit/test_state.py` — append/load roundtrip, `is_complete()`, `needs_resume()`
- [ ] `tests/unit/test_validator.py` — empty response, too short, disrespectful language, valid response
- [ ] `tests/unit/test_watchdog.py` — fires on timeout, cancel prevents fire, context manager cleanup
- [ ] `tests/unit/test_output.py` — folder creation, result file uniqueness, path properties
- [ ] `tests/unit/test_cost.py` — accumulation, summary format, cost.md append idempotency
- [ ] `tests/unit/test_base_agent.py` — retry loop: succeeds on 2nd attempt, skips after max retries
- [ ] `tests/unit/test_debate_agent.py` — prompt construction, history formatting, position enforcement
- [ ] `tests/unit/test_judge_agent.py` — verdict parsing, no-tie enforcement, factcheck field presence
- [ ] `tests/unit/test_orchestrator.py` — topic validation accept/reject, turn sequencing A→B→A, resume start turn
- [ ] `tests/integration/test_full_debate.py` — 4-turn debate (mocked Agent calls); verifies JSONL output, result file written
- [ ] `tests/integration/test_resume.py` — write 2 turns to JSONL, resume, verify turns 3–4 added without re-running 1–2
- [ ] `tests/integration/test_judge_standalone.py` — run judge against a completed JSONL; verify verdict structure

---

## Phase 7 — Polish & Documentation

**Goal:** Zero Ruff violations; all docstrings present; README usable by a new developer.

- [ ] Run `ruff check src/ orchestrator.py main.py` — fix all violations
- [ ] Run `ruff format` — apply consistent formatting
- [ ] Audit all classes and methods for missing or incomplete docstrings
- [ ] `README.md` — setup instructions, `.env` config, usage examples (`/orchestrate`, `--resume`, standalone judge)
- [ ] Final `docs/TODO.md` update — mark all phases complete with commit hashes

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Agent definitions | `.claude/agents/` | Native Claude Code subagent pattern; isolated context per agent |
| Skills | `.claude/skills/` | Reusable LLM + tool capabilities; invokable by agents and users |
| Agent invocation | Orchestrator spawns debate/judge agents | Agents never call each other directly; orchestrator owns sequencing |
| Debate output | JSONL line per turn | Consistent with state file format; machine-parseable |
| Judge output | Single JSON object | Structured scores; easy to parse and save as result file |
| Data passing | History injected into prompt string | No temp file I/O; simpler agent interface |
| Factcheck | Single prompt, `$FACTCHECK_ENABLED` injected | One skill definition; behavior controlled by parameter |
| State format | JSONL (one turn per line) | Atomic appends; safe for interruption; resume-friendly |
| Config format | Dataclass + argparse + optional YAML file | Type-safe; CLI-first; file for complex/reusable configs |
| Watchdog impl | `threading.Timer` | Simple; works with synchronous Agent calls; no asyncio required |
| Result files | Timestamped filenames | Append-safe; multiple judge runs preserved |
| Language enforcement | Validation + orchestrator prompt | All debates in English per PRD |
