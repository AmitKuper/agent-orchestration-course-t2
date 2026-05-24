# PRD: Agent System

## Overview
Three specialized agent roles implement the debate: two opposing debaters and a judge scorer. All share common retry and validation infrastructure via `BaseAgent`.

## Goals
- Debaters always defend their assigned position without concession
- Judge produces deterministic, structured verdicts with no ties
- All agents self-correct on validation failures via retry with feedback

## Acceptance Criteria
- [ ] `DebateAgent` outputs valid JSONL on every accepted turn
- [ ] `JudgeAgent` scores Logic, Evidence, Clarity, Persuasiveness (0–10 each)
- [ ] `BaseAgent.invoke_with_retry` retries up to `max_retries` times
- [ ] Each retry includes the specific violation reason in the prompt
- [ ] Agent definition files loaded from `.claude/agents/*.md` at startup
- [ ] Variable substitution (`$AGENT_NAME`, `$POSITION`, etc.) applied correctly
- [ ] Empty/too-short/disrespectful responses rejected by validator

## Components
| Component | File | Responsibility |
|-----------|------|---------------|
| `BaseAgent` | `src/agents/base.py` | Retry loop, validation, backend invocation |
| `DebateAgent` | `src/agents/debate.py` | Debate turn prompt construction |
| `JudgeAgent` | `src/agents/judge.py` | Scoring prompt and verdict parsing |
| `load_agent_def` | `src/agents/base.py` | Loads `.claude/agents/*.md` as system prompts |

## Scoring Rubric (Judge)
| Dimension | Weight |
|-----------|--------|
| Logic & Reasoning | 25% |
| Evidence & Examples | 25% |
| Clarity & Structure | 25% |
| Persuasiveness | 25% |
