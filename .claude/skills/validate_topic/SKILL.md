---
name: validate_topic
description: Validates that a debate topic can be split into exactly two clear opposing positions. Use once before a debate starts. Returns both positions if valid.
arguments:
  topic: The debate topic to validate
---

Evaluate whether the following topic can be clearly split into exactly two opposing, defensible positions:

**Topic:** $topic

Rules:
- Must have exactly two sides that directly contradict each other
- Both sides must be arguable (not trivially one-sided or factual)
- Must be debatable in English regardless of original language
- Reject ambiguous, harmful, or unanswerable topics

If valid, extract the two opposing positions concisely.

Respond with JSON only:

```json
{"valid": true, "position_a": "...", "position_b": "..."}
```

or

```json
{"valid": false, "reason": "..."}
```
