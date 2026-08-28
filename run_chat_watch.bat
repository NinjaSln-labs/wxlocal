@echo off
cd /d "%~dp0"
wscript //nologo "%~dp0launchers\win\run_daemon.vbs" bootstrap_ninjasin_watch.py chat-watch
