# Deprecated — use setup_wxlocal_autostart.bat (Startup folder, mp-scroll + chat-watch).
#
# This wrapper forwards to setup_wxlocal_autostart.ps1 for backward compatibility.

param(
    [ValidateSet("Startup", "Task")]
    [string]$Mode = "Startup",
    [switch]$Uninstall,
    [string]$ProjectRoot = "",
    [string]$TaskName = "WxLocalAutostart"
)

Write-Host "[!] setup_autostart.ps1 is deprecated; use setup_wxlocal_autostart.bat" -ForegroundColor Yellow
Write-Host ""

$target = Join-Path $PSScriptRoot "setup_wxlocal_autostart.ps1"
if (-not (Test-Path $target)) {
    Write-Error "Missing $target"
    exit 1
}

& $target -Mode $Mode -Uninstall:$Uninstall -ProjectRoot $ProjectRoot -TaskName $TaskName
exit $LASTEXITCODE
