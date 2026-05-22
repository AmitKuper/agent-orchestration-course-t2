# ── Edit these parameters before running ────────────────────────────────────

$config  = "examples/configs/messi-ronaldo.json"
$backend = "ollama"       # api | cli | ollama
$model   = "Qwen3:14b"   # Ollama model (ignored for api / cli)
$turns   = 6             # 0 = use value from config file
$outdir  = "outputs/messi-ronaldo/ollama"

# ─────────────────────────────────────────────────────────────────────────────

$args = @("main.py", "--config", $config, "--backend", $backend, "--outdir", $outdir)

if ($turns -gt 0)                        { $args += @("--turns", $turns) }
if ($backend -eq "ollama")               { $args += @("--model-a", $model, "--model-b", $model, "--model-judge", $model) }

python @args
