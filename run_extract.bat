@echo off
:: 微信 4.1.13 一键提取密钥 + 解密 + 导出
:: 需管理员权限提取密钥；微信需已登录

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
set DB_DIR=D:\app\WeixinData\xwechat_files\sndddepdc_who_29ad\db_storage
set PY=E:\Python312\python.exe
set VPY=.venv\Scripts\python.exe

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
echo     数据库: decrypted\
echo     聊天记录: output\messages.json
echo     Web 查看: http://127.0.0.1:8787
pause
