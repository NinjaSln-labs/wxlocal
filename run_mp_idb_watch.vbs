' Deprecated — use launchers\win\run_daemon.vbs
CreateObject("WScript.Shell").Run "wscript //nologo """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\launchers\win\run_daemon.vbs"" bootstrap_mp_watch.py mp-scroll", 0, False
