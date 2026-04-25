@echo off
echo ========================================
echo   KILL ALL VS CODE: PROCESSES
echo ========================================
echo.
echo This will kill ALL VS Code: processes.
echo Save your work first!
echo.
pause
echo Killing all Code.exe processes...
taskkill /f /im Code.exe 2>nul
echo.
echo Done. VS Code: will close.
echo Restart VS Code: after this.
pause

