@echo off
title High CPU Killer - Run as Admin
echo Scanning and killing common high CPU processes...
echo.

taskkill /f /im python.exe 2>nul && echo Killed python.exe or echo No python.exe found
taskkill /f /im python3.exe 2>nul && echo Killed python3.exe || echo No python3.exe found
taskkill /f /im docker.exe 2>nul && echo Killed docker.exe || echo No docker.exe found
taskkill /f /im dockerd.exe 2>nul && echo Killed dockerd.exe || echo No dockerd.exe found
taskkill /f /im wsl.exe 2>nul && echo Killed wsl.exe || echo No wsl.exe found
taskkill /f /im com.docker.service.exe 2>nul && echo Killed Docker service || echo No Docker service found
taskkill /f /im node.exe 2>nul && echo Killed node.exe || echo No node.exe found
taskkill /f /im kai.exe 2>nul && echo Killed kai.exe || echo No kai.exe found

echo.
echo Process kill complete. Open Task Manager to verify CPU usage.
echo If Kai Python error persists, fix syntax in C:\Users\7nujy6xc\kai\src\kai\assistant.py line 451.
echo Press any key to exit.
pause >nul
