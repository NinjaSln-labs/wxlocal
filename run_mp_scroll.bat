@echo off
cd /d "%~dp0"
wscript //nologo "%~dp0launchers\win\run_daemon.vbs" bootstrap_mp_watch.py mp-scroll
