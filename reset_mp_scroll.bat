@echo off
cd /d "%~dp0"
call stop_mp_idb_watch.bat
echo.
echo Reset mp-scroll (%*)
.venv\Scripts\python.exe reset_mp_scroll.py %*
echo.
echo Restart watch: run_mp_scroll.bat
