@echo off
title NESPAK PMS - Guest Access
color 1F
cls
echo ============================================================
echo   NESPAK PMS - Open on this computer (Guest)
echo ============================================================
echo.
echo   This computer does NOT run the server.
echo   The Admin computer must already be running NESPAK PMS.
echo.
echo   Enter the Admin computer's network address shown
echo   when they started the server, for example:
echo.
echo       192.168.1.50
echo.
set /p IP="Enter Admin computer's IP address: "

start http://%IP%:5000

echo.
echo   Opening http://%IP%:5000 in your browser...
echo   Login with Guest password: guest123
echo.
pause
