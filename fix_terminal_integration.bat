@echo off
REM Kai Terminal Integration Fix
REM This script helps resolve terminal integration issues

echo.
echo ========================================
echo   KAI TERMINAL INTEGRATION FIX
echo ========================================
echo.
echo This script helps resolve issues where Kai
echo interferes with normal terminal commands.
echo.

echo [1/3] Checking for PATH conflicts...
where python 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: Python not found in PATH
) else (
    echo Python found in PATH
)

where kai 2>nul
if %ERRORLEVEL% equ 0 (
    echo WARNING: 'kai' command exists - this might conflict
    where kai
)

echo.
echo [2/3] Checking for shell integrations...
if exist "%USERPROFILE%\.bashrc" (
    echo Found .bashrc - checking for Kai integrations...
    findstr /i "kai\|Kai" "%USERPROFILE%\.bashrc" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo WARNING: Found Kai references in .bashrc
    ) else (
        echo No Kai references in .bashrc
    )
) else (
    echo No .bashrc found
)

if exist "%USERPROFILE%\.bash_profile" (
    echo Found .bash_profile - checking for Kai integrations...
    findstr /i "kai\|Kai" "%USERPROFILE%\.bash_profile" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo WARNING: Found Kai references in .bash_profile
    )
)

echo.
echo [3/3] Creating safe launcher...
echo.
echo Creating 'kai-safe.bat' - a launcher that isolates Kai
echo from your normal terminal environment.
echo.

(
echo @echo off
echo REM Safe Kai Launcher - Isolated from normal terminal
echo setlocal
echo.
echo echo Starting Kai in isolated environment...
echo.
echo REM Clear any conflicting environment variables
echo set PYTHONPATH=
echo set KAI_%%
echo.
echo REM Launch Kai
echo call run-kai.bat
echo.
echo endlocal
) > kai-safe.bat

echo.
echo ========================================
echo         FIX COMPLETE
echo ========================================
echo.
echo Solutions implemented:
echo.
echo 1. Created 'kai-safe.bat' - use this instead of
echo    run-kai.bat if you're experiencing interference
echo.
echo 2. The safe launcher clears environment variables
echo    that might cause conflicts
echo.
echo 3. If issues persist, check your shell configuration
echo    files (.bashrc, .bash_profile) for Kai aliases
echo.
echo Usage: kai-safe.bat
echo.
pause