# Run once after closing Cursor/terminals using the old path.
# Removes E:\workspace\wechat-reader if E:\workspace\wxlocal is the active clone.

$ErrorActionPreference = "Stop"
$legacy = "E:\workspace\wechat-reader"
$current = "E:\workspace\wxlocal"

if (-not (Test-Path $current)) {
    Write-Error "Expected active repo at $current"
    exit 1
}
if (-not (Test-Path $legacy)) {
    Write-Host "[ok] Legacy folder already gone: $legacy"
    exit 0
}

try {
    Remove-Item -LiteralPath $legacy -Recurse -Force -ErrorAction Stop
} catch {
    Write-Warning "Could not remove $legacy (files in use). Close Cursor/old daemons and retry."
    Write-Warning $_.Exception.Message
    exit 1
}

if (Test-Path $legacy) {
    Write-Warning "Legacy folder still exists: $legacy"
    exit 1
}

Write-Host "[ok] Removed legacy folder: $legacy"
