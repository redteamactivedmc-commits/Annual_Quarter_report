@echo off
title ADMC Reporting Agent
echo.
echo   =============================================
echo        ADMC Reporting Agent - Starting...
echo   =============================================
echo.

cd /d "%~dp0"

set "REPO_URL=https://github.com/redteamactivedmc-commits/Annual_Quarter_report.git"
set "BRANCH=claude/compassionate-clarke-Cvw9C"

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

echo   Checking git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   WARNING: git is not installed, so the app cannot update itself.
    echo   Install Git from https://git-scm.com/download/win to get updates.
    echo.
    goto :run
)

REM --- Self-healing update: works even if this folder came from a ZIP ---
if not exist ".git" (
    echo.
    echo   This folder is NOT connected to GitHub ^(it was unzipped, not cloned^).
    echo   Connecting it now so updates work...
    git init -q
    git remote add origin "%REPO_URL%" 2>nul
)

REM Make sure origin points at the right place even on an existing clone
git remote set-url origin "%REPO_URL%" 2>nul

echo   Pulling latest updates from GitHub...
git fetch origin %BRANCH%
if %errorlevel% neq 0 (
    echo.
    echo   WARNING: Could not reach GitHub. Running the version you already have.
    echo.
    goto :run
)

REM Force the working tree to match the latest code on the branch.
REM Untracked files ^(your .env and your Inputs\logos^) are preserved.
git checkout -B %BRANCH% origin/%BRANCH% >nul 2>&1
git reset --hard origin/%BRANCH%
echo   Updated to the latest version.
echo.

:run
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
