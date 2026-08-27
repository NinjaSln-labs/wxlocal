@echo off
cd /d "%~dp0"
echo [*] 启动微信聊天记录 Web 服务...
echo [*] 地址: http://127.0.0.1:8787
echo.
".venv\Scripts\python.exe" app.py --host 127.0.0.1 --port 8787
pause
