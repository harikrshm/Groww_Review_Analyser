# PowerShell script to check email inbox for analysis requests

# Activate virtual environment if it exists
if (Test-Path "venv312\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "venv312\Scripts\Activate.ps1"
}

# Check if EMAIL_PASSWORD is set
if (-not $env:EMAIL_PASSWORD) {
    Write-Host "WARNING: EMAIL_PASSWORD environment variable is not set!" -ForegroundColor Yellow
    Write-Host "Set it with: `$env:EMAIL_PASSWORD='your-app-password'" -ForegroundColor Yellow
    Write-Host ""
}

# Run the check-email command
Write-Host "Checking email inbox for analysis requests..." -ForegroundColor Cyan
python -m src.cli check-email

