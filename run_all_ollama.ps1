$python = ".\.venv\Scripts\python.exe"
$logFile = "outputs\run_all_ollama.log"

New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting 9-run sweep: 3 topics x 3 ollama backends" | Tee-Object -FilePath $logFile

$runs = @(
    # ollama-api
    @{ config = "examples/ai-jobs/config-ollama-api.json";           label = "ai-jobs / ollama-api" },
    @{ config = "examples/iran-nuclear/config-ollama-api.json";      label = "iran-nuclear / ollama-api" },
    @{ config = "examples/messi-ronaldo/config-ollama-api.json";     label = "messi-ronaldo / ollama-api" },
    # ollama-cli (OllamaOrchestratorBackend)
    @{ config = "examples/ai-jobs/config-ollama-cli.json";           label = "ai-jobs / ollama-cli" },
    @{ config = "examples/iran-nuclear/config-ollama-cli.json";      label = "iran-nuclear / ollama-cli" },
    @{ config = "examples/messi-ronaldo/config-ollama-cli.json";     label = "messi-ronaldo / ollama-cli" },
    # ollama-cli-agents (OllamaCliBackend)
    @{ config = "examples/ai-jobs/config-ollama-cli-agents.json";    label = "ai-jobs / ollama-cli-agents" },
    @{ config = "examples/iran-nuclear/config-ollama-cli-agents.json"; label = "iran-nuclear / ollama-cli-agents" },
    @{ config = "examples/messi-ronaldo/config-ollama-cli-agents.json"; label = "messi-ronaldo / ollama-cli-agents" }
)

$total = $runs.Count
$i = 0
foreach ($run in $runs) {
    $i++
    $start = Get-Date
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$i/$total] START: $($run.label)" | Tee-Object -FilePath $logFile -Append
    & $python main.py --config $run.config 2>&1 | Tee-Object -FilePath $logFile -Append
    $exit = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $start).TotalSeconds
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$i/$total] DONE: $($run.label)  exit=$exit  elapsed=${elapsed}s" | Tee-Object -FilePath $logFile -Append
    ""  | Add-Content $logFile
}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] All $total runs complete." | Tee-Object -FilePath $logFile -Append
