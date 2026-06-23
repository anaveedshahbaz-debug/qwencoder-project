@echo off
REM NESPAK PMS Desktop Launcher for Windows
REM Double-click this file to start the application

cd /d "%~dp0"

echo ============================================================
echo   NESPAK Project Monitoring System - Desktop Edition
echo ============================================================
echo.
echo Starting application...
echo.

REM Check if running as compiled EXE or from source
if exist "NESPAK_PMS.exe" (
    echo Launching compiled application...
    start "" "NESPAK_PMS.exe"
) else (
    echo Launching from Python source...
    python desktop_app.py
)

pause
