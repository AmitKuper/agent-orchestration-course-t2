# PRD: Backend Abstraction Layer

## Overview
The backend layer decouples agent invocation from the transport mechanism, allowing the platform to run agents via the Anthropic SDK, Claude Code CLI, or Ollama without changing any agent or orchestration logic.

## Goals
- Support 4 distinct invocation backends selectable at runtime
- Zero code changes required when switching backends
- Consistent error handling and token usage recording across all backends
- Clean ANSI/VT100 output from CLI-based backends (e.g. Qwen3 thinking mode)

## Acceptance Criteria
- [x] `make_backend(type)` returns a correctly typed instance for all 4 backend types
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
| `ApiBackend` | `src/backends/_api.py` | Anthropic SDK calls |
| `CliBackend` | `src/backends/_cli.py` | `claude --model … --print` subprocess |
| `OllamaCliBackend` | `src/backends/_cli.py` | `ollama run <model>` subprocess |
| `OllamaBackend` | `src/backends/_ollama.py` | Ollama HTTP API (OpenAI-compatible) |
| `make_backend` | `src/backends/_factory.py` | Factory: type string → backend instance |
| `extract_response` | `src/backends/_ansi.py` | VT100 terminal emulator; strips ANSI codes and thinking preambles |

## Configuration
- Backend selected via `--backend {api,cli,ollama-cli,ollama}`
- Ollama base URL from `OLLAMA_BASE_URL` env var
