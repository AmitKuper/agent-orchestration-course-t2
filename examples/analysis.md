# Example Runs — Analysis

Generated: 2026-05-26 | Model: Qwen3:14b (all runs except noted)

## Overview

9 debates across 3 topics × 3 backends. All runs completed 20/20 turns with zero skipped turns and zero post-novelty repeats, except where noted.

---

## Results by Topic

### AI Automation & Jobs
*"Will AI automation destroy more jobs than it creates, or will it generate new industries that outweigh the losses?"*
**Winner across all backends: Optimist**

| Backend | Turns | Pessimist | Optimist | Margin | Notes |
|---------|-------|-----------|----------|--------|-------|
| ollama-api | 20/20 | 32 | 35 | +3 | Clean, direct rebuttals, evolving evidence |
| ollama-cli | 20/20 | 35 | 46 | +11 | Lopsided — single-shot model shows scoring bias |
| ollama-cli-agents | 20/20 | 33 | 36 | +3 | Strongest quality; both sides cited ILO, OECD, WEF, IBM reskilling |

---

### Iran Nuclear — Attack vs. Diplomacy
*"Will attacking Iran prevent them from achieving a nuclear weapon, or is diplomacy the way to go?"*
**Winner across all backends: Dove (diplomacy)**

| Backend | Turns | Hawk | Dove | Margin | Notes |
|---------|-------|------|------|--------|-------|
| ollama-api | 20/20 | 35 | 36 | +1 | Very close; novelty check fired once (turn 16), forced fresh argument |
| ollama-cli | 20/20 | 34 | 43 | +9 | Lopsided — single-shot scoring bias |
| ollama-cli-agents | 20/20 | 28 | 34 | +6 | Debaters: gemma3:12b; Judge: Qwen3:14b (Qwen3 produced invalid JSON on early turns consistently) |

---

### Messi vs. Ronaldo
*"Who is the greatest soccer player of all time — Lionel Messi or Cristiano Ronaldo?"*
**Winner across all backends: TeamMessi**

| Backend | Turns | TeamMessi | TeamRonaldo | Margin | Notes |
|---------|-------|-----------|-------------|--------|-------|
| ollama-api | 20/20 | 35 | 33 | +2 | Good engagement; novelty check fired 4×, all corrected |
| ollama-cli | 20/20 | 45 | 35 | +10 | Lopsided — single-shot scoring bias |
| ollama-cli-agents | 20/20 | 35 | 34 | +1 | Very close; 2 borderline repeats (0.77, 0.79) — retry fired but correction only marginal |

---

## Backend Comparison

### ollama-api
- **Format reliability**: High — occasional JSON errors corrected within 1 retry
- **Argument quality**: Good — agents directly attack opponent claims, cite specific evidence (JCPOA, Osirak strike, WEF job forecasts), arguments evolve across turns
- **Novelty**: Novelty check fired and forced corrections in 2/3 topics; post-run repeats = 0
- **Scores**: Competitive margins (1–3 points); reflects genuine debate quality

### ollama-cli (single-shot orchestrator)
- **Format reliability**: Perfect — model generates all turns in one call, no per-turn JSON failures
- **Argument quality**: Shallow — agents state their own points but rarely attack the opponent's specific claims; engagement is weaker than per-turn backends
- **Novelty**: Not applicable (no per-turn validation); no observable verbatim repetition
- **Scores**: Consistently lopsided (10-point margins) — single-shot model shows scoring bias toward one side

### ollama-cli-agents (Qwen3:14b via ollama CLI)
- **Format reliability**: Low-medium — Qwen3:14b frequently produces unescaped characters inside JSON strings, causing `Expecting ',' delimiter` parse errors. Most resolve within 1–2 retries; occasionally all 3 retries fail on a turn
- **Argument quality**: Good to mediocre — better than single-shot but stagnates in later turns; `iran-nuclear` run switched to gemma3:12b to avoid persistent JSON failures
- **Novelty**: Novelty check fired in all 3 topics; post-run repeats = 0 for 2/3 (messi-ronaldo has 2 borderline pairs at 0.77/0.79)
- **Scores**: Competitive margins; judge reflects real quality differences

---

## Novelty Validation in Action

The novelty check (SequenceMatcher threshold 0.75) fired across multiple runs and successfully forced agents to introduce new arguments:

| Run | Agent | Fired on turns | Outcome |
|-----|-------|----------------|---------|
| iran-nuclear-api | Dove | 16 | Corrected ✅ |
| messi-ronaldo-api | TeamRonaldo | 8, 18, 20 | Corrected ✅ |
| messi-ronaldo-api | TeamMessi | 19 | Corrected ✅ |
| ai-jobs-ollama-cli-agents | Pessimist | 15 | Corrected ✅ |
| iran-nuclear-ollama-cli-agents | Dove | 8, 18 | Corrected ✅ |
| iran-nuclear-ollama-cli-agents | Hawk | 15, 19 | Corrected ✅ |
| messi-ronaldo-ollama-cli-agents | TeamMessi | 9, 11, 15, 17 | Corrected ✅ (2 borderline) |
| messi-ronaldo-ollama-cli-agents | TeamRonaldo | 18, 20 | Corrected ✅ |

---

## Known Issues

- **Qwen3:14b JSON reliability**: Produces unescaped apostrophes/commas inside JSON string values. Fails ~30–50% of turns on `iran-nuclear` topic with `ollama-cli-agents` backend. Resolved by switching to gemma3:12b for that run.
- **ollama-cli scoring bias**: Single-shot model consistently produces lopsided scores (10-point gaps vs. 1–3 for per-turn backends). The winner is correct but scores do not reflect close debates.
- **Borderline novelty** (`messi-ronaldo-ollama-cli-agents`): Turns 15→17 (0.77) and 17→19 (0.79) remain just above threshold after retry correction. The model updated the most-similar prior turn but residual similarity to a different prior turn persisted.
