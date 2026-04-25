@echo off
title Hung Process Cleaner
echo ========================================
echo    HUNG PROCESS CLEANER
echo ========================================
echo.

setlocal EnableDelayedExpansion
set KILLED=0

REM Kill orphaned Code.exe (no window title) using PowerShell one-liner
echo [1/3] Killing orphaned VS Code: processes...
powershell.exe -NoProfile -Command "Get-Process Code -ErrorAction SilentlyContinue | Where-Object { [string]::IsNullOrWhiteSpace($_.MainWindowTitle) -and $_.Id -ne $PID } | ForEach-Object { Write-Host ('  Killing orphaned Code.exe PID ' + $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"

echo.
echo [2/3] Killing excess VS Code: processes (keeping 8 newest)...
powershell.exe -NoProfile -Command "$procs = Get-Process Code -ErrorAction SilentlyContinue | Sort-Object StartTime; $count = $procs.Count; if ($count -gt 8) { $toKill = $count - 8; foreach ($p in $procs) { if ($toKill -le 0) { break }; if ($p.Id -ne $PID) { Write-Host ('  Killing excess Code.exe PID ' + $p.Id); Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; $toKill-- } } } else { Write-Host ('  Only ' + $count + ' Code.exe found - within normal range') }"

echo.
echo [3/3] Killing stale python/node processes...
taskkill /f /fi "IMAGENAME eq python.exe" /fi "CPUTIME gt 01:00:00" 2>nul && echo Killed stale python.exe || echo No stale python.exe
taskkill /f /fi "IMAGENAME eq node.exe" /fi "CPUTIME gt 01:00:00" 2>nul && echo Killed stale node.exe || echo No stale node.exe

echo.
echo ========================================
echo    CLEANUP COMPLETE
echo ========================================
echo.
echo Press any key to exit.
pause >nul

