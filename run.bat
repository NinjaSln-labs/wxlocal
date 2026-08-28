@echo off
:: 以管理员身份运行 Python 微信聊天记录读取工具
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
if exist ".venv\Scripts\wxlocal-export.exe" (
    ".venv\Scripts\wxlocal-export.exe" %*
) else (
    ".venv\Scripts\python.exe" -m wxlocal.export.cli %*
)
pause
