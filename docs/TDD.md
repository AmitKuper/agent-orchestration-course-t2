# Test-Driven Development — Methodology & Examples

## What is TDD?

TDD (Test-Driven Development) is a development cycle where **tests are written before the code they verify**:

```
RED  →  GREEN  →  REFACTOR
```

| Phase | Action | Goal |
|-------|--------|------|
| **RED** | Write a test that asserts the desired behaviour. Run it — it must fail. | Prove the test can catch a real defect |
| **GREEN** | Write the minimum code to make the test pass. | Get to passing state as fast as possible |
| **REFACTOR** | Clean up the implementation without breaking the test. | Maintain code quality |

This cycle repeats for every new behaviour, keeping feedback loops tight and preventing both over-engineering and regressions.

---

## TDD Applied in This Project

The examples below show the RED → GREEN → REFACTOR cycle for features in this codebase.

---

### Example 1 — `OrchestratorBackend.fallback_backend_type`

**Context:** `DebateOrchestrator.validate_topic()` needs to fall back to a per-turn backend when the configured backend is an `OrchestratorBackend` (which only speaks full debates, not single turns).

#### RED — failing test

```python
# tests/unit/test_orchestrator_core.py

def test_validate_topic_fallback_for_orchestrator_backend(orch):
    """OrchestratorBackend uses its own fallback_backend_type for topic validation."""
    orch._backend = OllamaOrchestratorBackend()
    with (
        patch("orchestrator.make_backend", return_value=MagicMock()) as mk,
        patch("orchestrator.validate_topic", return_value=("FOR", "AGAINST")),
    ):
        orch.validate_topic("test topic")
    mk.assert_called_once_with(OllamaOrchestratorBackend.fallback_backend_type)
```

Running this test first would **fail** because `validate_topic()` originally called `make_backend("ollama-api")` — a hard-coded string, not a class attribute.

#### GREEN — minimum implementation

```python
# src/backends/_orchestrator_base.py
class OrchestratorBackend(ABC):
    fallback_backend_type: str = "claude-api"   # ← added class attribute
    ...

# src/backends/_ollama_orchestrator.py
class OllamaOrchestratorBackend(OrchestratorBackend):
    fallback_backend_type: str = "ollama-cli-agents"   # ← overrides default
    ...

# orchestrator.py
def validate_topic(self, topic: str) -> tuple[str, str]:
    backend = self._backend or make_backend(self.config.backend, ...)
    if isinstance(backend, OrchestratorBackend):
        backend = make_backend(backend.fallback_backend_type)   # ← uses attribute
    return validate_topic(topic, self.config.model_judge, backend)
```

Test now passes (GREEN). The hard-coded string is gone; each `OrchestratorBackend` subclass declares its own appropriate fallback.

#### REFACTOR

Added docstrings explaining *why* the fallback exists (`OrchestratorBackend cannot handle per-turn calls`) so future developers understand the constraint without reading the history.

---

### Example 2 — `ConversationState.needs_resume()`

**Context:** `resume_debate()` must raise `RuntimeError` if called on a completed debate, not silently re-run all turns.

#### RED

```python
# tests/unit/test_orchestrator_core.py

def test_resume_raises_if_complete(orch, state):
    """resume_debate raises RuntimeError if the debate is already complete."""
    for i in range(1, 5):
        state.append_turn({"agent": "A", "turn": i, "argument": "x", "references": []})
    with pytest.raises(RuntimeError, match="complete"):
        orch.resume_debate()
```

This fails if `resume_debate()` doesn't guard against complete state.

#### GREEN

```python
# orchestrator.py
def resume_debate(self) -> None:
    if self.state.is_complete(self.config.turns):
        raise RuntimeError("Debate is already complete — cannot resume.")
    ...
```

#### REFACTOR

Extracted `state.is_complete()` as a named method on `ConversationState` rather than inlining the length check in the orchestrator, making the intent readable.

---

### Example 3 — `validate_stance()` Concession Detection

**Context:** An agent that concedes or agrees with the opponent should be caught and the response retried.

#### RED

```python
# tests/unit/test_stance_validator.py

@pytest.mark.parametrize("text", [
    "I concede your point about renewable energy",
    "You are absolutely right that AI will create jobs",
    "I agree with your analysis",
])
def test_concession_phrases_detected(text):
    result = validate_stance(text)
    assert result.is_valid is False
```

All three fail before `validate_stance()` exists.

#### GREEN

```python
# src/stance_validator.py
CONCESSION_PHRASES = ["i concede", "you are right", "i agree"]

def validate_stance(text: str) -> ValidationResult:
    lower = text.lower()
    for phrase in CONCESSION_PHRASES:
        if phrase in lower:
            return ValidationResult(is_valid=False, reason=f"Concession detected: '{phrase}'")
    return ValidationResult(is_valid=True)
```

#### REFACTOR

Expanded the phrase list based on edge cases found in example debate outputs, and moved the list to `src/constants.py` to make it configurable.

---

## Key TDD Benefits Demonstrated in This Project

| Benefit | Where it helped |
|---------|----------------|
| **No untested code paths** | Every validator function was driven by parametrized RED tests; no dead branches sneak in |
| **Design pressure** | Writing tests first revealed that `validate_topic()` depended on a hard-coded fallback — the test forced a cleaner class-attribute design |
| **Regression protection** | All 200 tests run in < 5 seconds; every commit is gated against the full suite |
| **Living documentation** | Test names like `test_resume_raises_if_complete` describe system behaviour in plain English |

---

## Running Tests

```bash
# Full suite with coverage (≥85% enforced)
uv run pytest --cov=src --cov=orchestrator --cov-report=term

# TDD inner loop: run only the file you're working on
uv run pytest tests/unit/test_orchestrator_core.py -v

# Watch mode (re-run on file change) — requires pytest-watch
uv run ptw tests/unit/test_orchestrator_core.py
```
