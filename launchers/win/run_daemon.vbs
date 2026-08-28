' Silent launcher for a wxlocal bootstrap script.
' Usage: wscript //nologo run_daemon.vbs <bootstrap.py> [log-tag]
Option Explicit

Dim fso, root, pyw, sh, launchLog, ts, bootstrapScript, logTag
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

If WScript.Arguments.Count < 1 Then
    WScript.Echo "usage: run_daemon.vbs bootstrap_script.py [log-tag]"
    WScript.Quit 1
End If

bootstrapScript = WScript.Arguments(0)
If WScript.Arguments.Count >= 2 Then
    logTag = WScript.Arguments(1)
Else
    logTag = "daemon"
End If

root = ResolveProjectRoot(fso)
pyw = ResolvePythonw(fso, root, sh)
launchLog = root & "\output\autostart_launch.log"

Function ResolveProjectRoot(fso)
    Dim scriptDir, repoRoot, rootFile, legacyFile, startupRootFile
    scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
    repoRoot = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
    rootFile = fso.BuildPath(repoRoot, "wxlocal.path")
    legacyFile = fso.BuildPath(repoRoot, "wechat-reader.path")
    startupRootFile = fso.BuildPath(WScript.CreateObject("WScript.Shell").SpecialFolders("Startup"), "wxlocal.path")
    If fso.FileExists(startupRootFile) Then
        Dim tsStartup
        Set tsStartup = fso.OpenTextFile(startupRootFile, 1)
        ResolveProjectRoot = Trim(tsStartup.ReadAll())
        tsStartup.Close
        Exit Function
    End If
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

If Not fso.FileExists(root & "\" & bootstrapScript) Then
    AppendLaunchLog "ERROR bootstrap missing: " & root & "\" & bootstrapScript
    WScript.Quit 1
End If

sh.CurrentDirectory = root
sh.Environment("Process")("PYTHONIOENCODING") = "utf-8"
AppendLaunchLog "starting " & bootstrapScript & " via " & pyw & " root=" & root
sh.Run """" & pyw & """ """ & root & "\" & bootstrapScript & """", 0, False
