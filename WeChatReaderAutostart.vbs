' Deprecated — use WxLocalAutostart.vbs
CreateObject("WScript.Shell").Run "wscript //nologo """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\WxLocalAutostart.vbs""", 0, False
