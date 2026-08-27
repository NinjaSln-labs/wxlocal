@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist output mkdir output
echo [*] starting mitm on 8848, log: output\mp_capture.log
echo [*] stop: stop_mp_capture.bat
start "mp-capture" /min cmd /c "cd /d "%~dp0" && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe run_mp_capture.py >> output\mp_capture.log 2>&1"
