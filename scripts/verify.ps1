# wxlocal pre-commit verification (T0-T5). Integration tests T2/T3 require WeChat + .env.
param(
    [switch]$SkipIntegration
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "T1 compileall..."
& $python -m compileall -q wxlocal
if ($LASTEXITCODE -ne 0) { throw "T1 compileall failed ($LASTEXITCODE)" }
Write-Host "  OK"

Write-Host "T5 pytest..."
& $python -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) { throw "T5 pytest failed ($LASTEXITCODE)" }
Write-Host "  OK"

Write-Host "T0 env binding (fresh process, no WeChat)..."
& $python scripts\check_env_binding.py
if ($LASTEXITCODE -ne 0) { throw "T0 env binding failed ($LASTEXITCODE)" }
Write-Host "  OK"

if (-not $SkipIntegration) {
    Write-Host "T2 wxlocal-watch --once..."
    $watch = Join-Path $Root ".venv\Scripts\wxlocal-watch.exe"
    if (Test-Path $watch) {
        & $watch --once
    } else {
        & $python -m wxlocal.pipelines.chat_watch.daemon --once
    }
    if ($LASTEXITCODE -ne 0) { throw "T2 watch failed ($LASTEXITCODE)" }
    Write-Host "  OK"

    Write-Host "T3 wxlocal-mp-scroll --once..."
    $scroll = Join-Path $Root ".venv\Scripts\wxlocal-mp-scroll.exe"
    if (Test-Path $scroll) {
        & $scroll --once
    } else {
        & $python -m wxlocal.pipelines.mp_scroll.daemon --once
    }
    if ($LASTEXITCODE -ne 0) { throw "T3 mp-scroll failed ($LASTEXITCODE)" }
    Write-Host "  OK"
} else {
    Write-Host "T2/T3 skipped (-SkipIntegration) — still ran T0/T5"
}

Write-Host "T4 doc links..."
$docs = @(
    "docs/DISCLAIMER.md",
    "docs/STANDALONE.md",
    "docs/MP_CAPTURE.md",
    "docs/WECHAT_4.1.13_RESEARCH.md",
    "docs/LOCAL_SETUP.example.md",
    "docs/ARCHITECTURE.md",
    "docs/DEV_PLAN.md",
    "CHANGELOG.md"
)
foreach ($rel in $docs) {
    if (-not (Test-Path (Join-Path $Root $rel))) {
        throw "T4 missing: $rel"
    }
}
Write-Host "  OK"

Write-Host "T6 root .py count..."
$rootPy = @(Get-ChildItem -Path $Root -File -Filter "*.py" -ErrorAction SilentlyContinue)
if ($rootPy.Count -ne 0) {
    throw ("T6 root still has .py: " + (($rootPy | ForEach-Object Name) -join ", "))
}
Write-Host "  OK (0)"

Write-Host ""
Write-Host "All checks passed."
