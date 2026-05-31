# Architecture — AI Debate Platform

Diagrams use [Mermaid](https://mermaid.js.org/) and render natively on GitHub/GitLab.

---

## 1. C4 Level 1 — System Context

Who uses the system and what external systems it talks to.

```mermaid
C4Context
    title AI Debate Platform — System Context

    Person(user, "User", "Researcher or developer running debates via CLI or Python SDK")

    System(platform, "AI Debate Platform", "Orchestrates multi-agent structured debates: topic validation → alternating argument turns → judge verdict → file output")

    System_Ext(anthropic, "Anthropic API", "Claude models (claude-haiku, claude-sonnet, claude-opus) served over HTTPS")
    System_Ext(ollama, "Ollama Server", "Local LLM inference (llama3, mistral, etc.) on localhost:11434")
    System_Ext(claude_cli, "Claude Code CLI", "Subprocess-based multi-agent sessions driven by .claude/agents/*.md files")

    Rel(user, platform, "Runs debates", "CLI (main.py) / Python import")
    Rel(platform, anthropic, "Sends prompts, reads responses", "HTTPS REST")
    Rel(platform, ollama, "Sends prompts, reads responses", "HTTP localhost:11434")
    Rel(platform, claude_cli, "Spawns agent subprocesses", "subprocess / stdin-stdout")
```

---

## 2. C4 Level 2 — Container View

The major deployable units and their responsibilities.

```mermaid
C4Container
    title AI Debate Platform — Container View

    Person(user, "User")

    Container(main, "main.py", "Python CLI", "Entry point: parses CLI args, builds DebateConfig, calls DebateSDK.run()")
    Container(sdk, "DebateSDK", "Python class (src/sdk/debate_sdk.py)", "Single public entry point. Assembles infrastructure dependencies and delegates to DebateOrchestrator. Returns DebateResult.")
    Container(orch, "DebateOrchestrator", "Python class (orchestrator.py)", "Coordinates full lifecycle: topic validation → agent init → debate turns → judge → cost report")
    Container(agents, "Agents", "Python classes (src/agents/)", "DebateAgent A and B generate arguments. JudgeAgent evaluates and returns a verdict.")
    Container(backends, "Backends", "ABC + implementations (src/backends/)", "Transport layer. Backend for per-turn invoke(). OrchestratorBackend for full single-shot run_debate().")
    Container(validators, "Validators", "Python functions (src/)", "Guard layer: topic_validator, protocol_validator, stance_validator, verdict_validator, novelty check in validator.py")
    Container(state, "ConversationState", "JSONL file (src/state.py)", "Append-only turn log. Powers resume and novelty checks across turns.")
    Container(output, "OutputManager", "Python class (src/output.py)", "Writes config.json, conversation.jsonl, result.json, debate.log, result_<ts>.json")
    Container(config, "DebateConfig", "Python dataclass (src/config.py)", "Resolved config: YAML/JSON file merged with CLI overrides")
    Container(gatekeeper, "APIGatekeeper", "Python class (src/shared/gatekeeper.py)", "Rate-limit retry wrapper around API backends")
    ContainerDb(fs, "Output Folder", "Filesystem", "Per-run outputs/YYYY-MM-DD_HH-MM-SS/ folder")

    Rel(user, main, "Invokes", "CLI args / Python import")
    Rel(main, sdk, "Calls run(config)")
    Rel(sdk, orch, "Creates and delegates to")
    Rel(orch, agents, "Constructs and drives turn by turn")
    Rel(orch, validators, "Validates topic and agent responses")
    Rel(agents, backends, "Sends prompts via invoke()")
    Rel(agents, state, "Reads prior turns for history and novelty")
    Rel(agents, gatekeeper, "API calls throttled through")
    Rel(orch, state, "Appends turns / checks completion")
    Rel(orch, output, "Writes all artifacts")
    Rel(orch, config, "Reads all settings from")
    Rel(output, fs, "Persists to")
    Rel(state, fs, "Reads/writes conversation.jsonl")
```

---

## 3. UML Class Diagram — Backend Hierarchy

Two independent ABC contracts served by different concrete backends.

```mermaid
classDiagram
    class Backend {
        <<abstract>>
        +uses_memory bool = False
        +close() None
        +invoke(name, model, prompt, cost_tracker, max_tokens, temperature, system) str
    }

    class OrchestratorBackend {
        <<abstract>>
        +fallback_backend_type str = "claude-api"
        +run_debate(config, pos_a, pos_b) tuple~list, dict~
        +close() None
    }

    class ApiBackend {
        -_client Anthropic
        -_get_anthropic() Anthropic
        +invoke(...) str
    }

    class CliBackend {
        -_proc subprocess.Popen
        +invoke(...) str
        +close() None
    }

    class OllamaBackend {
        -_base_url str
        +invoke(...) str
    }

    class OllamaCliBackend {
        +invoke(...) str
    }

    class PersistentCliBackend {
        -_session subprocess.Popen
        +invoke(...) str
        +close() None
    }

    class OllamaOrchestratorBackend {
        +fallback_backend_type str = "ollama-cli-agents"
        +run_debate(...) tuple
    }

    Backend <|-- ApiBackend : extends
    Backend <|-- CliBackend : extends
    Backend <|-- OllamaBackend : extends
    Backend <|-- OllamaCliBackend : extends
    Backend <|-- PersistentCliBackend : extends
    OrchestratorBackend <|-- OllamaOrchestratorBackend : extends
```

**Key design rule:** `DebateOrchestrator` only ever calls `backend.invoke()` or `backend.run_debate()`. It never knows which concrete class it holds. Adding a new backend requires only implementing the matching ABC and registering it in `_factory.py`.

---

## 4. Sequence Diagram — Debate Turn Flow

What happens inside `DebateOrchestrator.run_turn()` for a single agent turn.

```mermaid
sequenceDiagram
    participant Orch as DebateOrchestrator
    participant WD as Watchdog
    participant Agent as DebateAgent
    participant Val as Validators
    participant GK as APIGatekeeper
    participant API as Backend

    Orch->>WD: start(timeout_seconds)
    Orch->>Agent: run_turn(turn_number)

    loop up to max_retries
        Agent->>Agent: build_prompt(history, position)
        Agent->>GK: request slot (rate limiting)
        GK->>API: invoke(prompt, model, system)
        API-->>GK: raw response text
        GK-->>Agent: response text

        Agent->>Val: validate_debate_turn(response)
        Note over Val: checks JSON schema, required fields, type correctness
        Agent->>Val: check_novelty(response, prior_turns)
        Note over Val: SequenceMatcher ratio < 0.75 threshold
        Agent->>Val: validate_stance(response)
        Note over Val: detects concession phrases

        alt all validators pass
            Agent-->>Orch: response JSON string
        else validation fails
            Agent->>Agent: increment retry_count
        end
    end

    Orch->>WD: cancel()
    Orch->>Orch: state.append_turn(parsed)
```

---

## 5. Deployment Diagram — Local vs Cloud

```mermaid
graph TB
    subgraph Dev["Developer Machine"]
        CLI["main.py / DebateSDK"]
        Proc["Python Process\n(orchestrator + agents)"]
        FS["File System\noutputs/ examples/ config/"]
        Ollama["Ollama Server\n:11434 (optional)"]
        ClaudeCLI["Claude Code CLI\n(optional)"]
    end

    subgraph Cloud["Cloud (external)"]
        Anthropic["Anthropic API\napi.anthropic.com"]
    end

    CLI --> Proc
    Proc --> FS
    Proc -->|"HTTP (ollama-api / ollama-cli-agents)"| Ollama
    Proc -->|"subprocess"| ClaudeCLI
    Proc -->|"HTTPS (claude-api)"| Anthropic
```

**Deployment modes:**
| Mode | Requires | Network |
|------|----------|---------|
| `claude-api` | `ANTHROPIC_API_KEY` env var | Cloud (Anthropic) |
| `ollama-api` | Ollama server running locally | Local only |
| `cli` / `claude-cli-agents` | Claude Code CLI installed | Cloud (via CLI auth) |
| `ollama-cli` / `ollama-cli-agents` | Ollama + Claude Code CLI | Local only |
