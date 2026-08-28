' Login autostart — mp-scroll + chat-watch (wxlocal)
Option Explicit

Dim fso, root, pyw, sh, launchLog, ts
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = ResolveProjectRoot(fso)
pyw = ResolvePythonw(fso, root, sh)
launchLog = root & "\output\autostart_launch.log"

Function ResolveProjectRoot(fso)
    Dim rootFile, scriptDir, legacyFile
    scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
    rootFile = fso.BuildPath(scriptDir, "wxlocal.path")
    legacyFile = fso.BuildPath(scriptDir, "wechat-reader.path")
    If fso.FileExists(rootFile) Then
        Dim tsRoot
        Set tsRoot = fso.OpenTextFile(rootFile, 1)
        ResolveProjectRoot = Trim(tsRoot.ReadAll())
        tsRoot.Close
    ElseIf fso.FileExists(legacyFile) Then
        Set tsRoot = fso.OpenTextFile(legacyFile, 1)
        ResolveProjectRoot = Trim(tsRoot.ReadAll())
        tsRoot.Close
    Else
        ResolveProjectRoot = scriptDir
    End If
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
