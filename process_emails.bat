@echo off
echo =====================================
echo Email Processing - RFQ Agent
echo =====================================
echo.

REM Change to project directory
REM Change to project directory (using current directory)
REM cd /d "%~dp0"

REM Activate venv (disabled as it might not exit or have different name)
REM call venv\Scripts\activate.bat

echo Checking dependencies...
pip install imapclient email-validator --quiet

echo Checking email for tender submissions...
echo.

REM Run email processor
python scripts\process_emails.py

echo.
if errorlevel 1 (
    echo ❌ Email processing FAILED
    pause
) else (
    echo ✅ Email processing COMPLETE
    pause
)
