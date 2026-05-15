# PRD: AI Debate Platform

## Overview

A multi-agent debate platform where two AI agents argue opposing sides of a topic, moderated by an orchestrator agent, and judged by a dedicated judge agent. The primary learning objective is to deeply understand agent orchestration: skills, context management, state persistence, and inter-agent communication.

---

## Goals

- Build a fully functional debate pipeline using Claude agents
- Demonstrate mastery of: agent context passing, orchestrator control flow, state persistence, and retry/error handling
- Produce structured, human-readable output for every debate run
- Support resuming an interrupted debate from the exact step it stopped

---

## Agents

### Debate Agents (Agent A & Agent B)
- The two agents hold **opposite points of view** — Agent A and Agent B are always in direct disagreement
- The orchestrator extracts the two opposing sides from the topic and assigns one to each agent at initialization — e.g., topic "Messi vs. Ronaldo": Agent A argues *Messi is better*, Agent B argues *Ronaldo is better*
- Each agent must always defend their assigned position — they cannot agree with, concede to, or validate the other agent's point of view under any circumstance
- Only the judge determines who is right; agents never resolve the disagreement themselves
- Each agent is given a name and a consistent debater persona at initialization
- Each agent can be configured to use a different AI model
- Each agent receives the full conversation history on every turn so they can build on prior arguments

### Orchestrator Agent
- Manages the entire debate flow: topic injection, turn sequencing, context assembly, and output writing
- Passes each agent's response to the other as input for the next turn
- Validates every response before passing it on (see Validation section)
- Records all conversation turns in real time
- Maintains a clean, respectful conversation
- Invokes the Judge Agent at the end of the debate and writes the final result

### Judge Agent
- Invoked by the Orchestrator at the end of the debate
- Can also be run independently by the user, referencing a completed debate
- Receives the full conversation as context
- Scores each agent on: Logic, Evidence, Clarity, and Persuasiveness
- Optionally evaluates **factual correctness**: whether agents based their arguments on real, accurate information or fabricated/hallucinated facts — flags specific claims that appear invented or unverifiable
- Produces a total score per agent and declares a winner
- No ties allowed — if scores are equal, the judge must still pick one winner on a tiebreaker criterion
- Outputs a structured verdict, scores, and explanation

---

## Topic Validation

- Before starting a debate, the orchestrator must validate that the topic can be clearly split into two opposing sides
- If the topic is not debatable (e.g. has no clear opposing positions), the system rejects it with a clear explanation and exits without starting
- All debates must be conducted in **English**, regardless of the language the topic was written in

---

## Debate Structure

- The debate consists of **X** total argument turns, split evenly between the two agents (default: 20 turns, 10 per agent)
- Agent A always goes first
- The conversation is strictly synchronized — one agent responds at a time, in strict alternating order; an agent cannot respond out of turn or produce multiple responses in a row
- The orchestrator is the sole controller of turn sequencing and must enforce this order
- The orchestrator opens the debate by posing the topic as a question — this is not an agent turn
- On every turn, each agent is informed how many turns they have remaining so they can plan their argumentation strategy
- There are no closing statements

---

## Watchdog & Timeout

- Each agent (Agent A, Agent B, and the Judge) must have a dedicated watchdog
- The watchdog monitors the agent's response time and terminates the agent process if it exceeds a configurable timeout threshold
- A timeout is treated as an invalid response — the orchestrator applies the same retry behavior as any other invalid response
- If the agent times out on all retries, the turn is skipped and logged, and the debate continues
- If the **Judge** times out on all retries, it is treated as a conversation failure — the state is preserved and the debate can be resumed to re-run the judgment
- The overall conversation also has a watchdog — if the total debate duration exceeds a configurable limit, the debate is terminated gracefully and the current state is preserved for resume
- Timeout thresholds are independently configurable per agent type (debater vs. judge)

---

## Validation

