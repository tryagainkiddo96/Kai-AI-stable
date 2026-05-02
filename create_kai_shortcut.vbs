Dim objShell, objFSO, desktopPath, shortcut

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

desktopPath = objShell.SpecialFolders("Desktop")

Set shortcut = objShell.CreateShortcut(desktopPath & "\Launch Kai AI.lnk")
shortcut.TargetPath = "c:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI\Start-Kai.vbs"
shortcut.WindowStyle = 1
shortcut.IconLocation = "c:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI\KaiUnified.spec"
shortcut.Description = "Launch Kai AI Companion"
shortcut.WorkingDirectory = "c:\Users\7nujy6xc\OneDrive\Desktop\Kai-AI"
shortcut.Save

WScript.Echo "Shortcut created on desktop: Launch Kai AI.lnk"

Set shortcut = Nothing
Set objShell = Nothing
Set objFSO = Nothing