@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\wxlocal-web.exe" (
    ".venv\Scripts\wxlocal-web.exe" --host 127.0.0.1 --port 8787
) else (
    ".venv\Scripts\python.exe" -m wxlocal.web.app --host 127.0.0.1 --port 8787
)
