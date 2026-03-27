@echo off
echo =====================================
echo Database Migration - Add Version Columns
echo =====================================
echo.

REM Change to project directory
cd /d "D:\RFQ agent"

REM Activate venv
call venv\Scripts\activate.bat

echo Running migration...
echo.

python scripts\migrate_add_version_columns.py

echo.
if errorlevel 1 (
    echo ❌ Migration FAILED
    pause
) else (
    echo ✅ Migration COMPLETE
    pause
)
