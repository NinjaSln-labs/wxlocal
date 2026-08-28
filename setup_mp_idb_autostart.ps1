# Deprecated — forwards to setup_wxlocal_autostart.ps1
param(
    [ValidateSet("Startup", "Task")]
    [string]$Mode = "Startup",
    [switch]$Uninstall,
    [string]$ProjectRoot = "",
    [string]$TaskName = "WxLocalAutostart"
)

Write-Host "[!] setup_mp_idb_autostart.ps1 is deprecated; use setup_wxlocal_autostart.bat" -ForegroundColor Yellow
& "$PSScriptRoot\setup_wxlocal_autostart.ps1" -Mode $Mode -Uninstall:$Uninstall -ProjectRoot $ProjectRoot -TaskName $TaskName
exit $LASTEXITCODE
