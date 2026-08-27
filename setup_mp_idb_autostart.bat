@echo off
REM Wrapper — avoids PowerShell ExecutionPolicy blocking .ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_mp_idb_autostart.ps1" %*
