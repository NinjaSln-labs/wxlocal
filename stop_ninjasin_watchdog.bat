@echo off
cd /d "%~dp0"
powershell -WindowStyle Hidden -NoProfile -Command "$patterns = @('*bootstrap_ninjasin_watch*','*watchdog.py*'); foreach ($pat in $patterns) { Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like $pat } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }"
if exist "F:\ext\knowledge-base\wechat\ninjasin\state\ninjasin_watch.pid" del /f /q "F:\ext\knowledge-base\wechat\ninjasin\state\ninjasin_watch.pid"
echo [ok] ninjasin-watch stop attempted
