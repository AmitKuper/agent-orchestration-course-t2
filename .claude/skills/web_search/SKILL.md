---
name: web_search
description: Search the web for evidence, statistics, citations, and factual verification. Use when a debater agent needs supporting sources or when the judge needs to verify a factual claim.
allowed-tools: WebSearch
arguments:
  query: The search query string
---

Search the web for: $query

Return the top results as JSON only:

```json
{"results": [{"title": "...", "url": "...", "snippet": "..."}]}
```

Include up to 5 results. If no results are found, return `{"results": []}`.
Output only the JSON — no explanation, no preamble.
