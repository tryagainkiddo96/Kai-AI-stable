Option Explicit

Dim objShell, objFSO, strKaiPath, psScript, strCommand

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strKaiPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
psScript = strKaiPath & "\tools\launch_kai_latest.ps1"
strCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """"

objShell.Run strCommand, 1, True
