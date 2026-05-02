@echo off
REM Kai DeepSeek Launcher
echo ========================================
echo   KAI AI COMPANION - DeepSeek Mode
echo ========================================
echo.

cd /d "%~dp0.."

set PYTHONPATH=%~dp0..
set KAI_PROVIDER=deepseek
set KAI_MODEL=deepseek-chat
set KAI_TEMPERATURE=0.3

echo Provider: %KAI_PROVIDER%
echo Model: %KAI_MODEL%
echo.

python kai_dashboard.py

echo.
echo Kai session ended.
pause

