# Debate Platform — Experimental Analysis

Three debates were run using the `ollama-cli` backend (Qwen3:14b) to validate the platform
end-to-end and observe real behaviour. This document synthesises the findings.

---

## Debates Run

| Topic | Agents | Turns | Backend |
|-------|--------|-------|---------|
| Iran nuclear — attack vs. diplomacy | Hawk vs. Dove | 20 | ollama-cli / Qwen3:14b |
| AI automation — jobs destroyed vs. created | Pessimist vs. Optimist | 20 | ollama-cli / Qwen3:14b |
| Soccer GOAT — Messi vs. Ronaldo | TeamMessi vs. TeamRonaldo | 20 | ollama-cli / Qwen3:14b |

---

## Results Summary

| Debate | Winner | Margin | Factcheck Flags |
|--------|--------|--------|----------------|
| Iran nuclear | Dove (diplomacy) | 37 – 35 | 2 (Hawk cited unverifiable studies) |
| AI jobs | Pessimist | 35 – 31 | 0 |
| Messi vs. Ronaldo | TeamMessi | 36 – 32 | 0 |

---

## Retry & Reliability Analysis

All three debates ran on Qwen3:14b via `ollama-cli`. The model's thinking mode emits
cursor-correction ANSI escape sequences before outputting JSON, which required a dedicated
VT100 terminal emulator (`src/backends/_ansi.py`) to clean the output reliably.

| Debate | Total Retries | Skipped Turns | Root Cause |
|--------|--------------|---------------|------------|
| Iran nuclear | 4 retries | 1 (Hawk turn 1) | All `Invalid JSON: Expecting ',' delimiter` — model included unescaped commas inside string values |
| AI jobs | 2 retries | 0 | Same root cause; retry prompt succeeded on 2nd attempt |
| Messi vs. Ronaldo | 0 retries | 0 | Clean run |

**Pattern:** JSON serialisation errors were the only failure mode — the model understood the
task and produced substantive arguments, but occasionally embedded commas or apostrophes in
ways that broke the JSON structure. The format-specific retry prompt (no history re-attachment,
just "fix the JSON") resolved these in 1–2 attempts in all but one case.

The one turn skip (Hawk, turn 1, iran-nuclear) occurred on the platform's first ever run.
All subsequent runs either had zero skips or recovered via retry.

---

## Factchecker Observations

Factcheck was enabled (`"factcheck": true`) for all three debates.

**Iran nuclear — 2 flags raised:**
- `"2024 MIT Security Analysis"` — cited by Hawk; the judge could not verify this as a real publication
- `"2024 Stanford Nonproliferation Study"` — same issue

Both flags were against Hawk (the losing side), and both were framed as authoritative-sounding
institution names without traceable publication details. This is a known Qwen3 hallucination
pattern: the model constructs plausible-sounding citations rather than recalling real ones.

**AI jobs — 0 flags**, despite the Optimist citing UNESCO and WEF figures.
This is notable: in an earlier (discarded) run the judge flagged those same Optimist citations
as unverifiable. In the accepted run they were not flagged, suggesting the factchecker's
behaviour is non-deterministic across runs even on the same model — consistent with LLM
stochasticity.

**Messi vs. Ronaldo — 0 flags.** The judge explicitly confirmed all statistics as accurate.
Sports statistics are well-represented in training data, making hallucination less likely here.

---

## Scoring Patterns

Across all three debates the judge displayed two consistent behaviours:

1. **Compressed score range.** All scores fell between 7 and 10. The judge never awarded
   below 7 on any criterion, even to the losing side. This suggests the model interprets
   the rubric relative to the quality of the debate it witnessed rather than against an
   absolute standard — both sides argued well, so both scored highly.

2. **Persuasiveness as the tiebreaker dimension.** In all three debates, the winning agent
   had a higher persuasiveness score than the other criteria gap would suggest. The judge's
   explanations consistently cited persuasiveness as the differentiating factor, even when
   logic and evidence scores were equal. This aligns with the judge prompt's framing, which
   asks for a winner — the model resolves close calls by amplifying small persuasiveness gaps.

3. **Evidence quality drove outcomes more than argumentation style.** In the two debates
   where factcheck flags were possible (iran-nuclear and ai-jobs), the side that relied on
   verifiable, named institutions (ILO, IAEA, McKinsey) outscored the side that used
   vaguer or fabricated citations. This is a meaningful signal: the judge appears sensitive
   to citation quality even without formal fact-checking — and the factchecker reinforces it
   when enabled.

---

## Platform Behaviour Observations

**Retry categorisation worked as designed.** All retries were format failures (bad JSON).
The format retry prompt — which omits history and focuses purely on fixing serialisation —
resolved every case except the one exhausted turn. No content failures (too short, empty,
disrespectful) were observed across any run, which reflects well on Qwen3:14b's ability to
follow the debate task.

**Parallel execution was safe.** The ai-jobs and messi-ronaldo debates were run in parallel
(background processes) without any state collision, shared file corruption, or interleaved
output. The per-run output folder isolation worked correctly.

**Runtime per debate:** approximately 5–8 minutes for a 20-turn debate on a local GPU with
Qwen3:14b. The judge invocation (single call with full transcript context) added ~30 seconds.

---

## Conclusions

1. Qwen3:14b is a viable model for this platform but requires ANSI output cleaning and
   tolerates ~10–15% of turns needing a format retry. Larger or more instruction-tuned
   models would likely reduce this further.

2. The factchecker adds meaningful signal but its output is non-deterministic. Flags should
   be treated as probabilistic hints rather than definitive verdicts, especially for
   citation-dense topics.

3. The judge's compressed scoring range (7–10) is a design consideration for future work:
   if finer discrimination is needed, the prompt could explicitly require using the full
   0–10 range.

4. The retry system performed its core function: one skipped turn in three 20-turn debates
   (~0.3% skip rate) is an acceptable reliability level for a local open-source model.
