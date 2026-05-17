---
name: validate_json
description: Validates that a given text string is well-formed JSON using Python json.loads. Use after every agent response before accepting it.
allowed-tools: Bash
arguments:
  text: The raw response string to validate
---

Run the following Bash command to validate the input:

```bash
python -c "
import json, sys
text = '''$text'''
try:
    json.loads(text)
    print('{\"valid\": true}')
except json.JSONDecodeError as e:
    print('{\"valid\": false, \"error\": \"' + str(e) + '\"}')
"
```

Return the JSON output exactly as printed.
