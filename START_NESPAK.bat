@echo off
title NESPAK PMS Server
color 1F
cls

cd /d "%~dp0"

echo ============================================================
echo   NESPAK Project Monitoring System - Starting...
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo During installation, CHECK "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages, please wait...
    pip install flask openpyxl
    echo.
)

echo Starting server...
echo.
echo ============================================================
echo   IMPORTANT: KEEP THIS WINDOW OPEN while using NESPAK PMS
echo.
echo   Your browser will open automatically in 3 seconds.
echo   If not, manually open: http://localhost:5000
echo.
echo   Login:
echo     Admin password: admin123
echo     Guest password: guest123
echo.
echo   To STOP: close this window or press Ctrl+C
echo ============================================================
echo.

REM Open browser after a short delay (in background)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

REM Start the server (this keeps the window open and shows logs)
python run.py

pause
