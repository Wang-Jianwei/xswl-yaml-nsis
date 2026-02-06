# Create and prepare a Python 3.8 virtual environment named `.venv38`
# Usage: Run in repository root with PowerShell (Windows)
# Requires: Python 3.8.x installed (e.g., D:\Python\Python38) and on PATH or specify full path

param (
    [string]$Python = "D:\\Python\\Python38\\python.exe",
    [string]$VenvDir = ".venv38"
)

if (-not (Test-Path $Python)) {
    Write-Error "Python executable not found at $Python. Please install Python 3.8 or adjust the path."
    exit 1
}

Write-Host "Creating virtual environment at '$VenvDir' using $Python..." -ForegroundColor Cyan
& $Python -m venv $VenvDir
if ($LASTEXITCODE -ne 0) { Write-Error 'Failed to create virtual env'; exit 1 }

$activate = Join-Path $VenvDir 'Scripts\Activate'
Write-Host "Activating virtual environment and upgrading packaging tools..." -ForegroundColor Cyan
& "$VenvDir\Scripts\python.exe" -m pip install -U pip setuptools wheel

Write-Host "Installing project in editable mode with dev and validation extras..." -ForegroundColor Cyan
& "$VenvDir\Scripts\python.exe" -m pip install -e ".[dev,validation]"

Write-Host "Running test suite to verify environment..." -ForegroundColor Cyan
& "$VenvDir\Scripts\python.exe" -m pytest tests/ -v

Write-Host "Done. To use the venv, run: .\$VenvDir\Scripts\Activate" -ForegroundColor Green