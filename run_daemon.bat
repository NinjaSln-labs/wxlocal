@echo off
:: 后台守护进程（无窗口）— 请用 run_ninjasin_watchdog.bat / .vbs
cd /d "%~dp0"
wscript //nologo "%~dp0run_ninjasin_watchdog.vbs"
