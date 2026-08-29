' Silent launcher for a wxlocal bootstrap module.
' Usage: wscript //nologo run_daemon.vbs <module.name> [log-tag]
Option Explicit

Dim fso, root, pyw, sh, launchLog, ts, moduleName, logTag, modulePath
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

If WScript.Arguments.Count < 1 Then
    WScript.Echo "usage: run_daemon.vbs module.name [log-tag]"
    WScript.Quit 1
End If

moduleName = WScript.Arguments(0)
If WScript.Arguments.Count >= 2 Then
    logTag = WScript.Arguments(1)
Else
    logTag = "daemon"
End If

root = ResolveProjectRoot(fso)
pyw = ResolvePythonw(fso, root, sh)
launchLog = root & "\output\autostart_launch.log"
modulePath = root & "\" & Replace(moduleName, ".", "\") & ".py"

Function ResolveProjectRoot(fso)
    Dim scriptDir, repoRoot, rootFile, legacyFile, localRoot, shLocal, startupLegacy
    Set shLocal = CreateObject("WScript.Shell")
    scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
    repoRoot = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
    ' Preferred: %LOCALAPPDATA%\wxlocal\install_root.txt (never put this in Startup)
    localRoot = shLocal.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\wxlocal\install_root.txt"
    If fso.FileExists(localRoot) Then
        Dim tsLocal
        Set tsLocal = fso.OpenTextFile(localRoot, 1)
        ResolveProjectRoot = Trim(tsLocal.ReadAll())
        tsLocal.Close
        Exit Function
    End If
    rootFile = fso.BuildPath(repoRoot, "wxlocal.path")
    legacyFile = fso.BuildPath(repoRoot, "wechat-reader.path")
    startupLegacy = shLocal.SpecialFolders("Startup") & "\wxlocal.path"
    If fso.FileExists(rootFile) Then
        Dim tsRoot
        Set tsRoot = fso.OpenTextFile(rootFile, 1)
        ResolveProjectRoot = Trim(tsRoot.ReadAll())
        tsRoot.Close
    ElseIf fso.FileExists(legacyFile) Then
        Set tsRoot = fso.OpenTextFile(legacyFile, 1)
        ResolveProjectRoot = Trim(tsRoot.ReadAll())
        tsRoot.Close
    ElseIf fso.FileExists(startupLegacy) Then
        Dim tsStartup
        Set tsStartup = fso.OpenTextFile(startupLegacy, 1)
        ResolveProjectRoot = Trim(tsStartup.ReadAll())
        tsStartup.Close
    Else
        ResolveProjectRoot = repoRoot
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
    ts.WriteLine Now & " [" & logTag & "] " & msg
    ts.Close
End Sub

If Not fso.FileExists(pyw) And pyw <> "pythonw.exe" Then
    AppendLaunchLog "ERROR pythonw missing: " & pyw
    WScript.Quit 1
End If

If Not fso.FileExists(modulePath) Then
    AppendLaunchLog "ERROR bootstrap module missing: " & modulePath
    WScript.Quit 1
End If

sh.CurrentDirectory = root
sh.Environment("Process")("PYTHONIOENCODING") = "utf-8"
AppendLaunchLog "starting -m " & moduleName & " via " & pyw & " root=" & root
sh.Run """" & pyw & """ -m " & moduleName, 0, False
