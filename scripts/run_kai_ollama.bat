@echo off
REM Kai Ollama Launcher - Local models
echo ========================================
echo   KAI AI COMPANION - Ollama Mode
echo ========================================
echo.

cd /d "%~dp0.."

set PYTHONPATH=%~dp0..
set KAI_MODEL=llama3.2:3b

echo Model: %KAI_MODEL%
echo.

python kai_dashboard.py --provider ollama --model %KAI_MODEL%

echo.
echo Kai session ended.
pause

