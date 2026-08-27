@echo off
cd /d "%~dp0"
call stop_mp_idb_watch.bat
call stop_ninjasin_watchdog.bat
echo [ok] wxlocal background tasks stop attempted
