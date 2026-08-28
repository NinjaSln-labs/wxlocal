@echo off
cd /d "%~dp0"
echo === mp-scroll status ===
echo.
.\.venv\Scripts\python.exe scripts\daemon_status.py mp-scroll
echo --- last 5 lines (run log) ---
powershell -NoProfile -Command "if (Test-Path 'output\mp_scroll.log') { Get-Content 'output\mp_scroll.log' -Tail 5 } elseif (Test-Path 'output\mp_idb_watch.log') { Get-Content 'output\mp_idb_watch.log' -Tail 5 } else { Write-Host '(no log)' }"
