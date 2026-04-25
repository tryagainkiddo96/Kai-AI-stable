@echo off
title Full Cleanup - Hung Processes + Terminal Fix
echo ========================================
echo   FULL SYSTEM CLEANUP
echo ========================================
echo.

echo STEP 1: Killing hung VS Code: processes...
powershell.exe -NoProfile -Command "Get-Process Code -ErrorAction SilentlyContinue | Where-Object { [string]::IsNullOrWhiteSpace($_.MainWindowTitle) } | ForEach-Object { Write-Host ('  Killing orphaned Code.exe PID ' + $_.Id) -ForegroundColor Red; Stop-Process -Id $_.Id -Force }"

echo.
echo STEP 2: Killing excess VS Code: processes...
powershell.exe -NoProfile -Command "$procs = Get-Process Code -ErrorAction SilentlyContinue | Sort-Object StartTime; $count = $procs.Count; if ($count -gt 6) { $toKill = $count - 6; foreach ($p in $procs) { if ($toKill -le 0) { break }; Write-Host ('  Killing excess Code.exe PID ' + $p.Id) -ForegroundColor Red; Stop-Process -Id $p.Id -Force; $toKill-- } } else { Write-Host ('  ' + $count + ' Code.exe processes - OK') -ForegroundColor Green }"

echo.
echo STEP 3: Killing stale python/node processes...
taskkill /f /fi "IMAGENAME eq python.exe" /fi "CPUTIME gt 01:00:00" 2>nul
taskkill /f /fi "IMAGENAME eq python3.exe" /fi "CPUTIME gt 01:00:00" 2>nul
taskkill /f /fi "IMAGENAME eq node.exe" /fi "CPUTIME gt 01:00:00" 2>nul

echo.
echo STEP 4: Fixing terminal auto-venv...
wsl -d kali -u root -- sed -i '/\.venv.*activate/d' /home/tryagain/.bashrc 2>nul
wsl -d kali -u root -- sed -i '/source.*venv/d' /home/tryagain/.bashrc 2>nul
wsl -d kali -u root -- sed -i '/kai fix/d' /home/tryagain/.bashrc 2>nul

echo.
echo ========================================
echo   CLEANUP COMPLETE
echo ========================================
echo.
echo Please CLOSE and REOPEN VS Code: terminal.
echo.
pause

