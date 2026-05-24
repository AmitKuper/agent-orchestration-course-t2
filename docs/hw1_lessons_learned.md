# Lessons Learned: From HW1 to HW2

## The Story

### HW1 — Signal Extraction with Neural Networks

HW1 was a machine learning project: build a neural network pipeline that recovers clean sinusoid components from a noisy composite signal, comparing three architectures (Fully Connected, RNN, LSTM). It included a Streamlit GUI, Jupyter notebooks for analysis, PyTorch training, and a full evaluation framework.

The project was technically ambitious and well-structured, with a comprehensive planning document, layered SDK architecture, 180+ tests, and 98.53% coverage. It was submitted with high confidence.

**Grade received: 73.64 base → 83.64 after automatic 10-point bonus.**

The feedback noted that expressing strong confidence in the work triggered a more rigorous evaluation lens — a useful reminder that self-assessment must be grounded.

### HW2 — AI Debate Platform

HW2 is a different kind of project: a multi-agent orchestration pipeline where two AI agents argue opposing sides of a topic, an orchestrator manages the debate lifecycle, and a judge agent scores the result. The primary learning goal is hands-on mastery of Claude Code agent orchestration — skills, context management, state persistence, and inter-agent communication.

HW2 has no GUI requirement and no notebooks. It is a CLI-first, backend-agnostic, fully tested Python system with 160 tests at 100% coverage, strict 150-line file limits, and support for multiple inference backends (Anthropic API, Claude CLI, Ollama CLI, Ollama HTTP API).

---

## HW1 Feedback Summary

### Areas of Excellence (what was praised)

- **Code Documentation** — clear, professional, allows any developer to get started
- **Configuration & Security** — proper use of `.env`, config files, no secrets in code
- **Testing Quality** — rigorous coverage across edge cases
- **Research & Analysis** — documented experimental process with genuine insight
- **Version Management** — disciplined commit history with AI-assisted workflow visible
- **Mixed-Signal Generation** — principled construction of composite signals
- **Train/Test/Generalization Evaluation** — clean measurement with meaningful interpretation
- **Visualization** — panel-based plots across all frequencies

### Areas for Improvement (what was criticised)

| Area | Feedback |
|------|----------|
| **Project Planning** | Lacked foundational planning docs; a new team member couldn't understand the vision without asking |
| **UI/UX** | User-facing experience not communicated; reader can't understand what it feels like to use the system without running it |
| **Costs & Pricing** | No evidence of cost or resource awareness; real-world AI apps must consider economic implications |
| **Extensibility** | Architecture didn't clearly separate concerns; hard to tell how a new developer would extend without disrupting |
| **Quality Standards** | Automated quality tooling not clearly established |
| **ML-Specific Issues** | Per-sample noise variation, clean target separation, train/test seed discipline, LSTM architecture, sequence-length justification, training loop visibility (all domain-specific to HW1) |

---

## Mapping Feedback to HW2

The ML-specific items (noise variation, LSTM architecture, training loop, etc.) are not applicable to HW2. The structural and professional-standards items all are.

### ✅ Weaknesses from HW1 that HW2 directly addresses

| HW1 Weakness | How HW2 Addresses It |
|---|---|
| **Project Planning** | Full PRD, per-component PRDs (agents, backends, orchestrator), PLAN.md with architecture decisions, TODO.md updated per commit |
| **Costs & Pricing** | `docs/cost.md` with per-call token tracking; Ollama backend explicitly adopted and documented as a zero-cost alternative to the Anthropic API during development |
| **Quality Standards** | Ruff enforced with zero violations; 150-line file limit enforced via refactoring; 160 tests at 100% coverage; commit conventions enforced (`Feature:`, `BugFix:`, `Refactor:`, `Docs:`) |

### ⚠️ Partially addressed — present but could be stronger

**UI/UX — The CLI experience is not demonstrated**
HW2 has no GUI (intentionally — it is out of scope). However, the feedback was really about helping a reader understand what using the system feels like without running it. The README explains flags and config but doesn't show a real run: what the terminal looks like, what files are produced, what the verdict JSON looks like. The `examples/` directory contains real run outputs but it's buried and not surfaced as a live demonstration.

**Extensibility — Architecture is good, documentation of extension paths is thin**
HW2 has solid separation of concerns (Backend abstraction, BaseAgent ABC, validator, orchestrator fully decoupled from debate content). However, HW1's PLAN.md had explicit "How to Extend" sections, a Plugin Architecture, and a full ISO/IEC 25010 compliance matrix. HW2's PLAN.md has a Key Technical Decisions table but doesn't tell a developer *how* to add a new backend, a new agent type, or a new validation rule.

**PLAN.md directory structure is stale**
The directory tree in PLAN.md was written at project inception and was never updated to reflect the actual codebase. It still shows `src/backends.py` (now a package), missing `src/sdk/`, `src/shared/`, `src/agents/loader.py`, `src/debate_helpers.py`, and old test file names.

### ❌ Not yet covered

**Research & Analysis**
HW1 was praised for "analytical work that clearly documents the experimental process and insights derived from it." HW2's equivalent is the example debates — three complete runs with judge verdicts, scores, and factcheck flags. But this material is sitting in `examples/` as raw JSON files with no synthesis. There is no document that asks: What did we observe? Were certain models more prone to JSON retries? How reliable was the factchecker? What patterns emerged in the judge's scoring? This is the human insight layer that distinguishes a project that ran from a project that was understood.

---

## What Should Be Done Better in HW2

In priority order:

### 1. ✅ Add a "Sample Run" section to README
Show the actual terminal output of a debate run — log lines, retry warnings, verdict printed to console — and the resulting `result.json`. A reader should be able to see the full lifecycle in under one page without running anything.
→ **Done:** Added to README with real log output, result JSON, and output file listing.

### 2. ✅ Add `docs/analysis.md`
Write a 1–2 page synthesis of the three example debates (iran-nuclear, ai-jobs, messi-ronaldo):
- Retry frequency per backend/model
- What the factchecker caught (and whether flags were accurate)
- Patterns in judge scoring across topics
- What surprised us about the system's behaviour in practice
This is the "research & analysis" layer that demonstrates genuine engagement with the output.
→ **Done:** `docs/analysis.md` created covering retry analysis, factchecker observations, scoring patterns, and platform behaviour conclusions.

### 3. ✅ Update PLAN.md directory structure
Bring the directory tree up to date with the actual codebase — backends package, sdk, shared, loader, debate_helpers, all split test files.
→ **Done:** Directory tree in PLAN.md fully updated.

### 4. ✅ Add "How to Extend" to PLAN.md
Document how a new developer would:
- Add a new backend (what interface to implement)
- Add a new agent type (what to subclass)
- Add a new validation rule (where to add it)
→ **Done:** "How to Extend" section added to PLAN.md with step-by-step instructions for all four extension paths.

### 5. ✅ ISO/IEC 25010 compliance matrix (optional but strong signal)
HW1 included a quality characteristics compliance matrix. Adding one to HW2 demonstrates professional engineering awareness and gives the evaluator a single structured view of how the project meets each quality dimension.
→ **Done:** Added to PLAN.md covering Functional Suitability, Reliability, Performance Efficiency, Usability, Security, Maintainability, and Portability.

---

## Key Takeaway

HW1 was strong on implementation and weak on documentation of process, cost awareness, and communicating the user experience. HW2 fixed the first two explicitly. The remaining gap is the same one: **showing that the system was not just built but understood** — through demonstrated use, observed behaviour, and synthesised analysis.
