' Deprecated — use launchers\win\run_daemon.vbs
CreateObject("WScript.Shell").Run "wscript //nologo """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\launchers\win\run_daemon.vbs"" bootstrap_ninjasin_watch.py chat-watch", 0, False
