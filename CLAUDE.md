# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Debate Platform** — a multi-agent pipeline where two Claude agents argue opposing sides of a topic, managed by an orchestrator agent, and scored by a judge agent. The primary learning goal is hands-on mastery of Claude Code agent orchestration: skills, context management, state persistence, and inter-agent communication. See `docs/PRD.md` for full requirements.

## Agent Architecture

Four distinct agent roles, each implemented as a separate Claude Code skill:

- **Orchestrator** — controls the full debate lifecycle: topic injection, turn sequencing, context assembly, validation, retry logic, and output writing. Never debates; only coordinates.
- **Debater agent A / B** — assigned opposing positions at initialization; must always defend their side, never concede. Receive full conversation history on every turn.
- **Judge** — invoked by the orchestrator after all turns complete. Scores Logic, Evidence, Clarity, and Persuasiveness; optionally checks factual accuracy. No ties allowed.

Agents communicate strictly through the orchestrator — debaters never call each other directly.

## Debate Flow

1. Orchestrator validates topic (must split into two clear opposing sides; rejects otherwise)
2. Orchestrator extracts opposing positions and assigns one to each agent
3. Orchestrator poses the topic as a question (not counted as an agent turn)
4. Agents alternate turns starting with Agent A; default 20 turns total (10 per agent)
5. Each agent is told their remaining turn count on every turn
6. After all turns, orchestrator invokes the Judge
7. Outputs written to a dedicated folder per run

## State & History

History is passed via **prompt injection** — on every turn, the orchestrator assembles the full conversation history from `ConversationState` and includes it in the prompt sent to the agent (`build_prompt()` in `src/agents/debate.py`). This applies to all backends uniformly.

The JSONL conversation file (`conversation.jsonl`) is the persistent source of truth: `ConversationState` reads from it to support resume. It is also used for judge input, cost tracking, and output reporting.

## Validation & Retry

Every agent response is validated before being accepted. Invalid if: wrong format, disrespectful language, API error, empty/too short, or clearly off-topic. On failure: orchestrator explains the violation and retries (configurable max). If max retries exceeded, turn is skipped and logged. Judge timeout on all retries = conversation failure; state is preserved for resume.

## Watchdog / Timeout

Each agent has a dedicated watchdog with a configurable timeout. A timeout counts as an invalid response and triggers retry logic. The overall debate also has a watchdog; if it fires, the debate terminates gracefully and state is preserved.

## Output Structure

Each run writes to a dedicated output folder (default path configurable via `--outdir`):

| File | Contents |
|------|----------|
| config | Resolved configuration for this run |
| conversation (JSONL) | One entry per turn with token usage and metadata |
| log | All operations, retries, errors |
| result | Judge verdict, scores, fact-check flags; each judge run appends a new file (never overwrites) |

Judge can only run on a **completed** debate (all turns finished).

## Configuration

All parameters configurable via CLI flags or config file; CLI overrides config. Configurable: topic, number of turns, model per agent, agent names, max retries, minimum response length, output directory, factual correctness check, log level. Config is saved to the output folder at run start.

## Code Rules (from `docs/rules.md`)

- **File size limit**: 150 lines max per file. Extract helpers, split by responsibility, constants to `constants.py`.
- **Docstrings**: Every method, class, and function requires detailed docstrings.
- **No code duplication**: single responsibility, OOP with inheritance/mixins.
- **Linting**: Zero Ruff violations.
- **Test coverage**: ≥ 85%; unit tests per class/method; tests in `unit/` and `integration/` subfolders.
- **Secrets**: API keys via environment variables only; use `.env.example` as template.
- **Token cost tracking**: Record input/output tokens for every agent call in `docs/cost.md`.

## Commit Conventions

- `Feature: <name>` — new features
- `BugFix: <description>` — bug fixes
- `Refactor: <scope>` — refactoring
- `Docs: <change>` — documentation

`docs/TODO.md` must be updated in the same commit as the work it describes. Mark completed items `[x]`, in-progress items `🚧 In Progress`, and completed phases `✅ Complete` with the commit hash.

## Logging

Logs written simultaneously to console and output log file. Log level configurable:
- `DEBUG`: full prompts sent to agents, orchestration decisions
- `INFO`: turn progress, agent responses, retry attempts, debate start/end
- `WARNING`: invalid responses, skipped turns, max retries reached
- `ERROR`: API failures, unrecoverable errors
