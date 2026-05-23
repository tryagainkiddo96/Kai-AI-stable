@echo off
REM ========================================
REM K//AI COMPANION — LAUNCHER
REM Double-click to start Kai in browser
REM ========================================

cd /d "%~dp0"

title K//AI Companion

echo.
echo  K//AI COMPANION
echo  Black & Tan Shiba Inu — JARVIS-Class AI
echo  ================================================
echo.
echo  Starting server and opening browser...
echo  (Close this window or press Ctrl+C to stop)
echo.

python kai_web_ui.py

echo.
echo  Server stopped.
pause
