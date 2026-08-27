@echo off
:: 微信 4.1.13 一键提取密钥 + 解密 + 导出
:: 需管理员权限提取密钥；微信需已登录
:: 配置：复制 .env.example -> .env，设置 WECHAT_DATA_ROOT

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
set VPY=.venv\Scripts\python.exe
if not exist "%VPY%" (
    echo [!] 未找到虚拟环境: %VPY%
    pause
    exit /b 1
)

for /f "delims=" %%i in ('"%VPY%" scripts\print_env.py WXLOCAL_PYTHON') do set PY=%%i
if not defined PY set PY=%VPY%

for /f "delims=" %%i in ('"%VPY%" scripts\resolve_db_storage.py') do set DB_DIR=%%i
if not defined DB_DIR (
    echo [!] 未找到 db_storage。请在 .env 设置 WECHAT_DATA_ROOT 并确保微信已登录。
    pause
    exit /b 1
)

echo [*] db_storage: %DB_DIR%
echo [*] python:     %PY%
echo.

echo [*] 1/3 提取密钥...
"%PY%" vendor\wcdb-key-tool-main\wcdb_key_tool_windows.py extract --db-dir "%DB_DIR%" --output output\all_keys.json
if %errorlevel% neq 0 (
    echo [!] 密钥提取失败。请确保微信已登录，或退出后重新登录再试。
    pause
    exit /b 1
)

echo [*] 2/3 解密数据库...
"%PY%" vendor\wcdb-key-tool-main\wcdb_key_tool_windows.py decrypt --keys output\all_keys.json --output output\decrypted

echo [*] 3/3 导出聊天记录...
"%VPY%" export_messages.py

echo.
echo [+] 完成！
echo     密钥: output\all_keys.json
echo     数据库: output\decrypted\
echo     聊天记录: output\messages.json
echo     Web 查看: http://127.0.0.1:8787
pause
