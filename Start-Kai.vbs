Option Explicit

Dim objShell, objFSO, desktopDir, launcherPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

desktopDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
launcherPath = desktopDir & "\Kai-AI\kai_launcher.vbs"

objShell.Run "wscript.exe """ & launcherPath & """", 0, False
