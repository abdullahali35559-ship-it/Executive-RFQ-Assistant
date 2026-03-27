# RFQ Agent Quick Test Script
# Run this after activating venv

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "RFQ Agent - Client Tracking Test" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if venv is activated
$pythonPath = (Get-Command python).Source
if ($pythonPath -notlike "*venv*") {
    Write-Host "❌ Virtual environment not activated!" -ForegroundColor Red
    Write-Host "Please activate venv first:" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Virtual environment: Active" -ForegroundColor Green
Write-Host "   Python: $pythonPath" -ForegroundColor Gray
Write-Host ""

# Check psycopg2
try {
    python -c "import psycopg2" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ psycopg2: Loaded" -ForegroundColor Green
    } else {
        throw "psycopg2 not found"
    }
} catch {
    Write-Host "❌ psycopg2 not installed" -ForegroundColor Red
    Write-Host "Installing..." -ForegroundColor Yellow
    pip install psycopg2-binary
}

Write-Host ""
Write-Host "Running RFQ Agent..." -ForegroundColor Cyan
Write-Host ""

# Run the test
python scripts\run_rfq_agent.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Test COMPLETED" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Test FAILED" -ForegroundColor Red
}
