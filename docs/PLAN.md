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
                    ├─ debater agent          (turn 1, Agent A)
                    │    └─ web_search skill
                    ├─ validate_json skill    (after each turn)
                    ├─ validate_stance skill  (after each turn)
                    ├─ debater agent          (turn 2, Agent B)
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
    debate-agent.md       # Debater system prompt — argues assigned position
    debate-judge.md       # Judge system prompt — scores and declares winner
    debate-orchestrator.md# Orchestrator system prompt — lifecycle control
  skills/
    validate_json/SKILL.md
    validate_topic/SKILL.md
    validate_stance/SKILL.md
    judgment/SKILL.md
    web_search/SKILL.md

src/
  constants.py            # All defaults and magic values
  config.py               # DebateConfig dataclass + argparse CLI + file loader/saver
  logger.py               # Dual console+file logger (attaches to root debate logger)
  state.py                # JSONL read/write, turn tracking, resume detection
  validator.py            # ResponseValidator + ValidationResult (valid, reason, category)
  watchdog.py             # Threading-based per-agent timeout wrapper
  output.py               # Run folder creation, canonical file paths
  cost.py                 # Per-call token recording + docs/cost.md appender
  exceptions.py           # InvalidTopicError
  topic_validator.py      # validate_topic() via Claude API
  debate_helpers.py       # run_turn() helper extracted from orchestrator
  agents/
    __init__.py
    base.py               # BaseAgent ABC: invoke_with_retry(), format/content retry prompts
    debate.py             # DebateAgent: build_prompt(), _format_history(), _invoke()
    judge.py              # JudgeAgent: build_scoring_prompt(), parse_verdict(), _validate_verdict()
    loader.py             # load_agent_def(): loads .claude/agents/*.md as system prompts
  backends/
    __init__.py           # Public re-exports
    _base.py              # Backend ABC: invoke() interface
    _api.py               # ApiBackend — Anthropic SDK
    _cli.py               # CliBackend + OllamaCliBackend — subprocess invocation
    _ollama.py            # OllamaBackend — Ollama HTTP API
    _factory.py           # make_backend(type) factory
    _ansi.py              # VT100 terminal emulator; strips ANSI codes and thinking preambles
  sdk/
    __init__.py
    debate_sdk.py         # DebateSDK — high-level API facade
  shared/
    __init__.py
    gatekeeper.py         # APIGatekeeper — rate-limit / concurrency guard
    version.py            # Package version constant

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
    test_topic_validator.py
    test_backend_factory.py
    test_api_backend.py
    test_cli_backend.py
    test_ollama_backend.py
    test_ollama_cli_backend.py
    test_agent_file_model.py
    test_orchestrator_core.py
    test_orchestrator_judge.py
    test_debate_sdk.py
    test_gatekeeper.py
    test_version.py
  integration/
    test_full_debate.py
    test_resume.py
    test_resume_complete.py
    test_judge_standalone.py
    test_debate_config_file.py

examples/
  debate-config.example.json   # Canonical config template
  iran-nuclear/output-ollama/  # Full run output — diplomacy vs. military
  ai-jobs/output-ollama/       # Full run output — AI job displacement
  messi-ronaldo/output-ollama/ # Full run output — GOAT debate

docs/
  PRD.md
  PRD_agents.md
  PRD_backends.md
  PRD_orchestrator.md
  PLAN.md
  TODO.md
  rules.md
  cost.md                      # Token/cost log appended after every run
  analysis.md                  # Experimental findings across example debates
  hw1_lessons_learned.md       # Feedback from HW1 and conclusions for HW2

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
| **Dedicated judge vs orchestrator-as-judge** | Dedicated `JudgeAgent` | The orchestrator has operational context (retries, skips, validation failures) that could bias scoring. A separate judge receives only the clean accepted arguments — the same view a human reader has. It also allows re-running judgment independently with different parameters (model, factcheck on/off) without replaying orchestration logic. |
| **Retry prompt strategy** | Split by failure category (`format` vs `content`) | Format failures (bad JSON) need a tight "fix the serialisation" prompt without history noise. Content failures (too short, off-topic) need history re-attached so the agent can produce a substantive response. A single retry prompt served neither case well. |

---

## How to Extend

### Add a new backend

There are two backend contracts. Choose the right one before writing any code.

#### Option A — Per-turn Backend (subclass `Backend`)

Use this when the backend handles **one agent call at a time** — the orchestrator drives the turn loop and calls `invoke()` on every turn. This is the standard path for API backends, CLI wrappers, and HTTP transports.

1. **Create `src/backends/_mybackend.py`** — subclass `Backend` from `_base.py` and implement:
   ```python
   def invoke(
       self, name: str, model: str, prompt: str,
       cost_tracker: CostTracker, max_tokens: int,
       temperature: float | None = None, system: str | None = None,
   ) -> str: ...
   ```
