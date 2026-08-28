@echo off
cd /d "%~dp0"
wscript //nologo "%~dp0launchers\win\run_daemon.vbs" wxlocal.pipelines.chat_watch.bootstrap chat-watch
