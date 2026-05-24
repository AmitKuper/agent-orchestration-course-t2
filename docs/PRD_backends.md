# PRD: Backend Abstraction Layer

## Overview
The backend layer decouples agent invocation from the transport mechanism, allowing the platform to run agents via the Anthropic SDK, Claude Code CLI, or Ollama without changing any agent or orchestration logic.

## Goals
- Support 4 distinct invocation backends selectable at runtime
- Zero code changes required when switching backends
- Consistent error handling and token usage recording across all backends

## Acceptance Criteria
- [ ] `make_backend(type)` returns a correctly typed instance for all 4 backend types
- [ ] All backends implement the `Backend.invoke()` interface
- [ ] `ApiBackend` records actual input/output token counts
- [ ] `CliBackend` passes `--model <model>` to the `claude` CLI
- [ ] `OllamaCliBackend` routes calls through `ollama run <model>`
- [ ] `OllamaBackend` posts to Ollama's `/v1/chat/completions` endpoint
- [ ] Unknown backend type raises `ValueError` with clear message
- [ ] `update_agent_file_model()` rewrites frontmatter model field safely

## Components
| Component | File | Responsibility |
|-----------|------|---------------|
| `Backend` | `src/backends.py` | Abstract interface |
| `ApiBackend` | `src/backends.py` | Anthropic SDK calls |
| `CliBackend` | `src/backends.py` | `claude --model … --print` subprocess |
| `OllamaCliBackend` | `src/backends.py` | `ollama run <model>` subprocess |
| `OllamaBackend` | `src/backends.py` | Ollama HTTP API (OpenAI-compatible) |

## Configuration
- Backend selected via `--backend {api,cli,ollama-cli,ollama}`
- Rate limits per backend in `config/rate_limits.json`
- Ollama base URL from `OLLAMA_BASE_URL` env var