2. **Set `uses_memory`** — class attribute on your backend (`bool`, default `False`).
   - `False` (recommended for all new backends): the orchestrator injects full conversation history into every prompt via `build_prompt()`.
   - `True` only if your backend maintains its own persistent memory and agents must never receive history in their prompt (currently unused — the original CliBackend design intent that was never completed).
3. **Register in `src/backends/_factory.py`**:
   - Add your type string to the `_CHOICES` tuple.
   - Add a branch in `make_backend()`: `if backend_type == "my-backend": return MyBackend(...)`.
4. **Export from `src/backends/__init__.py`** — add to both the `import` block and `__all__`.
5. **Add to `--backend` choices** in `build_cli_parser()` in `src/config.py`.
6. **If CLI-based** (subprocess per agent turn): add your backend name to the `if c.backend in (...)` guard in `orchestrator.py` `initialize_agents()` so `.claude/agents/*.md` model fields are updated before agent construction.
7. **Add tests** in `tests/unit/test_mybackend.py` — cover `invoke()`, token recording, error handling, and any constructor arguments.

#### Option B — Orchestrator Backend (subclass `OrchestratorBackend`)

Use this when the backend **generates the entire debate in a single call** — the model self-orchestrates all turns and the judge verdict internally. The Python orchestrator detects this via `isinstance` and delegates the full lifecycle to `run_debate()`.

1. **Create `src/backends/_myorchestrator.py`** — subclass `OrchestratorBackend` from `_orchestrator_base.py` and implement:
   ```python
   def run_debate(
       self, config: DebateConfig, position_a: str, position_b: str,
   ) -> tuple[list[dict], dict | None]: ...
   ```
   Returns `(turns, verdict)` where `turns` is a list of accepted turn dicts (same schema as `conversation.jsonl`) and `verdict` is the judge result dict or `None`.
2. **Set `fallback_backend_type: str`** — the per-turn backend to use for single calls that `OrchestratorBackend` cannot handle (e.g. topic validation). Must be from the same family as your backend so the environment requirements match:
   - Claude orchestrator → `"claude-api"`
   - Ollama orchestrator → `"ollama-cli-agents"`
   - The base class default is `"claude-api"` — override it explicitly to avoid surprises.
3. **Register in `src/backends/_factory.py`** — same as Option A steps 3–5.
4. **Export from `src/backends/__init__.py`** — same as Option A step 4.
5. **Add to `--backend` choices** in `build_cli_parser()` in `src/config.py`.
6. **Add tests** in `tests/unit/test_myorchestrator.py` — cover `run_debate()` output parsing, `fallback_backend_type` value, and the prompt builder if present.

### Add a new agent type

1. Create `src/agents/myagent.py` — subclass `BaseAgent` from `base.py`
2. Implement `_invoke(prompt) -> str` (use `self.backend.invoke(...)`)
3. Implement any prompt-building methods the agent needs
4. Add a system-prompt definition in `.claude/agents/myagent.md`
5. Add tests in `tests/unit/test_myagent.py`

### Add a new validation rule

1. Open `src/validator.py` — add a new `_check_*` method on `ResponseValidator`
2. Call it from `validate()` in the check chain (before `validate_json`)
3. Return `ValidationResult(False, "reason", category="content")` on failure
4. Add the new pattern/constant to `src/constants.py` if needed
5. Add a test case in `tests/unit/test_validator.py`

### Add a new example debate

1. Create `examples/<topic>/` directory
2. Run: `python main.py --config <your-config.json>`
3. Copy the run output folder to `examples/<topic>/output-<backend>/`
4. The config is already saved inside the output folder — no top-level config needed

---

## Future Development Options

### New Backends

**`ClaudeOrchestratorBackend`** (`src/backends/_claude_orchestrator.py`)
Single-call Claude backend — sends one prompt asking Claude to generate the complete debate as JSONL, then parses the output. Mirrors `OllamaOrchestratorBackend` exactly. Set `fallback_backend_type = "claude-api"`. Useful for rapid prototyping and cost estimation without per-turn API overhead.

**`OpenAIBackend`** (`src/backends/_openai.py`)
Per-turn backend using the OpenAI API (GPT-4o, o1, etc.). Implement `invoke()` via the `openai` Python SDK. Add `OPENAI_API_KEY` to `.env.example`. Token tracking already works — `record_call()` accepts any integer counts.

**`AsyncApiBackend`** (`src/backends/_async_api.py`)
`asyncio`-based variant of `ApiBackend`. Enables both debate agents to generate their turns concurrently (Agent A and Agent B share no state between turns, so turns within a single round are independent). Requires an async orchestrator loop and `asyncio.gather()` for paired turns. Halves wall-clock time on API backends.

**`GeminiBackend`** (`src/backends/_gemini.py`)
Per-turn backend using the Google Gemini API via `google-generativeai`. Same structure as `ApiBackend` — lazy client init, gatekeeper wrapping, token count from response metadata.

---

### Debate Formats

