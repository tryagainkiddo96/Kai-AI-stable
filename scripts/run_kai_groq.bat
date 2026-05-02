@echo off
REM Kai GROQ Launcher - Pre-configured to use GROQ API
echo ========================================
echo     KAI AI COMPANION - GROQ Cloud Mode
echo ========================================
echo.

cd /d "%~dp0.."

set PYTHONPATH=%~dp0..
set KAI_PROVIDER=groq
set KAI_MODEL=llama-3.1-8b-instant

echo Provider: %KAI_PROVIDER%
echo Model: %KAI_MODEL%
echo.
echo NOTE: Set GROQ_API_KEY environment variable before running
echo.

python kai_dashboard.py

echo.
echo Kai session ended.
pause

