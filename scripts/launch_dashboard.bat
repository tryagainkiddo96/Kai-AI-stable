@echo off
REM Kai Dashboard Launcher
REM Beautiful terminal UI for Kai AI

cd /d "%~dp0"

echo ========================================
echo   KAI DASHBOARD
echo   Beautiful Terminal UI
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

REM Check if rich is installed
python -c "import rich" >nul 2>&1
if errorlevel 1 (
    echo Installing rich library...
    pip install rich>=13.0.0
)

echo Starting Kai Dashboard...
echo.

REM Default: start with dashboard
python "%~dp0..\kai_dashboard.py" %*

pause

