<#
.SYNOPSIS
    Run the AI Debate Platform pipeline.

.DESCRIPTION
    Launches a debate for a chosen topic and backend. Topic configs live in
    examples/configs/. Outputs go to outputs/<topic>/<backend>/.

.PARAMETER Topic
    Topic shorthand. One of: ai-jobs, social-media, iran-nuclear,
    messi-ronaldo, ubi, nuclear-energy.

.PARAMETER Backend
    Invocation backend. One of: api, cli, cli-ollama, ollama.
    cli-ollama = --backend cli, requires `ollama launch claude` running first.

.PARAMETER Model
    Ollama model name used when Backend is 'ollama' or 'cli-ollama'.
    Defaults to Qwen3:14b.

.PARAMETER Config
    Path to a custom JSON config file (overrides -Topic).

.PARAMETER Turns
    Override the number of turns from the config file.

.EXAMPLE
    .\run.ps1 -Topic messi-ronaldo -Backend ollama
    .\run.ps1 -Topic iran-nuclear -Backend api
    .\run.ps1 -Topic ubi -Backend cli
    .\run.ps1 -Config examples/debate-config.example.json -Backend ollama -Model gemma3:12b
#>

param(
    [ValidateSet("ai-jobs", "social-media", "iran-nuclear", "messi-ronaldo", "ubi", "nuclear-energy")]
    [string]$Topic,

    [Parameter(Mandatory)]
    [ValidateSet("api", "cli", "cli-ollama", "ollama")]
    [string]$Backend,

    [string]$Model = "Qwen3:14b",

    [string]$Config,

    [int]$Turns = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve config file ──────────────────────────────────────────────────────

if ($Config) {
    $configPath = $Config
} elseif ($Topic) {
    $configPath = "examples/configs/$Topic.json"
} else {
    Write-Error "Provide -Topic or -Config."
    exit 1
}

if (-not (Test-Path $configPath)) {
    Write-Error "Config file not found: $configPath"
    exit 1
}

# ── Resolve backend and outdir ───────────────────────────────────────────────

$slug     = if ($Topic) { $Topic } else { [System.IO.Path]::GetFileNameWithoutExtension($configPath) }
$actualBackend = if ($Backend -eq "cli-ollama") { "cli" } else { $Backend }
$outdir   = "outputs/$slug/$Backend"

# ── Pre-flight checks ────────────────────────────────────────────────────────

if ($Backend -eq "ollama") {
    try {
        python -c "import requests" 2>$null
    } catch {
        Write-Host "[INFO] Installing requests..." -ForegroundColor Cyan
        pip install requests
    }

    $ollamaList = ollama list 2>&1
    if ($ollamaList -notmatch [regex]::Escape($Model)) {
        Write-Warning "Model '$Model' not found in ollama list. Available models:"
        ollama list
        exit 1
    }
}

if ($Backend -eq "cli-ollama") {
    Write-Host ""
    Write-Host "  NOTE: cli-ollama requires 'ollama launch claude' to be running." -ForegroundColor Yellow
    Write-Host "  Start it in a separate terminal before continuing." -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "  Press Enter to continue, or Ctrl+C to cancel"
}

if ($Backend -eq "api") {
    if (-not $env:ANTHROPIC_API_KEY) {
        $envFile = ".env"
        if (Test-Path $envFile) {
            Get-Content $envFile | ForEach-Object {
                if ($_ -match "^ANTHROPIC_API_KEY=(.+)$") {
                    $env:ANTHROPIC_API_KEY = $Matches[1]
                }
            }
        }
        if (-not $env:ANTHROPIC_API_KEY) {
            Write-Error "ANTHROPIC_API_KEY is not set. Add it to .env or set the environment variable."
            exit 1
        }
    }
}

# ── Build argument list ──────────────────────────────────────────────────────

$args = @(
    "main.py",
    "--config", $configPath,
    "--backend", $actualBackend,
    "--outdir",  $outdir
)

if ($Turns -gt 0) {
    $args += @("--turns", $Turns)
}

if ($Backend -in @("ollama", "cli-ollama")) {
    $args += @("--model-a", $Model, "--model-b", $Model, "--model-judge", $Model)
}

# ── Run ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  Topic    : $configPath"   -ForegroundColor Cyan
Write-Host "  Backend  : $Backend"      -ForegroundColor Cyan
if ($Backend -in @("ollama", "cli-ollama")) {
Write-Host "  Model    : $Model"        -ForegroundColor Cyan
}
Write-Host "  Output   : $outdir"       -ForegroundColor Cyan
Write-Host ""

python @args