**Panel debate** — more than two agents arguing the same topic from different angles (e.g. economic, ethical, technical). Requires `DebateConfig` to support `n_agents` and a turn-order list. `_run_turns()` in `orchestrator.py` already uses a modulo pattern — extend to cycle through `n` agents.

**Oxford format** — structured rounds: opening statements → rebuttals → audience questions → closing statements. Requires turn-type metadata in `ConversationState` and format-aware prompt injection in `build_prompt()`.

**Human-in-the-loop** — one debater is a human typing at the terminal. Add a `HumanBackend` that reads from `stdin` instead of calling a model. No changes to `DebateAgent` or validation needed — the human's input goes through the same schema validation as model output.

---

### Judge Improvements

**Multi-judge consensus** — invoke 2–3 judge agents with different models and average (or vote on) the scores. `execute_judge()` in `debate_helpers.py` already returns a verdict dict — run it N times and merge. Reduces single-model bias.

**Real factcheck integration** — connect `factcheck_flags` to a web search call (the `web_search` skill already exists for Claude CLI agents). When `factcheck=true`, extract all `references` from the debate, verify each URL/claim, and populate `factcheck_flags` with failed checks.

**Streaming judge output** — show scoring criteria as they are produced rather than waiting for the full verdict JSON. Requires streaming support in `ApiBackend` and a partial-JSON parser in `JudgeAgent`.

---

### Persistence & State

**SQLite backend for `ConversationState`** — replace JSONL append with a SQLite table. Enables indexed queries (turns by agent, turns by score), multi-debate history, and leaderboards across runs without parsing files. The `ConversationState` interface (`append_turn`, `get_turns`, `load_from_file`) is already abstract enough to swap implementations.

**S3 / remote output** — `OutputManager` writes all files locally. Add a `RemoteOutputManager` subclass that mirrors writes to an S3 bucket or GCS bucket. Useful for running debates on headless servers and collecting results centrally.

**Debate replay** — given a `conversation.jsonl`, re-run validation on every turn and re-invoke the judge. Useful for re-scoring an existing debate with a different model or updated criteria without re-running all turns.

---

### Observability

**Prometheus metrics** — export per-turn latency, retry counts, token usage, and validation failure rates as Prometheus counters/histograms. Add a `MetricsMiddleware` that wraps `APIGatekeeper.execute()`.

**Live progress UI** — a `rich`-based terminal dashboard showing current turn, agent scores so far, retry count, and elapsed time. Replace the plain `logging` output in `_run_turns()` with a `rich.Live` context.

**Cost alerts** — `CostTracker` already estimates USD cost per call. Add a configurable `max_cost_usd` field to `DebateConfig`; raise `CostLimitExceededError` (new exception in `exceptions.py`) before any call that would exceed the budget.

---

### API & Integration

**REST API server** — wrap `DebateSDK` in a FastAPI app. Expose `POST /debates` (start), `GET /debates/{id}` (status/result), and `POST /debates/{id}/resume`. `ConversationState` and `OutputManager` already provide the persistence layer.

**Tournament mode** — run N debates on the same topic with randomised position assignment, aggregate scores across runs, and report win rates per backend/model. Add a `Tournament` class that calls `DebateSDK.run()` in a loop and writes a summary CSV.

**Webhook notifications** — call a configurable URL when a debate completes or fails. Add `webhook_url` to `DebateConfig` and a `notify()` call at the end of `DebateOrchestrator.run_debate()`.

---

## ISO/IEC 25010 Compliance Matrix

| Quality Characteristic | Evidence in this Project |
|------------------------|--------------------------|
| **Functional Suitability** | Full debate lifecycle: topic validation, 20-turn alternating debate, judge scoring with schema enforcement; verified by 160 tests covering all acceptance criteria |
| **Reliability** | Retry logic with `max_retries`-bounded attempts; watchdog timeouts per agent; interrupted debates resume from last persisted turn; atomic JSONL appends prevent partial-turn corruption |
| **Performance Efficiency** | Ollama backend for zero-cost local inference; parallel debate execution supported; per-call token tracking identifies costly agents; configurable `min_response_len` / `max_tokens` bound output size |
| **Usability** | CLI-first interface with `--config` file support; comprehensive README with install, usage, and Ollama guide; `examples/` with three complete run outputs showing real terminal behaviour and verdicts |
| **Security** | No secrets in code; `ANTHROPIC_API_KEY` via `.env` only; `.gitignore` excludes `.env` and outputs; `CLAUDE`/`ANTHROPIC` env vars stripped in `CliBackend` to prevent recursive invocation |
| **Maintainability** | All files ≤ 150 lines; single-responsibility classes; zero Ruff violations; 160 tests at 100% coverage; `ValidationResult.category` cleanly separates retry strategies without branching in agent code |
| **Portability** | Backend abstraction decouples agent logic from transport (API, CLI, Ollama); runs on Windows, macOS, Linux; `uv` lockfile ensures reproducible dependency resolution across OS |
