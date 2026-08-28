# wxlocal pre-commit verification (T1-T5). Integration tests T2/T3 require WeChat + .env.
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
& $python -m compileall -q wxlocal mp_capture env_loader.py paths.py config.py watchdog.py watch_mp_idb.py app.py main.py service.py
if ($LASTEXITCODE -ne 0) { throw "T1 compileall failed ($LASTEXITCODE)" }
Write-Host "  OK"

Write-Host "T5 pytest..."
& $python -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) { throw "T5 pytest failed ($LASTEXITCODE)" }
Write-Host "  OK"

if (-not $SkipIntegration) {
    Write-Host "T2 watchdog --once..."
    & $python watchdog.py --once
    if ($LASTEXITCODE -ne 0) { throw "T2 watchdog failed ($LASTEXITCODE)" }
    Write-Host "  OK"

    Write-Host "T3 watch_mp_idb --once..."
    & $python watch_mp_idb.py --once
    if ($LASTEXITCODE -ne 0) { throw "T3 watch_mp_idb failed ($LASTEXITCODE)" }
    Write-Host "  OK"
} else {
    Write-Host "T2/T3 skipped (-SkipIntegration)"
}

Write-Host "T4 doc links..."
$docs = @(
    "docs/DISCLAIMER.md",
    "docs/STANDALONE.md",
    "docs/MP_CAPTURE.md",
    "docs/WECHAT_4.1.13_RESEARCH.md",
    "docs/LOCAL_SETUP.example.md",
    "docs/ARCHITECTURE.md",
    "docs/DEV_PLAN.md"
)
foreach ($rel in $docs) {
    if (-not (Test-Path (Join-Path $Root $rel))) {
        throw "T4 missing: $rel"
    }
}
Write-Host "  OK"

Write-Host ""
Write-Host "All checks passed."
