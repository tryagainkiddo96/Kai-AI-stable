@echo off
set MODEL=%1
set WORKSPACE=%2
if "%MODEL%"=="" set MODEL=sam860/dolphin3-llama3.2:3b
if "%WORKSPACE%"=="" set WORKSPACE=%USERPROFILE%\Kai-AI
echo [Kai] Opening Kai in a new window...
start "Kai" cmd /k "cd /d %WORKSPACE% & python -m kai_agent.assistant --model %MODEL% --workspace %WORKSPACE%"
