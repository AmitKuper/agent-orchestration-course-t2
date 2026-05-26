# Claude API Run Costs

Costs for running the 3 example topics with the `claude-api` backend.
Pricing: claude-haiku-4-5 at $0.80/M input + $4.00/M output tokens.
Pricing: claude-sonnet-4-6 at $3.00/M input + $15.00/M output tokens.

## Haiku (claude-haiku-4-5-20251001)

| Topic | Run ID | Input Tokens | Output Tokens | Cost (USD) |
|-------|--------|-------------|--------------|------------|
| ai-jobs | 20260526_221535 | 138,438 | 16,532 | $0.663 |
| iran-nuclear | 20260526_221931 | 130,960 | 13,329 | $0.593 |
| messi-ronaldo | 20260526_222240 | 135,278 | 15,130 | $0.633 |
| **Total** | | **404,676** | **44,991** | **$1.889** |

## Sonnet (claude-sonnet-4-6)

| Topic | Run ID | Input Tokens | Output Tokens | Cost (USD) |
|-------|--------|-------------|--------------|------------|
| ai-jobs | 20260526_224834 | 260,515 | 31,022 | $1.247 |
| iran-nuclear | 20260526_225837 | 261,185 | 31,656 | $1.258 |
| messi-ronaldo | 20260526_233207 | 290,324 | 33,308 | $1.371 |
| **Total** | | **812,024** | **95,986** | **$3.876** |

## Notes

- Input tokens grow with every turn because each agent receives the full conversation history.
- Sonnet uses ~2× the tokens of Haiku per run due to longer, more detailed arguments.
- The failed pre-fix run (20260526_220647, ai-jobs) cost $1.242 and produced no verdict — not included above.
