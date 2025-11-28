# PowerShell script to setup and activate Python 3.12 virtual environment

Write-Host "Setting up Python 3.12 virtual environment..." -ForegroundColor Green

# Check if Python 3.12 is available
$python312 = Get-Command py -ErrorAction SilentlyContinue
if (-not $python312) {
    Write-Host "Error: Python launcher (py) not found. Please install Python 3.12." -ForegroundColor Red
    exit 1
}

# Check Python 3.12 version
$version = py -3.12 --version
Write-Host "Found: $version" -ForegroundColor Cyan

# Remove existing venv if it exists
if (Test-Path "venv312") {
    Write-Host "Removing existing venv312..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv312
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Green
py -3.12 -m venv venv312

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment, run:" -ForegroundColor Cyan
Write-Host "  .\venv312\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or use the batch file:" -ForegroundColor Cyan
Write-Host "  .\activate_venv.bat" -ForegroundColor Yellow
Write-Host ""
Write-Host "Then install dependencies:" -ForegroundColor Cyan
Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow

