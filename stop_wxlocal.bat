@echo off
cd /d "%~dp0"
.\.venv\Scripts\python.exe scripts\daemon_status.py stop all
echo [ok] wxlocal background tasks stop attempted