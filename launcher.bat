@echo off
REM Kai Launcher Menu - Clean and organized launcher for all Kai modes

echo.
echo ========================================
echo        KAI LAUNCHER MENU
echo ========================================
echo.
echo [1] Run Kai (Terminal Mode)
echo [2] Run Kai Pentester Mode
echo [3] Setup Kai
echo [4] Enterprise Mode
echo [5] Docker Tools
echo [6] Troubleshooting
echo [7] View Documentation
echo.
set /p choice="Choose option [1-7]: "
echo.

if "%choice%"=="1" (
    echo Starting Kai Terminal Mode...
    call run-kai.bat
) else if "%choice%"=="2" (
    echo Starting Kai Pentester Mode...
    python launch_kai_pentester.py
) else if "%choice%"=="3" (
    echo Running Kai Setup...
    call scripts\setup_kai.bat
) else if "%choice%"=="4" (
    echo Starting Kai Enterprise Mode...
    call scripts\run-enterprise.bat
) else if "%choice%"=="5" (
    goto docker_menu
) else if "%choice%"=="6" (
    goto troubleshoot_menu
) else if "%choice%"=="7" (
    goto docs_menu
) else (
    echo Invalid choice. Press any key to exit.
    pause >nul
    exit /b 1
)

goto :eof

:docker_menu
cls
echo.
echo ========================================
echo        DOCKER TOOLS
echo ========================================
echo.
echo [A] Reset Docker Services
echo [B] Back to main menu
echo.
set /p docker_choice="Choose [A-B]: "
echo.

if "%docker_choice%"=="A" (
    echo Running Docker reset...
    call scripts\docker_reset.bat
) else if "%docker_choice%"=="B" (
    goto start
) else (
    echo Invalid choice.
    goto docker_menu
)

:troubleshoot_menu
cls
echo.
echo ========================================
echo      TROUBLESHOOTING TOOLS
echo ========================================
echo.
echo [A] Kill High CPU Processes
echo [B] Back to main menu
echo.
set /p trouble_choice="Choose [A-B]: "
echo.

if "%trouble_choice%"=="A" (
    echo Running high CPU killer...
    call scripts\high_cpu_killer.bat
) else if "%trouble_choice%"=="B" (
    goto start
) else (
    echo Invalid choice.
    goto troubleshoot_menu
)

:docs_menu
cls
echo.
echo ========================================
echo       KAI DOCUMENTATION
echo ========================================
echo.
echo Available docs in docs\ folder:
echo.
dir /b docs\*.md
echo.
echo Press any key to return to main menu...
pause >nul
goto start

:start
goto :eof