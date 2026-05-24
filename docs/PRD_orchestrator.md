# PRD: Debate Orchestrator

## Overview
The orchestrator manages the full debate lifecycle without ever participating in the debate. It sequences turns, manages state, invokes agents, and coordinates the judge.

## Goals
- Complete isolation between orchestration logic and debate content
- Interrupt-safe state persistence (resume at any turn)
- Configurable watchdog timeouts per agent

## Acceptance Criteria
- [x] `DebateOrchestrator.run_debate()` completes full lifecycle end-to-end
- [x] `resume_debate()` continues correctly from the last persisted turn
- [x] Watchdog fires and is logged if agent exceeds `DEBATER_TIMEOUT`
- [x] Each agent response validated before being appended to state
- [x] Topic validation raises `InvalidTopicError` for non-debatable topics
- [x] Cost tracker updated after every agent call
- [x] Config written to `config.json` at debate start
- [x] Turn skips logged at ERROR level; retries logged at WARNING level

## Lifecycle Sequence
```
validate_topic()
    → initialize_agents()
        → _run_turns(1..N)
            → run_turn() per agent
                → agent.invoke_with_retry()
                    → backend.invoke()
        → _run_judge()
    → cost_tracker.append_to_cost_md()
```

## State Machine
| State | Trigger | Next State |
|-------|---------|------------|
| INIT | run_debate() called | VALIDATING |
| VALIDATING | topic valid | RUNNING |
| RUNNING | all turns done | JUDGING |
| JUDGING | verdict written | COMPLETE |
| COMPLETE | — | — |
| INTERRUPTED | timeout / error | RESUMABLE |
