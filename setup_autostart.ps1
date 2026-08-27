# 可选 — wxlocal chat-watch 任务计划（推荐 setup_wxlocal_autostart.bat）

param(
    [string]$ProjectRoot = "",
    [string]$TaskName = "WxLocalDaemon"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) { $ProjectRoot = $PSScriptRoot }

# 检查管理员
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "[!] 请以管理员身份运行此脚本" -ForegroundColor Red
    Write-Host "    右键 PowerShell -> 以管理员身份运行"
    exit 1
}

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$DaemonBat = Join-Path $ProjectRoot "run_daemon.bat"

if (-not (Test-Path $DaemonBat)) {
    Write-Host "[!] 未找到 run_daemon.bat: $DaemonBat" -ForegroundColor Red
    exit 1
}

Write-Host "[*] 项目目录: $ProjectRoot"
Write-Host "[*] 任务名称: $TaskName"

# 删除旧任务
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[*] 删除已有任务..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 登录触发 + 最高权限（内存扫描需要）
$action = New-ScheduledTaskAction -Execute $DaemonBat -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "微信登录后自动同步聊天记录 (wechat-reader watchdog)"

Write-Host ""
Write-Host "[+] 任务计划已创建！" -ForegroundColor Green
Write-Host ""
Write-Host "  触发条件: 用户登录时自动启动"
Write-Host "  运行权限: 最高权限（管理员）"
Write-Host "  守护进程: $DaemonBat"
Write-Host ""
Write-Host "  手动启动: schtasks /run /tn $TaskName"
Write-Host "  查看状态: Get-ScheduledTask -TaskName $TaskName"
Write-Host "  删除任务: Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host ""
Write-Host "  日志文件: $ProjectRoot\output\daemon.log"
Write-Host ""
Write-Host "使用方式: 配置完成后，每次登录 Windows 并打开微信即可，无需手动操作。"
