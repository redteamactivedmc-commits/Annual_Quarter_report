@echo off
title ADMC Reporting Agent
echo.
echo   =============================================
echo        ADMC Reporting Agent - Starting...
echo   =============================================
echo.

cd /d "%~dp0"

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

echo   Checking packages...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo   First time setup - installing packages...
    pip install flask python-pptx openpyxl anthropic requests python-dotenv rich Pillow
    echo.
)

echo   Pulling latest updates...
git pull origin claude/compassionate-clarke-Cvw9C >nul 2>&1

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

cd admc_report_agent
python app.py

pause
