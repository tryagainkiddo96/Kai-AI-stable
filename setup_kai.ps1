# Kai AI One-Click Setup
# Run this in PowerShell: powershell -ExecutionPolicy Bypass -File setup_kai.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = "$env:USERPROFILE\OneDrive\Desktop"
if (-not (Test-Path $Desktop)) {
    $Desktop = "$env:USERPROFILE\Desktop"
}
$DesktopLauncher = Join-Path $Desktop "Start-Kai.vbs"
$RepoLauncher = Join-Path $RepoRoot "kai_launcher.vbs"
$WidgetLauncher = Join-Path $RepoRoot "tools\launch_kai_latest.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Kai AI - Runtime Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $WidgetLauncher)) {
    throw "Missing canonical launcher: $WidgetLauncher"
}

Write-Host "[1/4] Verifying local Python environment..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $RepoRoot ".venv"))) {
    python -m venv (Join-Path $RepoRoot ".venv")
}

& (Join-Path $RepoRoot ".venv\Scripts\Activate.ps1")

Write-Host ""
Write-Host "[2/4] Installing runtime dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
if (Test-Path (Join-Path $RepoRoot "requirements.txt")) {
    pip install -r (Join-Path $RepoRoot "requirements.txt") --quiet
}
pip install playwright --quiet
playwright install chromium

Write-Host ""
Write-Host "[3/4] Refreshing quiet launcher..." -ForegroundColor Yellow
$desktopVbs = @"
Option Explicit

Dim objShell, repoLauncher

Set objShell = CreateObject("WScript.Shell")
repoLauncher = "$($RepoLauncher.Replace('\', '\\'))"
objShell.Run "wscript.exe """ & repoLauncher & """", 0, False
"@
$desktopVbs | Out-File -FilePath $DesktopLauncher -Encoding ASCII

Write-Host ""
Write-Host "[4/4] Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Canonical repo launcher: run-kai.bat" -ForegroundColor White
Write-Host "Canonical PowerShell launcher: tools\launch_kai_latest.ps1" -ForegroundColor White
Write-Host "Quiet desktop launcher: $DesktopLauncher" -ForegroundColor White
Write-Host "Repo root: $RepoRoot" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to launch Kai now"
& $WidgetLauncher
