@echo off
:: ============================================================
:: Quick launcher — activates .venv then runs your command
:: Usage:
::   run.bat pytest -m api
::   run.bat pytest -m smoke -v
::   run.bat streamlit run dashboard\dashboard.py
::   run.bat pytest -n 2
::   run.bat webhook          (start n8n webhook server on :5050)
::   run.bat dashboard        (start Streamlit on :8501)
:: ============================================================

if not exist .venv (
    echo ERROR: .venv not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

:: Shortcuts
if "%1"=="webhook" (
    echo Starting STB Webhook Server on http://localhost:5050 ...
    python n8n\webhooks\webhook_server.py
    goto :EOF
)

if "%1"=="dashboard" (
    echo Starting Streamlit Dashboard on http://localhost:8501 ...
    streamlit run dashboard\dashboard.py --server.port 8501
    goto :EOF
)

echo [venv active] Running: %*
echo.
%*
