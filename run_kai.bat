@echo off
cd /d "%~dp0"
echo K//AI Companion - Starting...
echo.

REM Kill anything on port 5555
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5555"') do taskkill /F /PID %%a >nul 2>&1

REM Wait for port to free
timeout /t 2 /nobreak >nul

REM Run Python directly (keeps window open)
python kai_web_ui.py

pause
