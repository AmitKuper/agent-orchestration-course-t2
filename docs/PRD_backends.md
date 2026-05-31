# PRD: Backend Abstraction Layer

## Overview
The backend layer decouples agent invocation from the transport mechanism, allowing the platform to run agents via the Anthropic SDK, Claude Code CLI, or Ollama without changing any agent or orchestration logic.

## Goals
- Support 7 invocation backends selectable at runtime
- Zero code changes required when switching backends
- Consistent error handling and token usage recording across all backends
- Clean ANSI/VT100 output from CLI-based backends (e.g. Qwen3 thinking mode)
- All external calls routed through `APIGatekeeper` for rate-limiting and logging

## Acceptance Criteria
- [x] `make_backend(type)` returns a correctly typed instance for all backend types
- [x] All backends implement the `Backend.invoke()` interface
- [x] `ApiBackend` records actual input/output token counts
- [x] `CliBackend` passes `--model <model>` to the `claude` CLI
- [x] `OllamaCliBackend` routes calls through `ollama run <model>`
- [x] `OllamaBackend` posts to Ollama's `/v1/chat/completions` endpoint
- [x] Unknown backend type raises `ValueError` with clear message
- [x] `update_agent_file_model()` rewrites frontmatter model field safely
- [x] ANSI/VT100 escape sequences and thinking preambles stripped from CLI output

## Components
| Component | File | Responsibility |
|-----------|------|---------------|
| `Backend` | `src/backends/_base.py` | Abstract interface |
| `OrchestratorBackend` | `src/backends/_orchestrator_base.py` | Base for single-call orchestrating backends |
| `ApiBackend` | `src/backends/_api.py` | Anthropic SDK calls via `APIGatekeeper` |
| `CliBackend` | `src/backends/_cli.py` | `claude --model … --print` subprocess per turn |
| `OllamaCliBackend` | `src/backends/_cli.py` | `ollama run <model>` subprocess per turn |
| `OllamaBackend` | `src/backends/_ollama.py` | Ollama HTTP API (OpenAI-compatible) via `APIGatekeeper` |
| `OllamaOrchestratorBackend` | `src/backends/_ollama_orchestrator.py` | Single Ollama call; self-orchestrates full debate |
| `PersistentCliBackend` | `src/backends/_persistent_cli.py` | Keeps `claude` subprocess alive per agent session |
| `APIGatekeeper` | `src/shared/gatekeeper.py` | Rate-limit / concurrency guard wrapping all external calls |
| `make_backend` | `src/backends/_factory.py` | Factory: type string → backend instance |
| `extract_response` / `render_ansi` | `src/backends/_ansi.py` | VT100 terminal emulator; strips ANSI codes and thinking preambles |

## Backend Identifiers
| Identifier | Backend class | Description |
|-----------|--------------|-------------|
| `claude-api` | `ApiBackend` | Anthropic SDK (default) |
| `claude-cli-agents` | `CliBackend` | `claude --print` per turn |
| `claude-cli-session` | `PersistentCliBackend` | Persistent `claude` subprocess per agent |
| `ollama-api` | `OllamaBackend` | Ollama HTTP API |
| `ollama-cli-agents` | `OllamaCliBackend` | `ollama run` per turn |
| `ollama-cli` | `OllamaOrchestratorBackend` | Single-shot Ollama orchestrator |
| `ollama-orchestrator` | `OllamaOrchestratorBackend` | Alias for `ollama-cli` |

Legacy aliases: `api`, `cli`, `cli-session`, `ollama`.

## Configuration
- Backend selected via `--backend <identifier>`
- Ollama base URL from `OLLAMA_BASE_URL` env var
- `CLAUDE_SKIP_PERMISSIONS=true` (default) passes `--dangerously-skip-permissions` to CLI backends

---

## How API and CLI Backends Differ

The two Claude backends look similar from the outside — both take a prompt and return a
response — but they use `.claude/agents/*.md` in fundamentally different ways.

### API backend (`ApiBackend`)

```
Python code
  │
  ├── load_agent_def(".claude/agents/debate-agent.md")  → reads file → system_prompt string
  │
  └── anthropic.Anthropic().messages.create(
          model     = "claude-sonnet-4-6",
          system    = system_prompt,          ← agent def injected explicitly
          messages  = [{"role": "user",
                        "content": prompt}],  ← full prompt built by our code
          max_tokens = 2048,
      )
```

- Our Python code reads the `.claude/agents/*.md` file and forwards its content as the
  `system` parameter to the Anthropic API.
- The API has no knowledge of the file — it only sees the string.
- Full control over model, system prompt, max_tokens, and temperature.
- Actual input/output token counts are returned and recorded in `docs/cost.md`.

### CLI backend (`CliBackend`)

```
Python code
  │
  ├── update_agent_file_model(".claude/agents/debate-agent.md", model)
  │     └── rewrites the model: field in YAML frontmatter
  │
  └── subprocess.run(
          ["claude", "--model", model, "--print", "--dangerously-skip-permissions"],
          input = prompt,    ← piped to stdin
      )
          │
          └── claude process starts
                └── reads .claude/ on its own:
                      - .claude/agents/debate-agent.md  (system prompt + model)
                      - .claude/CLAUDE.md               (project-level instructions)
                      - .claude/settings.json           (permissions)
```

- Our Python code does **not** pass the system prompt — `system=` is ignored by `CliBackend`.
- Instead, Python writes the correct model into the `.md` frontmatter before invoking, so
  the `claude` subprocess picks it up from its own `.claude/` context.
- The agent definition, permissions, and project instructions are all handled by the claude
  process itself — our code only controls what goes into stdin (the prompt).
- Token counts are unavailable; the CLI does not expose them.

### Summary

| Dimension | `ApiBackend` | `CliBackend` |
|-----------|-------------|-------------|
| Who reads `.claude/agents/*.md` | Our Python code (then passes as `system=`) | The `claude` subprocess itself |
| System prompt | Passed explicitly as API parameter | Delegated to claude's own context |
| Model selection | Passed as API parameter | Written into `.md` frontmatter before invoke |
| Token counts | Available (recorded in cost.md) | Not available (recorded as 0) |
| Auth | `ANTHROPIC_API_KEY` env var | Claude Code Pro subscription (OAuth) |
| Use case | Production, cost tracking | Development with existing Pro subscription |
