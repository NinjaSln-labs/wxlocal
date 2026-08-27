@echo off
cd /d "%~dp0"
echo === mp-idb-watch status ===
echo.

set "PID_FILE=F:\ext\knowledge-base\wechat\mp-scroll\state\mp_idb_watch.pid"
if exist "%PID_FILE%" (
    echo pid file: %PID_FILE%
    type "%PID_FILE%"
) else (
    echo pid file: not found
)
echo.

powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*watch_mp_idb.py*' }; if ($p) { $p | Select-Object ProcessId, @{N='Started';E={$_.CreationDate}} | Format-Table -AutoSize } else { Write-Host 'process: not running' }"

echo.
echo --- last 5 lines (run log) ---
powershell -NoProfile -Command "if (Test-Path 'output\mp_idb_watch.log') { Get-Content 'output\mp_idb_watch.log' -Tail 5 } else { Write-Host '(no log)' }"

echo.
echo --- last 5 lines (errors) ---
powershell -NoProfile -Command "if (Test-Path 'F:\ext\knowledge-base\wechat\mp-scroll\state\mp_idb_watch_errors.log') { Get-Content 'F:\ext\knowledge-base\wechat\mp-scroll\state\mp_idb_watch_errors.log' -Tail 5 } else { Write-Host '(no errors yet)' }"

echo.
echo --- last 5 lines (launch) ---
powershell -NoProfile -Command "if (Test-Path 'F:\ext\knowledge-base\wechat\mp-scroll\state\launch.log') { Get-Content 'F:\ext\knowledge-base\wechat\mp-scroll\state\launch.log' -Tail 5 } else { Write-Host '(no launch log yet)' }"
