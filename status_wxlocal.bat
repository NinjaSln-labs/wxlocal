@echo off
cd /d "%~dp0"
echo === wxlocal autostart status ===
echo.
echo --- mp-scroll (IndexedDB watch) ---
call status_mp_idb_watch.bat
echo.
echo --- chat-watch (contact export) ---
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*watchdog.py*' -or $_.CommandLine -like '*bootstrap_ninjasin*' }; if ($p) { $p | Select-Object ProcessId, @{N='Started';E={$_.CreationDate}} | Format-Table -AutoSize } else { Write-Host 'process: not running' }"
echo.
echo repo: %CD%
echo docs: https://github.com/ninjasin-labs/wxlocal