Every agent response must be validated by the orchestrator before being accepted. A response is invalid if it:
- Is not in the required structured format
- Contains disrespectful language, profanity, or slurs
- Contains an API error or exception
- Is empty or too short
- Is clearly off-topic

**Retry behavior**:
- On invalid response: orchestrator explains the violation and requests a retry
- Maximum retries per turn is configurable
- If max retries exceeded: the turn is skipped and logged, debate continues

---

## Resume

- If a debate is interrupted for any reason — crash, error, or user cancellation (e.g. Ctrl+C) — it must be possible to resume it from the point it stopped
- The user triggers resume via CLI, referencing the previous debate run
- A turn only counts as complete if the agent fully finished their response. If an agent was mid-response when interrupted, that turn is redone from scratch on resume
- The conversation JSONL file is the source of truth for resume state — only fully completed turns are written to it
- On resume, agents must have their context fully reconstructed from the saved conversation so they continue as if uninterrupted
- A completed debate cannot be resumed

---

## Configuration

- All parameters must be configurable — either via CLI flags or a config file
- CLI flags override config file values when both are provided
- A copy of the resolved configuration is saved to the output folder at the start of each run
- Configurable parameters include: topic, number of turns, model per agent, agent names, max retries, minimum response length, output directory, factual correctness check, log level

---

## Output

Each debate run produces a dedicated output folder. The folder location has a default and can be overridden via `--outdir`. It contains:
- **Config** — the exact configuration used for this run
- **Topic** — the debate topic
- **Conversation** — the full conversation, one entry per turn, including token usage and metadata per turn
- **Log** — all operations, retries, and errors
- **Result** — the judge's verdict, scores per criterion, disputed claims (if fact-check enabled), summary, and explanation of the winner. Each judge run produces a separate result file — running the judge multiple times on the same debate does not overwrite previous results
- The judge can only be run on a **completed** debate (all turns finished). Running it on a partial debate is not allowed

---

## Logging

- Logs are written simultaneously to the console (real-time) and to the output log file
- Log level is configurable — controls what is shown on the console
- Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `DEBUG`: orchestration decisions, full prompts sent to agents
- `INFO`: turn progress, agent responses, retry attempts, debate start/end
- `WARNING`: invalid responses, skipped turns, max retries reached
- `ERROR`: API failures, unrecoverable errors

---

## Token / Cost Tracking

- Token usage (input and output) must be recorded for every agent call
- A cost summary must be appended to `docs/cost.md` after each run

---

## Educational Objective

The primary goal of this project is for the student to gain hands-on mastery of **Claude Code's agent system** — specifically:

### 1. `/skills` — Creating and Invoking Agents
- How to define a skill and what structure it requires
- How skills differ from plain prompts: scoping, reusability, invocation
- How to pass arguments into a skill and receive structured output back
- When to use a skill vs. a direct API call vs. a subagent
- **How to assign a specific skill to each agent** — giving the orchestrator, debaters, and judge distinct skill definitions with different behaviors, tools, and constraints

### 2. Context Manipulation
- How to construct and inject a system prompt that shapes agent behavior
- How to pass conversation history as context, and what to include vs. omit
- How context window limits affect multi-turn agents and how to manage them
- How the orchestrator assembles context differently for each agent type

### 3. `.claude/` Directory Structure
- What files live in `.claude/` and what each one controls
- How `CLAUDE.md` is used to give Claude persistent instructions about the project
- How to write a `CLAUDE.md` that guides Claude's behavior across all sessions
- How settings, hooks, and permissions affect Claude Code behavior

### 4. CLAUDE.md Best Practices
- What belongs in `CLAUDE.md` vs. `rules.md` vs. inline comments
- How to write instructions Claude will actually follow consistently
- How to encode project conventions, agent roles, and orchestration rules so they don't need to be re-explained each session

The implementation of the debate platform is the vehicle for learning these concepts — every architectural decision should be made with the goal of understanding these mechanisms more deeply.

---

## Out of Scope

- Web UI or frontend
- Multiple simultaneous debates
- Human participants in the debate
- Streaming responses
