' Login autostart — mp-scroll + chat-watch (wxlocal)
' Startup folder must only contain this .vbs (never a .path sidecar — Windows tries to open it).
Option Explicit

Dim fso, root, pyw, sh, launchLog, ts
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = ResolveProjectRoot(fso, sh)
pyw = ResolvePythonw(fso, root, sh)
launchLog = root & "\output\autostart_launch.log"

Function ResolveProjectRoot(fso, sh)
    Dim rootFile, legacyFile, localRoot, startupLegacy
    ' Preferred: %LOCALAPPDATA%\wxlocal\install_root.txt (not in Startup)
    localRoot = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\wxlocal\install_root.txt"
    If fso.FileExists(localRoot) Then
        ResolveProjectRoot = Trim(ReadAllText(fso, localRoot))
        Exit Function
    End If
    ' Repo-local pointer (optional)
    rootFile = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "wxlocal.path")
    ' When VBS lives in Startup, parent is Startup — skip non-vbs there; try known default
    If Right(LCase(rootFile), 15) = "\wxlocal.path" And InStr(1, LCase(rootFile), "\startup\", vbTextCompare) > 0 Then
        rootFile = ""
    End If
    If rootFile <> "" And fso.FileExists(rootFile) Then
        ResolveProjectRoot = Trim(ReadAllText(fso, rootFile))
        Exit Function
    End If
    ' Migrate: old Startup\wxlocal.path still readable once, then prefer AppData next install
    startupLegacy = sh.SpecialFolders("Startup") & "\wxlocal.path"
    If fso.FileExists(startupLegacy) Then
        ResolveProjectRoot = Trim(ReadAllText(fso, startupLegacy))
        Exit Function
    End If
    legacyFile = sh.SpecialFolders("Startup") & "\wechat-reader.path"
    If fso.FileExists(legacyFile) Then
        ResolveProjectRoot = Trim(ReadAllText(fso, legacyFile))
        Exit Function
    End If
    ResolveProjectRoot = fso.GetParentFolderName(WScript.ScriptFullName)
End Function

Function ReadAllText(fso, path)
    Dim ts
    Set ts = fso.OpenTextFile(path, 1)
    ReadAllText = ts.ReadAll()
    ts.Close
End Function

Function ResolvePythonw(fso, root, sh)
    Dim candidate
    candidate = sh.ExpandEnvironmentStrings("%WXLOCAL_PYTHON%")
    If candidate <> "" And candidate <> "%WXLOCAL_PYTHON%" And fso.FileExists(candidate) Then
        ResolvePythonw = candidate
        Exit Function
    End If
    candidate = sh.ExpandEnvironmentStrings("%WECHAT_READER_PYTHON%")
    If candidate <> "" And candidate <> "%WECHAT_READER_PYTHON%" And fso.FileExists(candidate) Then
        ResolvePythonw = candidate
        Exit Function
    End If
    candidate = root & "\.venv\Scripts\pythonw.exe"
    If fso.FileExists(candidate) Then
        ResolvePythonw = candidate
        Exit Function
    End If
    ResolvePythonw = "pythonw.exe"
End Function

Sub AppendLaunchLog(msg)
    On Error Resume Next
    Dim folder
    folder = fso.GetParentFolderName(launchLog)
    If Not fso.FolderExists(folder) Then
        fso.CreateFolder folder
    End If
    Set ts = fso.OpenTextFile(launchLog, 8, True)
    ts.WriteLine Now & " [autostart] " & msg
    ts.Close
End Sub

If Not fso.FileExists(pyw) And pyw <> "pythonw.exe" Then
    AppendLaunchLog "ERROR pythonw missing: " & pyw
    WScript.Quit 1
End If

sh.CurrentDirectory = root
sh.Environment("Process")("PYTHONIOENCODING") = "utf-8"
AppendLaunchLog "starting -m wxlocal.ops.bootstrap_autostart via " & pyw & " root=" & root
sh.Run """" & pyw & """ -m wxlocal.ops.bootstrap_autostart", 0, False
