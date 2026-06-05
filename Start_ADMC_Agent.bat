@echo off
title ADMC Reporting Agent
echo.
echo   =============================================
echo   ADMC Reporting Agent - Starting...
echo   =============================================
echo.

cd /d "%~dp0admc_report_agent"

echo   Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Python is not installed or not in PATH.
    echo   Please install Python from python.org
    echo   Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b
)

echo   Starting the app...
echo.
echo   =============================================
echo   Open your browser and go to:
echo.
echo       http://localhost:5000
echo.
echo   =============================================
echo.
echo   (Keep this window open while using the app)
echo   (Press Ctrl+C to stop)
echo.

python app.py

pause
