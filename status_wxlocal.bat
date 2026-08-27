@echo off
cd /d "%~dp0"
echo === wxlocal autostart status ===
echo.
.\.venv\Scripts\python.exe scripts\daemon_status.py
echo docs: https://github.com/NinjaSln-labs/wxlocal
