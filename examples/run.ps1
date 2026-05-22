# ── Edit these parameters before running ────────────────────────────────────

$config      = "examples/configs/messi-ronaldo.json"
$backend     = "ollama"       # api | cli | ollama
$model       = "Qwen3:14b"   # Ollama model (ignored for api / cli)
$turns       = 20            # 0 = use value from config file
$outdir      = "outputs/messi-ronaldo/ollama"
$temperature = 0.8           # sampling temperature (0.0-1.0); 0 = model default

# ─────────────────────────────────────────────────────────────────────────────

$args = @("main.py", "--config", $config, "--backend", $backend, "--outdir", $outdir)

if ($turns -gt 0)                        { $args += @("--turns", $turns) }
if ($backend -eq "ollama")               { $args += @("--model-a", $model, "--model-b", $model, "--model-judge", $model) }
if ($temperature -gt 0)                  { $args += @("--temperature", $temperature) }

python @args
