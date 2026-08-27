@echo off
cd /d "%~dp0"
call stop_mp_idb_watch.bat
echo.
echo Reset mp-scroll (%*)
.venv\Scripts\python.exe reset_mp_scroll.py %*
echo.
echo Restart watch: wscript //nologo run_mp_idb_watch.vbs
