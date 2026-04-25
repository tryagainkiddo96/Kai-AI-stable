@echo off
REM Kai Enterprise - Production-Grade AI Assistant

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ================================================
echo     KAI ENTERPRISE - Production AI Assistant
echo ================================================
echo.
echo Features:
echo   + Multi-LLM support (Ollama, OpenAI)
echo   + Plugin system (terminal, file, custom)
echo   + Vector memory database
echo   + Project management
echo   + REST API + WebSocket
echo   + FastAPI documentation
echo.

REM Check Docker
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not running
    pause
    exit /b 1
)

echo [*] Building containers...
docker compose -f docker-compose-enterprise.yml build

if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo [*] Starting Kai Enterprise...
docker compose -f docker-compose-enterprise.yml up -d

if errorlevel 1 (
    echo [ERROR] Startup failed
    pause
    exit /b 1
)

timeout /t 3 /nobreak

echo.
echo [SUCCESS] Kai Enterprise is running!
echo.
echo Access:
echo   CLI:    docker exec -it kai-cli bash
echo   API:    http://localhost:8001
echo   Docs:   http://localhost:8001/docs
echo   WS:     ws://localhost:8001/ws/chat
echo   Ollama: http://localhost:11434
echo.
echo Useful commands:
echo   docker compose -f docker-compose-enterprise.yml logs -f
echo   docker compose -f docker-compose-enterprise.yml down
echo   docker exec -it kai-api python -u kai_enterprise.py
echo.
pause
