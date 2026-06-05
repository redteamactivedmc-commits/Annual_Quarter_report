@echo off
title ADMC Reporting Agent - First Time Setup
echo.
echo   =============================================
echo   ADMC Reporting Agent - First Time Setup
echo   =============================================
echo.

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

echo   Python found!
echo.
echo   Installing required packages...
echo   (This may take a minute)
echo.

pip install flask python-pptx openpyxl anthropic requests python-dotenv rich Pillow

echo.
echo   =============================================
echo   Setup complete!
echo.
echo   Now double-click "Start_ADMC_Agent.bat" to run the app.
echo   =============================================
echo.

pause
