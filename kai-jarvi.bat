@echo off
REM ========================================
REM K//AI COMPANION LAUNCHER
REM Opens Kai — JARVIS-class AI partner in browser
REM ========================================

cd /d "%~dp0"

echo.
echo ================================================
echo   K//AI COMPANION
echo   Black & Tan Shiba Inu — JARVIS-Class AI
echo ================================================
echo.
echo Starting Kai...
echo Open http://localhost:5555 in your browser
echo.

python kai_web_ui.py

echo.
echo Kai session ended.
pause