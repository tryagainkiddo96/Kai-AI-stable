@echo off
setlocal
cd /d "%~dp0"
echo Launching Kai terminal runtime...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch_kai_latest.ps1"
