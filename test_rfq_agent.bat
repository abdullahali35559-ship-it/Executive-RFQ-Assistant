@echo off
echo =====================================
echo RFQ Agent Test - Client Tracking
echo =====================================
echo.

REM Change to project directory
cd /d "D:\RFQ agent"

REM Activate venv
call venv\Scripts\activate.bat

REM Verify psycopg2 is installed
echo Checking psycopg2...
python -c "import psycopg2; print('✅ psycopg2 loaded successfully')" 2>nul
if errorlevel 1 (
    echo ❌ psycopg2 not found, installing...
    pip install psycopg2-binary
)

echo.
echo Running RFQ Agent...
echo.

REM Run the test
python scripts\run_rfq_agent.py

echo.
if errorlevel 1 (
    echo ❌ Test FAILED
    pause
) else (
    echo ✅ Test COMPLETED
    pause
)
