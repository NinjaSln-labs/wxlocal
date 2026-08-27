@echo off
rem Legacy wrapper — detach via VBS (no lingering cmd)
cd /d "%~dp0"
wscript //nologo "%~dp0run_ninjasin_watchdog.vbs"
exit /b 0
