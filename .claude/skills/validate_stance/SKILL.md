---
name: validate_stance
description: Checks whether a debater agent's argument actually supports their assigned claim/position. Use after every debate turn to detect off-topic or conceding responses.
arguments:
  text: The agent's argument text to evaluate
  claim: The position the agent is supposed to be defending
---

Evaluate whether the following argument supports the assigned claim.

**Claim the agent must defend:** $claim

**Agent's argument:** $text

Check for:
- Does the argument actively advocate for the claim?
- Does it concede, agree with, or validate the opposing side?
- Is it clearly off-topic or unrelated to the claim?

Respond with JSON only:

```json
{"supports_claim": true, "confidence": "high", "reason": "..."}
```

or

```json
{"supports_claim": false, "confidence": "high", "reason": "..."}
```

Confidence values: `high`, `medium`, `low`.
