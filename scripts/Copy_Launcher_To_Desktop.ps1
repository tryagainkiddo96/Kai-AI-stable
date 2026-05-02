<#
Copy a fresh Kai Control Center launcher to the user's Desktop.
This creates Kai_Control_Center.bat on the Desktop that launches the CLI panel
with sensible defaults. Safe, quick-start for end users.
#>
param()

$desktop = [Environment]::GetFolderPath('Desktop')
$launcherName = 'Kai_Control_Center.bat'
$batchPath = Join-Path -Path $desktop -ChildPath $launcherName

if (Test-Path $batchPath) {
    Write-Host "[Kai Desktop Launcher] Launcher already exists at $batchPath" -ForegroundColor Yellow
} else {
    $content = @"@echo off
set MODEL=sam860/dolphin3-llama3.2:3b
set WORKSPACE=%USERPROFILE%\OneDrive\Desktop\Kai-AI
python "%USERPROFILE%\OneDrive\Desktop\Kai-AI\kai_control_panel.py" --model "%MODEL%" --workspace "%WORKSPACE%"
"@
    $content | Set-Content -Path $batchPath -Encoding UTF8
    Write-Host "[Kai Desktop Launcher] Created launcher at $batchPath" -ForegroundColor Green
}
