# Run once after closing Cursor/terminals using the old path.
# Removes E:\workspace\wechat-reader if E:\workspace\wxlocal is the active clone.

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
    Remove-Item -LiteralPath $legacy -Recurse -Force
    Write-Host "[ok] Removed legacy folder: $legacy"
} catch {
    Write-Warning "Could not remove $legacy (still in use). Close Cursor and retry."
    exit 1
}
