@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe scripts\ops\reset_mp_scroll.py %*
