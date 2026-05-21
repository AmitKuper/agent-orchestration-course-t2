---
name: judgment
description: Score a completed debate and declare a winner. Reads the conversation JSONL file, validates the debate is complete, formats the transcript, and invokes the debate-judge agent. Also user-invocable directly via /judgment on any completed debate file.
allowed-tools: Bash, Read
arguments:
  conversation_path: Path to the completed debate JSONL file
  agent_a_name: Name of debater A
  agent_b_name: Name of debater B
  factcheck_enabled: "true or false — whether to verify factual claims"
---

**Step 1 — Read and validate the conversation file**

Read the JSONL file at `$conversation_path` using the Read tool. Parse each line as a JSON object.

Validate that the debate is complete:
- The file must exist and be non-empty
- If the file is empty or missing, return: `{"error": "No completed debate found at the specified path."}`

**Step 2 — Invoke the judge**

Pass the full transcript to the `debate-judge` agent with:
- `$HISTORY` = all parsed turns
- `$AGENT_A_NAME` = $agent_a_name
- `$AGENT_B_NAME` = $agent_b_name
- `$FACTCHECK_ENABLED` = $factcheck_enabled

**Step 3 — Save the verdict**

Save the verdict to a timestamped result file in the same folder as the conversation file:

```bash
python -c "
from src.output import OutputManager
from pathlib import Path
import json, sys
verdict = json.loads(sys.stdin.read())
folder = Path('$conversation_path').parent
om = OutputManager.__new__(OutputManager)
om.run_folder = folder
path = om.result_path()
path.write_text(json.dumps(verdict, indent=2), encoding='utf-8')
print(str(path))
"
```

**Step 4 — Return the verdict**

Return the judge's JSON verdict exactly as received from the `debate-judge` agent.
