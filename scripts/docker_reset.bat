@echo off
title Docker Desktop Reset - Run as Admin
echo Stopping Docker services and resetting...
echo.

net stop com.docker.service /y 2>nul && echo Stopped com.docker.service || echo Service not running
net stop docker /y 2>nul && echo Stopped docker || echo Docker service not running

wsl --shutdown 2>nul && echo WSL shutdown || echo No WSL running

REM Clear Docker temp state (safe)
rmdir /s /q "%LOCALAPPDATA%\Docker\wsl" 2>nul
rmdir /s /q "%LOCALAPPDATA%\Docker\ext4.vhdx" 2>nul

echo.
echo Reset complete. Relaunch Docker Desktop normally.
echo If stalls, uninstall/reinstall from docker.com.
echo Press any key to exit.
pause >nul
