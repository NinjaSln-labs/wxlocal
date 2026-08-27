@echo off
cd /d "%~dp0"
powershell -WindowStyle Hidden -NoProfile -Command "$patterns = @('*bootstrap_mp_watch*','*watch_mp_idb.py*'); foreach ($pat in $patterns) { Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like $pat } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }"
if exist "F:\ext\knowledge-base\wechat\mp-scroll\state\mp_idb_watch.pid" del /f /q "F:\ext\knowledge-base\wechat\mp-scroll\state\mp_idb_watch.pid"
if exist "%LOCALAPPDATA%\wxlocal\mp_idb_watch.pid" del /f /q "%LOCALAPPDATA%\wxlocal\mp_idb_watch.pid"
if exist "%LOCALAPPDATA%\wechat-reader\mp_idb_watch.pid" del /f /q "%LOCALAPPDATA%\wechat-reader\mp_idb_watch.pid"
echo [ok] mp-idb-watch stop attempted
