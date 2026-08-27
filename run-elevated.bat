@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Read-WeChatChats.ps1" %*
pause
