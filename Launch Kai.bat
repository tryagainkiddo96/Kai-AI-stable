@echo off
REM==============================================================================
REM KAI LAUNCHER - Beautiful Terminal UI
REM Double-click to launch Kai AI Dashboard
REM==============================================================================

cd /d "%~dp0"

echo ╔═══════════════════════════════════════════════════════════╗
echo ║              KAI AI LAUNCHER                              ║
echo ║         Beautiful Terminal UI for Kai AI               ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Starting Kai Dashboard...
echo.

python kai_dashboard.py

echo.
echo Kai session ended.
pause
