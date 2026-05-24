# PRD: Agent System

## Overview
Three specialized agent roles implement the debate: two opposing debaters and a judge scorer. All share common retry and validation infrastructure via `BaseAgent`.

## Goals
- Debaters always defend their assigned position without concession
- Judge produces deterministic, structured verdicts with no ties
- All agents self-correct on validation failures via retry with feedback
- Retry prompts are tailored to the failure category (format vs. content)

## Acceptance Criteria
- [x] `DebateAgent` outputs valid JSONL on every accepted turn
- [x] `JudgeAgent` scores Logic, Evidence, Clarity, Persuasiveness (0–10 each)
- [x] `BaseAgent.invoke_with_retry` retries up to `max_retries` times
- [x] Format failures (bad JSON) receive a focused fix-the-format retry prompt without history
- [x] Content failures (too short, empty) receive a retry prompt that re-attaches full history context
- [x] Each retry includes the specific violation reason in the prompt
- [x] Agent definition files loaded from `.claude/agents/*.md` at startup
- [x] Variable substitution (`$AGENT_NAME`, `$POSITION`, etc.) applied correctly
- [x] Empty/too-short/disrespectful responses rejected by validator
- [x] `parse_verdict` enforces full per-category score schema; recomputes totals; normalises key case

## Components
| Component | File | Responsibility |
|-----------|------|---------------|
| `BaseAgent` | `src/agents/base.py` | Retry loop, validation, backend invocation |
| `DebateAgent` | `src/agents/debate.py` | Debate turn prompt construction |
| `JudgeAgent` | `src/agents/judge.py` | Scoring prompt, verdict parsing and schema enforcement |
| `load_agent_def` | `src/agents/loader.py` | Loads `.claude/agents/*.md` as system prompts |

## Scoring Rubric (Judge)
| Dimension | Weight |
|-----------|--------|
| Logic & Reasoning | 25% |
| Evidence & Examples | 25% |
| Clarity & Structure | 25% |
| Persuasiveness | 25% |

## Judge Verdict Schema
```json
{
  "winner": "<agent name>",
  "scores": {
    "<agent A name>": { "logic": 0-10, "evidence": 0-10, "clarity": 0-10, "persuasiveness": 0-10, "total": 0-40 },
    "<agent B name>": { "logic": 0-10, "evidence": 0-10, "clarity": 0-10, "persuasiveness": 0-10, "total": 0-40 }
  },
  "tiebreaker": "<string or null>",
  "explanation": "<non-empty string>",
  "factcheck_flags": ["<claim>", ...]
}
```
- `total` is always recomputed from the four criteria — any value provided by the model is overwritten
- Key capitalisation is normalised (`"Logic"` → `"logic"`)
- `tiebreaker` and `factcheck_flags` default to `null` and `[]` if absent
