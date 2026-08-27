# 配置登录后自动启动（mp-scroll + chat-watch）
#
#   .\setup_wxlocal_autostart.bat          ← 推荐（绕过 ExecutionPolicy）
#   .\setup_wxlocal_autostart.ps1 -Uninstall

param(
    [ValidateSet("Startup", "Task")]
    [string]$Mode = "Startup",
    [switch]$Uninstall,
    [string]$ProjectRoot = "",
    [string]$TaskName = "WxLocalAutostart"
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = $PSScriptRoot
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

$AutostartVbs = Join-Path $ProjectRoot "WxLocalAutostart.vbs"
$StartupFolder = [Environment]::GetFolderPath("Startup")
$StartupLink = Join-Path $StartupFolder "WxLocalAutostart.vbs"
$StartupRootFile = Join-Path $StartupFolder "wxlocal.path"
$LegacyVbs = Join-Path $StartupFolder "WeChatReaderAutostart.vbs"
$LegacyRootFile = Join-Path $StartupFolder "wechat-reader.path"
$LegacyStartupBat = Join-Path $StartupFolder "WeChatReaderAutostart.bat"
$LegacyStartupOld = Join-Path $StartupFolder "WeChatMpIdbWatch.bat"

function Write-Info($msg) { Write-Host "[*] $msg" }
function Write-Ok($msg) { Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }

if (-not (Test-Path $AutostartVbs)) {
    Write-Warn "未找到 WxLocalAutostart.vbs: $AutostartVbs"
    exit 1
}

if ($Uninstall) {
    foreach ($p in @($StartupLink, $StartupRootFile, $LegacyVbs, $LegacyRootFile, $LegacyStartupBat, $LegacyStartupOld)) {
        if (Test-Path $p) {
            Remove-Item $p -Force
            Write-Ok "已删除: $p"
        }
    }
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Ok "已删除计划任务: $TaskName"
    }
    foreach ($legacyTask in @("WeChatReaderAutostart", "WeChatReaderDaemon")) {
        $t = Get-ScheduledTask -TaskName $legacyTask -ErrorAction SilentlyContinue
        if ($t) {
            Unregister-ScheduledTask -TaskName $legacyTask -Confirm:$false
            Write-Ok "已删除旧任务: $legacyTask"
        }
    }
    exit 0
}

Write-Info "wxlocal 目录: $ProjectRoot"

if ($Mode -eq "Startup") {
    Copy-Item -Path $AutostartVbs -Destination $StartupLink -Force
    Set-Content -Path $StartupRootFile -Value $ProjectRoot -Encoding ASCII -NoNewline
    foreach ($p in @($LegacyVbs, $LegacyRootFile, $LegacyStartupBat, $LegacyStartupOld)) {
        if (Test-Path $p) { Remove-Item $p -Force }
    }
    Write-Ok "已写入登录启动项 WxLocalAutostart.vbs"
    Write-Host ""
    Write-Host "  启动项:   $StartupLink"
    Write-Host "  路径文件: $StartupRootFile"
    Write-Host "  卸载:     .\setup_wxlocal_autostart.ps1 -Uninstall"
    Write-Host "  状态:     .\status_wxlocal.bat"
    exit 0
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Warn "任务计划模式需要管理员"
    exit 1
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }

Set-Content -Path $StartupRootFile -Value $ProjectRoot -Encoding ASCII -NoNewline
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//nologo `"$AutostartVbs`"" -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "wxlocal autostart: mp-scroll + chat-watch"
Write-Ok "任务计划已创建: $TaskName"
