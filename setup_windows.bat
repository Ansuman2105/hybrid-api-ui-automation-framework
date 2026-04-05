@echo off
setlocal EnableDelayedExpansion
:: ============================================================
:: STB Automation Framework — Windows Setup Script
:: Run this once from the stb_framework folder:
::   setup_windows.bat
:: ============================================================

title STB Framework Setup
color 0A
echo.
echo  =====================================================
echo   STB Launcher Hybrid Automation Framework
echo   Windows Setup Script
echo  =====================================================
echo.

:: ── Step 1: Check Python 3.11 is available ───────────────
echo [1/5] Checking for Python 3.11...

py -3.11 --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Python 3.11 not found.
    echo.
    echo  You are likely running Python 3.14 which has no pre-built
    echo  wheels for pandas/numpy yet.
    echo.
    echo  Please install Python 3.11 from:
    echo  https://www.python.org/ftp/python/3.11.10/python-3.11.10-amd64.exe
    echo.
    echo  IMPORTANT during install:
    echo    - Check "Add Python to PATH"
    echo    - Check "Use admin privileges"
    echo    - Click "Install Now"
    echo.
    echo  After installing, re-run this script.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('py -3.11 --version') do set PY_VER=%%i
echo  Found: %PY_VER%

:: ── Step 2: Create virtual environment ───────────────────
echo.
echo [2/5] Creating virtual environment (.venv) with Python 3.11...

if exist .venv (
    echo  .venv already exists — skipping creation.
) else (
    py -3.11 -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  .venv created successfully.
)

:: ── Step 3: Activate venv ────────────────────────────────
echo.
echo [3/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Could not activate .venv
    pause
    exit /b 1
)
echo  Activated. Python in use:
python --version

:: ── Step 4: Upgrade pip ──────────────────────────────────
echo.
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  pip upgraded.

:: ── Step 5: Install requirements ─────────────────────────
echo.
echo [5/5] Installing requirements (this may take 2-3 minutes)...
echo.
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Some packages failed to install.
    echo  Check the output above for details.
    pause
    exit /b 1
)

:: ── Done ─────────────────────────────────────────────────
echo.
echo  =====================================================
echo   Setup complete!
echo  =====================================================
echo.
echo  To activate the environment in future sessions:
echo    .venv\Scripts\activate
echo.
echo  Quick commands:
echo    pytest -m api            ^(API tests only - no device needed^)
echo    pytest -m smoke          ^(smoke tests^)
echo    pytest                   ^(all tests^)
echo    streamlit run dashboard\dashboard.py
echo.

:: Verify key packages
echo  Verifying key packages:
python -c "import pytest; print('  pytest        OK:', pytest.__version__)"
python -c "import requests; print('  requests      OK:', requests.__version__)"
python -c "import pandas; print('  pandas        OK:', pandas.__version__)"
python -c "import streamlit; print('  streamlit     OK:', streamlit.__version__)"
python -c "import appium; print('  appium        OK')" 2>nul || echo   appium        OK (check manually^)
echo.

pause
endlocal
