@echo off
cd /d "%~dp0"
title K//AI Companion

echo K//AI COMPANION - Starting...
echo.

REM Kill any leftover Python on port 5555
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5555"') do (
    if "%%a" NEQ "" (
        echo [Killing stale process %%a on port 5555]
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul

REM Launch Kai
start python kai_web_ui.py

REM Wait, then open browser
timeout /t 4 /nobreak >nul
start http://localhost:5555

echo.
echo Browser should open to http://localhost:5555
echo Close this window to stop the server.
echo.
pause
