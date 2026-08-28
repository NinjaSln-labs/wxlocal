@echo off
cd /d "%~dp0"
start "mp-capture" /min cmd /c "cd /d "%~dp0" && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe scripts\ops\run_mp_capture.py >> output\mp_capture.log 2>&1"
