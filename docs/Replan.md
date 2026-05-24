Its seems that my originate plan was not explained accordingly.
I want that the code will support 4 diffrent backends:
1. Claude CLI (using the current plan) - this is the default
2. Claude using API-KEY
3. Ollama using ollama launch claude - ollama allow running claude on its own model
4. Ollama as an API.

Calude CLI
First change the model per agent in the .claude/agents agents files according to the provided configuration
Than use Calude in the cli command and use the model parameter to decide the model that the claude start with

Ollama claude CLI
the same as Cllaude CLI but the provided model and all agents model must be ollama installed models

Claude API
Uses the claude api

Ollama API
Uses the ollama api