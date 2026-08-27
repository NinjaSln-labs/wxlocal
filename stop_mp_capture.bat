@echo off
cd /d "%~dp0"
taskkill /IM mitmdump.exe /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8848" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
echo [ok] mp-capture stop attempted (port 8848 / mitmdump)
