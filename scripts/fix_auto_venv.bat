@echo off
title Fix Terminal Auto-Venv Activation
echo ========================================
echo   FIX TERMINAL AUTO-VENV ACTIVATION
echo ========================================
echo.
echo This fixes the broken auto-activation
echo that prefixes every command with venv path.
echo.

echo [1/3] Backing up shell configs...

wsl -d kali -u root -- cp /home/tryagain/.bashrc /home/tryagain/.bashrc.bak 2>nul
wsl -d kali -u root -- cp /home/tryagain/.profile /home/tryagain/.profile.bak 2>nul
wsl -d kali -u root -- cp /home/tryagain/.bash_profile /home/tryagain/.bash_profile.bak 2>nul

echo [2/3] Removing venv auto-activation from shell configs...

REM Use sed to remove lines containing auto-activation patterns
wsl -d kali -u root -- sed -i '/\.venv.*activate/d' /home/tryagain/.bashrc 2>nul
wsl -d kali -u root -- sed -i '/source.*venv/d' /home/tryagain/.bashrc 2>nul
wsl -d kali -u root -- sed -i '/kai fix/d' /home/tryagain/.bashrc 2>nul
wsl -d kali -u root -- sed -i '/\.venv.*activate/d' /home/tryagain/.profile 2>nul
wsl -d kali -u root -- sed -i '/source.*venv/d' /home/tryagain/.profile 2>nul
wsl -d kali -u root -- sed -i '/\.venv.*activate/d' /home/tryagain/.bash_profile 2>nul
wsl -d kali -u root -- sed -i '/source.*venv/d' /home/tryagain/.bash_profile 2>nul

echo [3/3] Killing broken VS Code: terminal integrations...

REM Kill any python processes that might be injecting terminal commands
taskkill /f /im python.exe /fi "MEMUSAGE gt 50000" 2>nul
taskkill /f /fi "IMAGENAME eq Code.exe" /fi "MEMUSAGE gt 900000" 2>nul

echo.
echo ========================================
echo   FIX COMPLETE
echo ========================================
echo.
echo Please CLOSE and REOPEN VS Code: terminal.
echo.
echo If issue persists, run VS Code: command:
echo   Developer: Reload Window
echo.
pause

